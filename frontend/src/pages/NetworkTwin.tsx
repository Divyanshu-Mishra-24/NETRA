const assets = [
  { id: 'internet', name: 'Internet', type: 'External', exposure: 'External', criticality: 'Low', port: '8080' },
  { id: 'web-01', name: 'Nginx Web Server', type: 'Web server', exposure: 'Public', criticality: 'Medium', port: '80' },
  { id: 'api-01', name: 'FastAPI Server', type: 'API server', exposure: 'Internal', criticality: 'High', port: '8000' },
  { id: 'db-01', name: 'PostgreSQL Database', type: 'Database', exposure: 'Private', criticality: 'Critical', port: '5432' },
];

export default function NetworkTwin() {
  return (
    <main className="twin-shell">
      <header className="twin-header">
        <a className="brand" href="#home"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span><span>NETRA</span></a>
        <a className="back-link" href="#home">← Back to environments</a>
      </header>

      <section className="twin-main" aria-labelledby="network-title">
        <div className="twin-intro"><p className="eyebrow">Network twin / live model</p><h1 id="network-title">Network <em>topology.</em></h1><p>Source infrastructure copied into a virtual model. Follow the allowed flow from the public edge to the protected database.</p></div>
        <div className="health"><span className="status-dot" /> Inventory loaded <b>4 assets</b></div>

        <section className="topology" aria-label="Network infrastructure topology">
          {assets.map((asset, index) => <div className="topology-step" key={asset.id}>
            <article className={`asset-node ${asset.id}`}>
              <span className="node-kind">{asset.type}</span><strong>{asset.name}</strong><span className="node-id">{asset.id}</span>
              <span className={`exposure ${asset.exposure.toLowerCase()}`}>{asset.exposure}</span>
            </article>
            {index < assets.length - 1 && <div className="connection"><span>TCP</span><b>{assets[index + 1].port}</b><i /></div>}
          </div>)}
        </section>

        <section className="asset-list" aria-label="Asset inventory">
          <div className="inventory-heading"><span>Asset inventory</span><span>Exposure</span><span>Criticality</span></div>
          {assets.map(asset => <div className="inventory-row" key={asset.id}><span><b>{asset.name}</b><small>{asset.id} / Port {asset.port}</small></span><span>{asset.exposure}</span><span className={`criticality ${asset.criticality.toLowerCase()}`}>{asset.criticality}</span></div>)}
        </section>
      </section>
    </main>
  );
}
