"""Deterministic explainable risk scoring for Cyber Twin assets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.vulnerability import RiskResult, RiskSummary
from app.services.vulnerability_service import AssetNotFoundError, _ensure_asset


WEIGHTS = {
    "vulnerability": 0.40,
    "exposure": 0.30,
    "connectivity": 0.15,
    "criticality": 0.15,
}


def risk_level(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _exposure_score(level: str) -> float:
    return {"public": 100.0, "internal": 60.0, "restricted": 20.0, "unknown": 30.0}.get(level, 30.0)


def _criticality_score(value: str | None) -> float:
    return {"low": 20.0, "medium": 50.0, "high": 75.0, "critical": 100.0}.get(
        str(value or "").lower(), 30.0
    )


def calculate_asset_risk(session: Any, asset_id: str) -> RiskResult:
    asset = _ensure_asset(session, asset_id)

    records = session.run(
        """
        MATCH (a:Asset {id: $asset_id})-[r:HAS_VULNERABILITY]->(v:Vulnerability)
        WHERE (r.status IN ['accepted', 'confirmed'] OR r.match_type = 'confirmed')
          AND r.match_type <> 'potential'
          AND r.status <> 'resolved'
          AND r.status <> 'rejected'
          AND coalesce(v.rejected, false) = false
        RETURN v.cvss_score AS cvss_score, v.cve_id AS cve_id
        """,
        asset_id=asset_id,
    )
    accepted_scores: list[float] = []
    cve_ids: list[str] = []
    for record in records:
        score = record["cvss_score"]
        if score is not None:
            accepted_scores.append(float(score))
            cve_ids.append(str(record["cve_id"]))

    if accepted_scores:
        distinct = sorted(set(accepted_scores), reverse=True)
        top = distinct[:3]
        vulnerability_score = min(100.0, max(top) * 10.0 + sum(top[1:]) * 2.0)
    else:
        vulnerability_score = 0.0

    exposure_level = str(asset.get("exposure", "")).lower()
    if exposure_level in {"public", "external", "internet-facing"}:
        normalized_exposure = "public"
    elif exposure_level in {"internal", "internally accessible"}:
        normalized_exposure = "internal"
    elif exposure_level in {"private", "restricted", "isolated"}:
        normalized_exposure = "restricted"
    else:
        normalized_exposure = "unknown"
    exposure_score = _exposure_score(normalized_exposure)

    degree_record = session.run(
        """
        MATCH (a:Asset {id: $asset_id})
        OPTIONAL MATCH (a)-[out:CONNECTS_TO]->(:Asset)
        WHERE out.allowed = true
        OPTIONAL MATCH (:Asset)-[incoming:CONNECTS_TO]->(a)
        WHERE incoming.allowed = true
        RETURN count(DISTINCT out) + count(DISTINCT incoming) AS degree
        """,
        asset_id=asset_id,
    ).single()
    degree = int(degree_record["degree"] or 0) if degree_record else 0
    connectivity_score = min(100.0, degree / 5.0 * 100.0)

    criticality_score = _criticality_score(asset.get("criticality"))
    overall = (
        WEIGHTS["vulnerability"] * vulnerability_score
        + WEIGHTS["exposure"] * exposure_score
        + WEIGHTS["connectivity"] * connectivity_score
        + WEIGHTS["criticality"] * criticality_score
    )
    overall = round(min(100.0, max(0.0, overall)), 2)
    level = risk_level(overall)
    calculated_at = datetime.now(timezone.utc).isoformat()

    evidence = [
        f"{len(cve_ids)} accepted/confirmed CVE association(s)",
        f"Exposure classified as {normalized_exposure}",
        f"Allowed graph degree is {degree}",
        f"Criticality is {str(asset.get('criticality') or 'unknown')}",
    ]
    uncertainty: list[str] = []
    if normalized_exposure == "unknown":
        uncertainty.append("Exposure evidence is incomplete")
    if not cve_ids:
        uncertainty.append("No CVSS-bearing confirmed/applicable vulnerability associations")

    result = RiskResult(
        asset_id=asset_id,
        overall_score=overall,
        risk_level=level,
        vulnerability_contribution=round(WEIGHTS["vulnerability"] * vulnerability_score, 2),
        exposure_contribution=round(WEIGHTS["exposure"] * exposure_score, 2),
        connectivity_contribution=round(WEIGHTS["connectivity"] * connectivity_score, 2),
        criticality_contribution=round(WEIGHTS["criticality"] * criticality_score, 2),
        factor_scores={
            "vulnerability": round(vulnerability_score, 2),
            "exposure": round(exposure_score, 2),
            "connectivity": round(connectivity_score, 2),
            "criticality": round(criticality_score, 2),
        },
        explanation=(
            f"Risk combines normalized vulnerability ({vulnerability_score:.1f}), exposure "
            f"({exposure_score:.1f}), connectivity ({connectivity_score:.1f}), and criticality "
            f"({criticality_score:.1f}) factors using the netra-risk-v1 weights."
        ),
        evidence=evidence,
        uncertainty=uncertainty,
        calculated_at=calculated_at,
    )
    session.run(
        """
        MATCH (a:Asset {id: $asset_id})
        SET a.risk_score = $risk_score,
            a.risk_level = $risk_level,
            a.risk_calculated_at = $calculated_at
        """,
        asset_id=asset_id,
        risk_score=overall,
        risk_level=level,
        calculated_at=calculated_at,
    ).consume()
    return result


def get_asset_risk(session: Any, asset_id: str) -> RiskResult:
    _ensure_asset(session, asset_id)
    return calculate_asset_risk(session, asset_id)


def recalculate_all(session: Any) -> list[RiskResult]:
    ids = session.run("MATCH (a:Asset) RETURN a.id AS id ORDER BY a.id")
    return [calculate_asset_risk(session, str(record["id"])) for record in ids]


def risk_summary(session: Any) -> RiskSummary:
    asset_records = session.run(
        """
        MATCH (a:Asset)
        OPTIONAL MATCH (a)-[r:HAS_VULNERABILITY]->(v:Vulnerability)
        RETURN a.risk_score AS risk_score,
               count(DISTINCT CASE WHEN r.status IN ['accepted','confirmed'] OR r.match_type = 'confirmed' THEN v.cve_id ELSE NULL END) AS asset_cves,
               count(DISTINCT v.cve_id) AS distinct_from_asset
        """
    )
    total = 0
    confirmed_assets = 0
    distinct: set[str] = set()
    bands = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
    scores: list[float] = []
    for record in asset_records:
        total += 1
        score = record["risk_score"]
        if score is None:
            bands["unknown"] += 1
        else:
            value = float(score)
            scores.append(value)
            bands[risk_level(value)] += 1
        if int(record["asset_cves"] or 0) > 0:
            confirmed_assets += 1

    cves = session.run(
        "MATCH (:Asset)-[:HAS_VULNERABILITY]->(v:Vulnerability) RETURN count(DISTINCT v.cve_id) AS count"
    ).single()
    distinct_count = int(cves["count"] or 0)
    overall = "unknown"
    if scores:
        overall = risk_level(round(sum(scores) / len(scores), 2))
    return RiskSummary(
        total_assets=total,
        confirmed_vulnerability_assets=confirmed_assets,
        distinct_associated_cves=distinct_count,
        high_risk_assets=bands["high"],
        medium_risk_assets=bands["medium"],
        low_risk_assets=bands["low"],
        unknown_risk_assets=bands["unknown"],
        overall_infrastructure_risk=overall,
        aggregation_method="Overall infrastructure risk is the average asset score rounded to 0-39 low, 40-69 medium, 70-100 high.",
    )
