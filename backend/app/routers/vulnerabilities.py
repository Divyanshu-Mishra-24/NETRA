"""Vulnerability lookup, association, exposure and risk API routes."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database.neo4j import Neo4jError, ServiceUnavailable, get_neo4j_session
from app.models.vulnerability import (
    AssetVulnerabilityAssociation,
    AttachVulnerabilityRequest,
    ExposureAssessment,
    RiskResult,
    RiskSummary,
    UpdateVulnerabilityRequest,
)
from app.services.nvd_service import (
    NVDNotFoundError,
    NVDAuthenticationError,
    NVDRateLimitError,
    NVDUnavailableError,
    NVDBadRequestError,
    NVDResponseError,
    nvd_client,
)
from app.services.vulnerability_service import (
    AssetNotFoundError,
    AssociationNotFoundError,
    DuplicateAssociationError,
    assess_exposure,
    attach_asset_vulnerability,
    list_asset_vulnerabilities,
    refresh_asset_vulnerabilities,
    remove_asset_vulnerability,
    update_asset_vulnerability,
)
from app.services.risk_service import calculate_asset_risk, get_asset_risk, recalculate_all, risk_summary

router = APIRouter(tags=["vulnerabilities"])
CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.I)


def _db_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, (ServiceUnavailable, Neo4jError)):
        return HTTPException(status_code=503, detail="Neo4j database is unavailable")
    return HTTPException(status_code=500, detail="Unexpected database error")


@router.get("/vulnerabilities/search")
def search_vulnerabilities(
    keyword: str = Query(min_length=1, max_length=200),
    start_index: int = Query(default=0, ge=0),
    results_per_page: int = Query(default=20, ge=1, le=2000),
) -> dict[str, Any]:
    try:
        return nvd_client.search(keyword, start_index, results_per_page)
    except NVDRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except NVDAuthenticationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except NVDBadRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NVDResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except NVDBadRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NVDResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (NVDUnavailableError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="NVD is temporarily unavailable") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/vulnerabilities/{cve_id}")
def get_vulnerability(cve_id: str) -> dict[str, Any]:
    cve_id = cve_id.upper()
    if not CVE_RE.match(cve_id):
        raise HTTPException(status_code=400, detail="CVE ID must use the format CVE-YYYY-NNNN")
    try:
        return nvd_client.get_cve(cve_id)
    except NVDNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NVDRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except NVDAuthenticationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except NVDUnavailableError as exc:
        raise HTTPException(status_code=503, detail="NVD is temporarily unavailable") from exc


@router.get("/assets/{asset_id}/vulnerabilities", response_model=list[AssetVulnerabilityAssociation])
def asset_vulnerabilities(asset_id: str, session: Any = Depends(get_neo4j_session)):
    try:
        return list_asset_vulnerabilities(session, asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise _db_errors(exc)


@router.post("/assets/{asset_id}/vulnerabilities", response_model=AssetVulnerabilityAssociation, status_code=201)
def attach_vulnerability(asset_id: str, payload: AttachVulnerabilityRequest, session: Any = Depends(get_neo4j_session)):
    try:
        return attach_asset_vulnerability(session, asset_id, payload)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DuplicateAssociationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except NVDNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NVDRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except NVDAuthenticationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except NVDUnavailableError as exc:
        raise HTTPException(status_code=503, detail="NVD is temporarily unavailable") from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise _db_errors(exc)


@router.patch("/assets/{asset_id}/vulnerabilities/{cve_id}", response_model=AssetVulnerabilityAssociation)
def patch_vulnerability(asset_id: str, cve_id: str, payload: UpdateVulnerabilityRequest, session: Any = Depends(get_neo4j_session)):
    try:
        return update_asset_vulnerability(session, asset_id, cve_id, payload)
    except AssociationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise _db_errors(exc)


@router.delete("/assets/{asset_id}/vulnerabilities/{cve_id}", status_code=204)
def delete_vulnerability(asset_id: str, cve_id: str, session: Any = Depends(get_neo4j_session)):
    try:
        remove_asset_vulnerability(session, asset_id, cve_id)
        return None
    except AssociationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise _db_errors(exc)


@router.post("/assets/{asset_id}/vulnerabilities/refresh", response_model=list[AssetVulnerabilityAssociation])
def refresh_vulnerability(asset_id: str, session: Any = Depends(get_neo4j_session)):
    try:
        return refresh_asset_vulnerabilities(session, asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise _db_errors(exc)


@router.get("/assets/{asset_id}/exposure", response_model=ExposureAssessment)
def asset_exposure(asset_id: str, session: Any = Depends(get_neo4j_session)):
    try:
        return assess_exposure(session, asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise _db_errors(exc)


@router.get("/assets/{asset_id}/risk", response_model=RiskResult)
def asset_risk(asset_id: str, session: Any = Depends(get_neo4j_session)):
    try:
        return get_asset_risk(session, asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise _db_errors(exc)


@router.post("/assets/{asset_id}/risk/recalculate", response_model=RiskResult)
def recalculate_asset_risk(asset_id: str, session: Any = Depends(get_neo4j_session)):
    try:
        return calculate_asset_risk(session, asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise _db_errors(exc)


@router.get("/risk/summary", response_model=RiskSummary)
def get_risk_summary(session: Any = Depends(get_neo4j_session)):
    try:
        return risk_summary(session)
    except (ServiceUnavailable, Neo4jError) as exc:
        raise _db_errors(exc)


@router.post("/risk/recalculate-all", response_model=list[RiskResult])
def recalculate_all_risk(session: Any = Depends(get_neo4j_session)):
    try:
        return recalculate_all(session)
    except (ServiceUnavailable, Neo4jError) as exc:
        raise _db_errors(exc)
