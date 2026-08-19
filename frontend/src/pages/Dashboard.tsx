type TwinOption = {
  name: string;
  label: string;
  description: string;
  action: string;
  className: string;
};

const twinOptions: TwinOption[] = [
  {
    name: 'Network Twin',
    label: 'On-premise infrastructure',
    description: 'Map your network estate, reveal attack paths, and test defensive decisions before they reach production.',
    action: 'Open network twin',
    className: 'network',
  },
  {
    name: 'Cloud Twin',
    label: 'Cloud infrastructure',
    description: 'Model cloud services and identity relationships to understand exposure across your cloud environment.',
    action: 'Open cloud twin',
    className: 'cloud',
  },
];

export default function Dashboard() {
  const enterTwin = (twin: string) => {
    window.location.hash = twin === 'Network Twin' ? 'network-twin' : 'cloud-twin';
  };

  return (
    <main className="shell">
      <div className="backdrop" aria-hidden="true" />
      <div className="grid-glow" aria-hidden="true" />

      <nav className="topbar" aria-label="Primary navigation">
        <a className="brand" href="#home" aria-label="NETRA home">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <span>NETRA</span>
        </a>
        <div className="nav-status"><span className="status-dot" /> Systems online</div>
      </nav>

      <section className="content" aria-labelledby="dashboard-title">
        <p className="eyebrow">Cybersecurity digital twin</p>
        <h1 id="dashboard-title">Choose your<br /><em>environment.</em></h1>
        <p className="intro">A unified view of your infrastructure, built for understanding risk before it becomes impact.</p>

        <div className="twin-options">
          {twinOptions.map((twin, index) => (
            <button
              className={`twin-card ${twin.className}`}
              key={twin.name}
              type="button"
              onClick={() => enterTwin(twin.name)}
              aria-label={twin.action}
            >
              <span className="card-topline"><span>0{index + 1}</span><span className="line" /></span>
              <span className="card-visual" aria-hidden="true">
                <span className="node node-a" /><span className="node node-b" /><span className="node node-c" />
              </span>
              <span className="card-copy">
                <span className="card-label">{twin.label}</span>
                <strong>{twin.name}</strong>
                <span className="card-description">{twin.description}</span>
              </span>
              <span className="card-action">{twin.action}<b aria-hidden="true">→</b></span>
            </button>
          ))}
        </div>
      </section>

      <footer><span>NETRA Security Intelligence</span><span>Digital Twin Platform</span></footer>
    </main>
  );
}
