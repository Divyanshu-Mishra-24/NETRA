import type { Asset } from '../services/api';

interface AssetPanelProps {
  asset: Asset | null;
  onClose: () => void;
}

function formatPorts(ports: number[] | undefined): string {
  if (!ports || ports.length === 0) return 'None';
  return ports.join(', ');
}

export default function AssetPanel({ asset, onClose }: AssetPanelProps) {
  if (!asset) {
    return (
      <aside className="asset-panel empty" aria-label="Asset details panel">
        <div className="asset-panel-header">
          <h2>Asset details</h2>
        </div>
        <p>Select a node in the graph to view its details.</p>
      </aside>
    );
  }

  return (
    <aside className="asset-panel" aria-label="Asset details panel">
      <div className="asset-panel-header">
        <div>
          <p className="eyebrow">Selected asset</p>
          <h2>{asset.name}</h2>
        </div>
        <button type="button" className="panel-close" onClick={onClose} aria-label="Close asset details">
          ×
        </button>
      </div>

      <dl className="asset-details">
        <div><dt>ID</dt><dd>{asset.id}</dd></div>
        <div><dt>Name</dt><dd>{asset.name}</dd></div>
        <div><dt>Type</dt><dd>{asset.type}</dd></div>
        <div><dt>IP Address</dt><dd>{asset.ip || 'N/A'}</dd></div>
        <div><dt>Operating System</dt><dd>{asset.os || 'N/A'}</dd></div>
        <div><dt>Ports</dt><dd>{formatPorts(asset.ports)}</dd></div>
        <div><dt>Exposure</dt><dd>{asset.exposure || 'N/A'}</dd></div>
        <div><dt>Criticality</dt><dd>{asset.criticality || 'N/A'}</dd></div>
        {asset.source ? <div><dt>Source</dt><dd>{asset.source}</dd></div> : null}
      </dl>
    </aside>
  );
}
