import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import AssetPanel from '../components/AssetPanel';
import InfrastructureGraph from '../components/InfrastructureGraph';
import {
  API_BASE_URL,
  ApiError,
  createAsset,
  createConnection,
  getGraph,
  getRiskSummary,
  type Asset,
  type AssetCreateInput,
  type GraphEdge,
  type GraphNode,
  type RiskSummary,
} from '../services/api';

type LoadState = 'loading' | 'ready' | 'empty' | 'error';

interface AssetFormState {
  id: string;
  name: string;
  type: string;
  ip: string;
  os: string;
  ports: string;
  exposure: string;
  criticality: string;
}

interface ConnectionFormState {
  source: string;
  target: string;
  protocol: string;
  port: string;
  allowed: string;
  evidence: string;
}

const initialAssetForm: AssetFormState = {
  id: '',
  name: '',
  type: '',
  ip: '',
  os: '',
  ports: '',
  exposure: '',
  criticality: '',
};

const initialConnectionForm: ConnectionFormState = {
  source: '',
  target: '',
  protocol: '',
  port: '',
  allowed: 'true',
  evidence: '',
};

function parsePorts(value: string): number[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => Number(item))
    .filter((item) => Number.isInteger(item) && item >= 0 && item <= 65535);
}

function formatPorts(ports: number[] | undefined): string {
  if (!ports || ports.length === 0) return 'None';
  return ports.join(', ');
}

function errorText(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred.';
}

export default function NetworkTwin() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [riskSummary, setRiskSummary] = useState<RiskSummary | null>(null);

  const [assetForm, setAssetForm] = useState<AssetFormState>(initialAssetForm);
  const [connectionForm, setConnectionForm] = useState<ConnectionFormState>(initialConnectionForm);
  const [assetSubmitting, setAssetSubmitting] = useState(false);
  const [connectionSubmitting, setConnectionSubmitting] = useState(false);
  const [assetFormMessage, setAssetFormMessage] = useState<string | null>(null);
  const [assetFormError, setAssetFormError] = useState<string | null>(null);
  const [connectionFormMessage, setConnectionFormMessage] = useState<string | null>(null);
  const [connectionFormError, setConnectionFormError] = useState<string | null>(null);

  const loadGraph = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) {
      setIsRefreshing(true);
    } else {
      setLoadState('loading');
    }
    setErrorMessage(null);

    try {
      const [graph, summary] = await Promise.all([
        getGraph(),
        getRiskSummary().catch(() => null),
      ]);
      setRiskSummary(summary);
      const nextNodes = Array.isArray(graph.nodes) ? graph.nodes : [];
      const nextEdges = Array.isArray(graph.edges) ? graph.edges : [];
      setNodes(nextNodes);
      setEdges(nextEdges);
      setLoadState(nextNodes.length === 0 ? 'empty' : 'ready');

      setSelectedAssetId((current) => {
        if (!current) return null;
        return nextNodes.some((node) => node.id === current) ? current : null;
      });
    } catch (error) {
      setNodes([]);
      setEdges([]);
      setSelectedAssetId(null);
      setLoadState('error');
      setErrorMessage(errorText(error));
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadGraph();
  }, [loadGraph]);

  const assets = useMemo<Asset[]>(() => nodes.map((node) => node.data), [nodes]);
  const selectedAsset = useMemo<Asset | null>(
    () => assets.find((asset) => asset.id === selectedAssetId) ?? null,
    [assets, selectedAssetId],
  );

  const statsLabel = useMemo(() => {
    if (loadState === 'loading') return 'Loading topology...';
    if (loadState === 'error') return 'Backend unavailable';
    return `${assets.length} assets / ${edges.length} connections`;
  }, [assets.length, edges.length, loadState]);

  const handleAssetSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAssetFormError(null);
    setAssetFormMessage(null);

    const payload: AssetCreateInput = {
      id: assetForm.id.trim(),
      name: assetForm.name.trim(),
      type: assetForm.type.trim(),
      ip: assetForm.ip.trim() || null,
      os: assetForm.os.trim() || null,
      ports: parsePorts(assetForm.ports),
      exposure: assetForm.exposure.trim() || null,
      criticality: assetForm.criticality.trim() || null,
    };

    if (!payload.id || !payload.name || !payload.type) {
      setAssetFormError('ID, name, and type are required.');
      return;
    }

    setAssetSubmitting(true);
    try {
      await createAsset(payload);
      setAssetFormMessage(`Asset "${payload.name}" added successfully.`);
      setAssetForm(initialAssetForm);
      await loadGraph(true);
    } catch (error) {
      setAssetFormError(errorText(error));
    } finally {
      setAssetSubmitting(false);
    }
  };

  const handleConnectionSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setConnectionFormError(null);
    setConnectionFormMessage(null);

    const source = connectionForm.source.trim();
    const target = connectionForm.target.trim();
    if (!source || !target) {
      setConnectionFormError('Source and target assets are required.');
      return;
    }
    if (source === target) {
      setConnectionFormError('Source and target must be different assets.');
      return;
    }

    const portText = connectionForm.port.trim();
    const portValue = portText ? Number(portText) : null;
    if (portText && (!Number.isInteger(portValue) || (portValue ?? -1) < 0 || (portValue ?? 70000) > 65535)) {
      setConnectionFormError('Port must be an integer between 0 and 65535.');
      return;
    }

    setConnectionSubmitting(true);
    try {
      await createConnection(source, {
        target,
        protocol: connectionForm.protocol.trim() || null,
        port: portValue,
        allowed: connectionForm.allowed === 'unknown' ? null : connectionForm.allowed === 'true',
        evidence: connectionForm.evidence.trim() || null,
      });
      setConnectionFormMessage(`Connection "${source}" → "${target}" created successfully.`);
      setConnectionForm((current) => ({ ...initialConnectionForm, source: current.source, target: '' }));
      await loadGraph(true);
    } catch (error) {
      setConnectionFormError(errorText(error));
    } finally {
      setConnectionSubmitting(false);
    }
  };

  return (
    <main className="twin-shell">
      <header className="twin-header">
        <a className="brand" href="#home"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span><span>NETRA</span></a>
        <a className="back-link" href="#home">← Back to environments</a>
      </header>

      <section className="twin-main" aria-labelledby="network-title">
        <div className="twin-intro">
          <p className="eyebrow">Network twin / live model</p>
          <h1 id="network-title">Network <em>topology.</em></h1>
          <p>Live cyber infrastructure digital twin backed by Neo4j. Explore assets, inspect details, and update the graph through the NETRA backend.</p>
        </div>

        <div className="twin-toolbar">
          <div className="health" role="status" aria-live="polite">
            <span className={`status-dot ${loadState === 'error' ? 'error' : ''}`} />
            <span>Topology status</span>
            <b>{statsLabel}</b>
          </div>
          <div className="toolbar-actions">
            <span className="api-hint">API: {API_BASE_URL}</span>
            <button type="button" className="secondary-btn" onClick={() => void loadGraph(true)} disabled={isRefreshing || loadState === 'loading'}>
              {isRefreshing ? 'Refreshing…' : 'Refresh graph'}
            </button>
          </div>
        </div>
        {riskSummary ? (
          <section className="risk-summary" aria-label="Infrastructure risk summary">
            <span><b>{riskSummary.total_assets}</b> assets</span>
            <span><b>{riskSummary.distinct_associated_cves}</b> distinct CVEs</span>
            <span><b>{riskSummary.confirmed_vulnerability_assets}</b> confirmed-vulnerability assets</span>
            <span><b>{riskSummary.high_risk_assets}</b> high</span>
            <span><b>{riskSummary.medium_risk_assets}</b> medium</span>
            <span><b>{riskSummary.low_risk_assets}</b> low</span>
            <span><b>{riskSummary.unknown_risk_assets}</b> unknown risk</span>
            <span>Overall <b className={`risk-summary-level ${riskSummary.overall_infrastructure_risk}`}>{riskSummary.overall_infrastructure_risk}</b></span>
          </section>
        ) : null}

        <section className="graph-workspace" aria-label="Network topology workspace">
          <div className="graph-panel">
            {loadState === 'loading' ? (
              <div className="state-panel loading">
                <h2>Loading network topology…</h2>
                <p>Fetching live assets and connections from the NETRA backend.</p>
              </div>
            ) : null}

            {loadState === 'error' ? (
              <div className="state-panel error" role="alert">
                <h2>Unable to load topology</h2>
                <p>{errorMessage || 'The backend is unavailable.'}</p>
                <p className="state-help">Ensure the FastAPI backend is running, Neo4j is reachable, and the inventory has been imported.</p>
                <button type="button" className="primary-btn" onClick={() => void loadGraph()}>Retry</button>
              </div>
            ) : null}

            {loadState === 'empty' ? (
              <div className="state-panel empty">
                <h2>No topology data found</h2>
                <p>The Neo4j digital twin is reachable but contains no network assets yet. Run the infrastructure importer or add an asset below.</p>
              </div>
            ) : null}

            {loadState === 'ready' ? (
              <InfrastructureGraph
                nodes={nodes}
                edges={edges}
                selectedAssetId={selectedAssetId}
                onSelectAsset={setSelectedAssetId}
              />
            ) : null}
          </div>

          <AssetPanel
            asset={selectedAsset}
            onClose={() => setSelectedAssetId(null)}
            onAssetUpdated={() => void loadGraph(true)}
          />
        </section>

        <section className="twin-actions" aria-label="Network twin actions">
          <article className="action-card">
            <div className="action-card-header">
              <p className="eyebrow">Update twin</p>
              <h2>Add asset</h2>
              <p>Create a new infrastructure asset in Neo4j.</p>
            </div>
            <form className="twin-form" onSubmit={handleAssetSubmit}>
              <div className="form-grid">
                <label><span>ID *</span><input value={assetForm.id} onChange={(e) => setAssetForm({ ...assetForm, id: e.target.value })} placeholder="web-02" required /></label>
                <label><span>Name *</span><input value={assetForm.name} onChange={(e) => setAssetForm({ ...assetForm, name: e.target.value })} placeholder="Secondary Web Server" required /></label>
                <label><span>Type *</span><input value={assetForm.type} onChange={(e) => setAssetForm({ ...assetForm, type: e.target.value })} placeholder="web_server" required /></label>
                <label><span>IP address</span><input value={assetForm.ip} onChange={(e) => setAssetForm({ ...assetForm, ip: e.target.value })} placeholder="10.0.1.20" /></label>
                <label><span>Operating system</span><input value={assetForm.os} onChange={(e) => setAssetForm({ ...assetForm, os: e.target.value })} placeholder="Ubuntu 24.04" /></label>
                <label><span>Ports (comma-separated)</span><input value={assetForm.ports} onChange={(e) => setAssetForm({ ...assetForm, ports: e.target.value })} placeholder="80, 443" /></label>
                <label><span>Exposure</span><input value={assetForm.exposure} onChange={(e) => setAssetForm({ ...assetForm, exposure: e.target.value })} placeholder="public / internal / private" /></label>
                <label><span>Criticality</span><input value={assetForm.criticality} onChange={(e) => setAssetForm({ ...assetForm, criticality: e.target.value })} placeholder="low / medium / high / critical" /></label>
              </div>
              {assetFormError ? <p className="form-message error" role="alert">{assetFormError}</p> : null}
              {assetFormMessage ? <p className="form-message success">{assetFormMessage}</p> : null}
              <button type="submit" className="primary-btn" disabled={assetSubmitting}>{assetSubmitting ? 'Adding asset…' : 'Add asset'}</button>
            </form>
          </article>

          <article className="action-card">
            <div className="action-card-header">
              <p className="eyebrow">Update twin</p>
              <h2>Create connection</h2>
              <p>Add a directed connection between existing assets.</p>
            </div>
            <form className="twin-form" onSubmit={handleConnectionSubmit}>
              <div className="form-grid">
                <label>
                  <span>Source asset *</span>
                  <select value={connectionForm.source} onChange={(e) => setConnectionForm({ ...connectionForm, source: e.target.value })} required>
                    <option value="">Select source</option>
                    {assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.name} ({asset.id})</option>)}
                  </select>
                </label>
                <label>
                  <span>Target asset *</span>
                  <select value={connectionForm.target} onChange={(e) => setConnectionForm({ ...connectionForm, target: e.target.value })} required>
                    <option value="">Select target</option>
                    {assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.name} ({asset.id})</option>)}
                  </select>
                </label>
                <label><span>Protocol</span><input value={connectionForm.protocol} onChange={(e) => setConnectionForm({ ...connectionForm, protocol: e.target.value })} placeholder="tcp" /></label>
                <label><span>Port</span><input value={connectionForm.port} onChange={(e) => setConnectionForm({ ...connectionForm, port: e.target.value })} placeholder="443" inputMode="numeric" /></label>
                <label>
                  <span>Allowed</span>
                  <select value={connectionForm.allowed} onChange={(e) => setConnectionForm({ ...connectionForm, allowed: e.target.value })}>
                    <option value="true">Allowed</option>
                    <option value="false">Denied</option>
                    <option value="unknown">Unknown</option>
                  </select>
                </label>
                <label className="span-2"><span>Evidence</span><input value={connectionForm.evidence} onChange={(e) => setConnectionForm({ ...connectionForm, evidence: e.target.value })} placeholder="Firewall rule / compose network / security group" /></label>
              </div>
              {connectionFormError ? <p className="form-message error" role="alert">{connectionFormError}</p> : null}
              {connectionFormMessage ? <p className="form-message success">{connectionFormMessage}</p> : null}
              <button type="submit" className="primary-btn" disabled={connectionSubmitting || assets.length < 2}>
                {connectionSubmitting ? 'Creating connection…' : 'Create connection'}
              </button>
              {assets.length < 2 ? <p className="form-help">Add at least two assets to create a connection.</p> : null}
            </form>
          </article>
        </section>

        <section className="asset-list" aria-label="Asset inventory">
          <div className="inventory-heading"><span>Asset inventory</span><span>Exposure</span><span>Criticality</span></div>
          {assets.length === 0 ? (
            <div className="inventory-empty">No assets to display.</div>
          ) : (
            assets.map((asset) => (
              <button
                type="button"
                className={`inventory-row inventory-row-button${selectedAssetId === asset.id ? ' selected' : ''}`}
                key={asset.id}
                onClick={() => setSelectedAssetId(asset.id)}
              >
                <span>
                  <b>{asset.name}</b>
                  <small>{asset.id} • {asset.type} • IP: {asset.ip || 'N/A'} • Ports: {formatPorts(asset.ports)}</small>
                </span>
                <span>{asset.exposure || 'N/A'}</span>
                <span className={`criticality ${(asset.criticality || 'unknown').toLowerCase()}`}>{asset.criticality || 'Unknown'}</span>
              </button>
            ))
          )}
        </section>
      </section>
    </main>
  );
}
