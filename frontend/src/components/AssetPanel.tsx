import { useEffect, useState, type FormEvent } from 'react';
import {
  attachAssetVulnerability,
  getAssetExposure,
  getAssetRisk,
  getAssetVulnerabilities,
  recalculateAssetRisk,
  refreshAssetVulnerabilities,
  removeAssetVulnerability,
  searchVulnerabilities,
  updateAssetVulnerability,
  type Asset,
  type AssetVulnerability,
  type ExposureAssessment,
  type RiskResult,
  type VulnerabilityDetails,
} from '../services/api';

interface AssetPanelProps {
  asset: Asset | null;
  onClose: () => void;
  onAssetUpdated?: () => void;
}

function formatPorts(ports: number[] | undefined): string {
  if (!ports || ports.length === 0) return 'None';
  return ports.join(', ');
}

export default function AssetPanel({ asset, onClose, onAssetUpdated }: AssetPanelProps) {
  const [vulnerabilities, setVulnerabilities] = useState<AssetVulnerability[]>([]);
  const [exposure, setExposure] = useState<ExposureAssessment | null>(null);
  const [risk, setRisk] = useState<RiskResult | null>(null);
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<VulnerabilityDetails[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!asset) return;
    setMessage(null);
    setError(null);
    void Promise.all([
      getAssetVulnerabilities(asset.id),
      getAssetExposure(asset.id),
      getAssetRisk(asset.id),
    ]).then(([vulns, exposureData, riskData]) => {
      setVulnerabilities(vulns);
      setExposure(exposureData);
      setRisk(riskData);
    }).catch((err) => setError(err instanceof Error ? err.message : 'Unable to load asset security data.'));
  }, [asset?.id]);

  if (!asset) {
    return (
      <aside className="asset-panel empty" aria-label="Asset details panel">
        <div className="asset-panel-header"><h2>Asset details</h2></div>
        <p>Select a node in the graph to view its details.</p>
      </aside>
    );
  }

  const reload = async () => {
    const [vulns, exposureData, riskData] = await Promise.all([
      getAssetVulnerabilities(asset.id),
      getAssetExposure(asset.id),
      getAssetRisk(asset.id),
    ]);
    setVulnerabilities(vulns);
    setExposure(exposureData);
    setRisk(riskData);
  };

  const handleSearch = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await searchVulnerabilities(search.trim());
      setSearchResults(result.items);
      if (!result.items.length) setMessage('No candidate CVEs returned by NVD.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'NVD search failed.');
    } finally {
      setBusy(false);
    }
  };

  const attach = async (cveId: string) => {
    setBusy(true);
    setError(null);
    try {
      await attachAssetVulnerability(asset.id, {
        cve_id: cveId,
        evidence: 'Manually reviewed candidate from NVD search',
        match_type: 'manual',
        status: 'potential',
      });
      setMessage(`${cveId} attached for review as a potential match.`);
      await reload();
      onAssetUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to attach CVE.');
    } finally {
      setBusy(false);
    }
  };

  const remove = async (cveId: string) => {
    if (!window.confirm(`Remove ${cveId} from ${asset.name}?`)) return;
    setBusy(true);
    setError(null);
    try {
      await removeAssetVulnerability(asset.id, cveId);
      setMessage(`${cveId} removed from this asset.`);
      await reload();
      onAssetUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to remove CVE.');
    } finally {
      setBusy(false);
    }
  };

  const accept = async (association: AssetVulnerability) => {
    setBusy(true);
    try {
      await updateAssetVulnerability(asset.id, association.cve_id, {
        status: 'accepted',
        match_type: 'confirmed',
      });
      await reload();
      onAssetUpdated?.();
      setMessage(`${association.cve_id} marked confirmed.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update association.');
    } finally {
      setBusy(false);
    }
  };

  const refresh = async () => {
    setBusy(true);
    setError(null);
    try {
      await refreshAssetVulnerabilities(asset.id);
      await recalculateAssetRisk(asset.id);
      await reload();
      onAssetUpdated?.();
      setMessage('CVE metadata and risk refreshed.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Refresh failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="asset-panel security-panel" aria-label="Asset details panel">
      <div className="asset-panel-header">
        <div><p className="eyebrow">Selected asset</p><h2>{asset.name}</h2></div>
        <button type="button" className="panel-close" onClick={onClose} aria-label="Close asset details">×</button>
      </div>
      <dl className="asset-details">
        <div><dt>ID</dt><dd>{asset.id}</dd></div>
        <div><dt>Type</dt><dd>{asset.type}</dd></div>
        <div><dt>IP Address</dt><dd>{asset.ip || 'N/A'}</dd></div>
        <div><dt>Operating System</dt><dd>{asset.os || 'N/A'}</dd></div>
        <div><dt>Ports</dt><dd>{formatPorts(asset.ports)}</dd></div>
        <div><dt>Software</dt><dd>{asset.software?.length ? asset.software.map((item) => `${item.product}${item.version ? ` ${item.version}` : ''}`).join(', ') : 'Not inventoried'}</dd></div>
        <div><dt>Exposure</dt><dd>{exposure?.exposure_level || asset.exposure || 'unknown'}</dd></div>
        <div><dt>Criticality</dt><dd>{asset.criticality || 'unknown'}</dd></div>
      </dl>

      {risk ? (
        <section className="security-section">
          <h3>Risk: {risk.overall_score}/100 <span className={`risk-badge ${risk.risk_level}`}>{risk.risk_level}</span></h3>
          <p>{risk.explanation}</p>
          <div className="risk-factors">
            <span>Vulnerability {risk.vulnerability_contribution}</span>
            <span>Exposure {risk.exposure_contribution}</span>
            <span>Connectivity {risk.connectivity_contribution}</span>
            <span>Criticality {risk.criticality_contribution}</span>
          </div>
          <small>Calculated {risk.calculated_at}</small>
        </section>
      ) : null}

      <section className="security-section">
        <div className="security-heading"><h3>Vulnerabilities ({vulnerabilities.length})</h3><button type="button" className="secondary-btn" onClick={() => void refresh()} disabled={busy}>Refresh</button></div>
        {vulnerabilities.length === 0 ? <p className="form-help">No associated CVEs.</p> : vulnerabilities.map((item) => (
          <article className="vulnerability-card" key={item.cve_id}>
            <div className="vulnerability-title"><strong>{item.cve_id}</strong><span className={`status-badge ${item.match_type}`}>{item.match_type}</span></div>
            <p>{item.vulnerability.description || 'No description available.'}</p>
            <div className="vulnerability-meta">
              <span>Severity: {item.vulnerability.severity || 'unknown'}</span>
              <span>CVSS: {item.vulnerability.cvss_score != null ? `${item.vulnerability.cvss_score} v${item.vulnerability.cvss_version || '?'}` : 'unavailable'}</span>
              <span>Status: {item.status}</span>
            </div>
            {item.evidence ? <small>Evidence: {item.evidence}</small> : null}
            <div className="vulnerability-actions">
              {item.match_type !== 'confirmed' ? <button type="button" className="secondary-btn" onClick={() => void accept(item)} disabled={busy}>Mark confirmed</button> : null}
              <button type="button" className="secondary-btn danger" onClick={() => void remove(item.cve_id)} disabled={busy}>Remove</button>
            </div>
          </article>
        ))}
      </section>

      <section className="security-section">
        <h3>NVD candidate search</h3>
        <form className="twin-form" onSubmit={handleSearch}>
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="nginx 1.25 / CVE keyword" required />
          <button type="submit" className="primary-btn" disabled={busy || !search.trim()}>{busy ? 'Searching…' : 'Search NVD'}</button>
        </form>
        {searchResults.map((item) => (
          <article className="vulnerability-card" key={item.cve_id}>
            <div className="vulnerability-title"><strong>{item.cve_id}</strong><span>{item.cvss_score != null ? `${item.cvss_score}` : 'No CVSS'}</span></div>
            <p>{item.description || 'No description available.'}</p>
            <button type="button" className="secondary-btn" onClick={() => void attach(item.cve_id)} disabled={busy}>Attach for review</button>
          </article>
        ))}
      </section>
      {exposure?.uncertainty.length ? <p className="form-help">Uncertainty: {exposure.uncertainty.join('; ')}</p> : null}
      {message ? <p className="form-message success">{message}</p> : null}
      {error ? <p className="form-message error" role="alert">{error}</p> : null}
    </aside>
  );
}
