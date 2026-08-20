type CloudAsset = {
  id: string;
  name: string;
  type: string;
  exposure: string;
  criticality: string;
  detail: string;
};

const assets: CloudAsset[] = [
  { id: 'internet', name: 'Public internet', type: 'External', exposure: 'External', criticality: 'Low', detail: '0.0.0.0/0' },
  { id: 'netra-web', name: 'netra-web', type: 'EC2 instance', exposure: 'Public', criticality: 'Medium', detail: '13.234.77.150 / port 80' },
  { id: 'netra-api', name: 'netra-api', type: 'EC2 instance', exposure: 'Internal', criticality: 'High', detail: '10.0.2.26 / port 8000' },
  { id: 'netra-db', name: 'netra-db', type: 'RDS PostgreSQL', exposure: 'Private', criticality: 'Critical', detail: 'ap-south-1 / port 5432' },
];

export default function CloudTwin() {
  return (
    <main className="twin-shell cloud-twin-shell">
      <header className="twin-header">
        <a className="brand" href="#home"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span><span>NETRA</span></a>
        <a className="back-link" href="#home">← Back to environments</a>
      </header>

      <section className="twin-main" aria-labelledby="cloud-title">
        <div className="twin-intro"><p className="eyebrow">Cloud twin / AWS fixture</p><h1 id="cloud-title">Cloud <em>topology.</em></h1><p>VPC services mapped across the public, application, and database tiers. Follow the permitted route through the cloud environment.</p></div>
        <div className="health"><span className="status-dot" /> Inventory loaded <b>4 assets</b><b>ap-south-1</b></div>

        <section className="topology" aria-label="Cloud infrastructure topology">
          {assets.map((asset, index) => <div className="topology-step" key={asset.id}>
            <article className={`asset-node ${asset.id}`}>
              <span className="node-kind">{asset.type}</span><strong>{asset.name}</strong><span className="node-id">{asset.id}</span>
              <span className={`exposure ${asset.exposure.toLowerCase()}`}>{asset.exposure}</span>
            </article>
            {index < assets.length - 1 && <div className="connection"><span>ALLOWED</span><b>{assets[index + 1].detail.match(/port (\d+)/)?.[1] ?? 'VPC'}</b><i /></div>}
          </div>)}
        </section>

        <section className="asset-list" aria-label="Cloud asset inventory">
          <div className="inventory-heading"><span>Cloud asset inventory</span><span>Exposure</span><span>Criticality</span></div>
          {assets.map(asset => <div className="inventory-row" key={asset.id}><span><b>{asset.name}</b><small>{asset.detail}</small></span><span>{asset.exposure}</span><span className={`criticality ${asset.criticality.toLowerCase()}`}>{asset.criticality}</span></div>)}
        </section>
      </section>
    </main>
  );
}