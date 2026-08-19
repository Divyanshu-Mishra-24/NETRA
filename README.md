# NETRA

### AI-Powered Cloud Infrastructure Digital Twin for Attack-Path Prediction and Security Simulation

CYBER-TWIN is a final-year major project that creates a graph-based digital twin of a small cloud infrastructure. It combines infrastructure discovery, vulnerability intelligence, attack-graph analysis, machine learning, honeypot telemetry, non-destructive what-if simulation, and a read-only AI security analyst in a SOC-style dashboard.

The system is designed for safe academic analysis. It simulates compromise and propagation on an abstract graph model; it does **not** exploit live systems, attack production infrastructure, or target third-party assets.

## Project Objectives

- Model cloud assets and their dependencies as a digital twin.
- Enrich assets with vulnerabilities, exposure, and security context.
- Compute and visualize possible attack paths.
- Score asset risk and rank likely attack paths with AI/ML.
- Detect anomalous activity from honeypot telemetry.
- Simulate compromise, apply hypothetical mitigations, and compare risk.
- Explain security findings in plain language through a grounded, read-only LLM analyst.

## Core Features

### Infrastructure Discovery and Modelling

- Manual entry of assets, services, ports, operating systems, and relationships.
- Optional AWS discovery for EC2, VPC, RDS, and Security Groups through `boto3`.
- A normalized asset schema shared by manual and cloud-discovered resources.

### Digital Twin Graph Engine

- Infrastructure assets represented as graph nodes.
- Connections and dependencies represented as directed edges.
- Neo4j persistence with native Cypher path queries.
- Typed graph operations exposed through the FastAPI backend.

### Vulnerability Mapping

- CVE ID, severity, and description attached to relevant assets.
- NVD API lookups by service and version, with local caching.
- Manual vulnerability entry and override for controlled demo scenarios.
- Exposure classification for internet-facing and internal assets.

### Attack Graph and Simulation

- All-path and shortest-path queries between selected assets.
- Breadth-first compromise propagation from a chosen entry node.
- Firewall and security-group constraints represented on graph edges.
- Affected assets, path sequence, and aggregate risk returned for every simulation.

### AI Engine

- **Risk scoring:** combines vulnerability severity, exposure, graph connectivity, and asset criticality.
- **Attack-path ranking:** ranks candidate paths with a gradient-boosted classifier trained on synthetic scenario outcomes.
- **Anomaly detection:** uses Isolation Forest over telemetry features such as event rate, source diversity, and authentication-failure ratio.

### Honeypot Telemetry

- Near-real-time ingestion from the existing multi-port honeypot.
- Normalization of logs into a common telemetry event schema.
- Mapping of observed activity, such as SSH brute-force attempts, to the relevant graph asset.
- Optional automatic simulation when an event crosses a severity threshold.

### What-If Simulation

- Mark an asset as hypothetically compromised.
- Apply a proposed mitigation, such as blocking an edge or patching a CVE.
- Re-run the scenario and compare before/after risk.
- Persist results as independent scenarios without modifying real asset or relationship records.

### LLM Security Analyst

- Answers natural-language questions using the twin's structured data.
- Grounds explanations in asset, CVE, exposure, and attack-path evidence.
- References the data points used in each response.
- Has no graph-write permission, cloud credentials, or infrastructure control path.

### SOC-Style Dashboard

- Interactive infrastructure graph with pan, zoom, and node inspection.
- Green, amber, and red risk visualization.
- Asset detail panel for OS, ports, vulnerabilities, risk factors, and recommended action.
- Simulation console for before/after comparisons.
- Live telemetry updates through WebSocket or Server-Sent Events.
- Analyst chat for grounded security explanations.


## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI |
| AI/ML | scikit-learn, XGBoost, optional PyTorch |
| Graph database | Neo4j, Cypher, Bolt protocol |
| Relational database | PostgreSQL |
| Frontend | React, TypeScript, Tailwind CSS, React Flow, D3.js |
| Cloud integration | AWS EC2, VPC, RDS, Security Groups, CloudWatch, S3, IAM |
| Infrastructure | Docker, Docker Compose, optional Terraform |
| Automation | GitHub Actions |
| External data | NVD/CVE REST API |
| AI explanation | OpenAI, Claude, or a compatible local LLM |

## Data Model

### Neo4j Graph

| Node label | Key properties |
|---|---|
| `Asset` | `id`, `name`, `type`, `ip`, `os`, `ports`, `criticality`, `exposure`, `risk_score` |
| `Vulnerability` | `cve_id`, `severity`, `description` |
| `TelemetryEvent` | `source`, `event_type`, `timestamp`, `severity` |
| `Scenario` | `id`, `created_by`, `entry_node`, `target_node`, `risk_before`, `risk_after` |

| Relationship | Direction | Key properties |
|---|---|---|
| `CONNECTS_TO` / `DEPENDS_ON` | Asset → Asset | `allowed` |
| `HAS_VULNERABILITY` | Asset → Vulnerability | — |
| `OBSERVED_ON` | TelemetryEvent → Asset | — |
| `COMPROMISES` / `TARGETS` | Scenario → Asset | — |

### PostgreSQL

| Table | Purpose |
|---|---|
| `users` | Accounts, password hashes, and Administrator/Analyst/Evaluator roles |
| `audit_log` | User actions, affected targets, and timestamps |
| `cve_cache` | Cached NVD vulnerability data and retrieval timestamps |

Neo4j remains the source of truth for infrastructure topology. PostgreSQL stores transactional and naturally tabular application data.

## Key API Endpoints

FastAPI generates the full OpenAPI specification at `/docs`. The central API contracts are:

| Method and path | Purpose |
|---|---|
| `POST /assets` | Create or import an infrastructure asset |
| `POST /assets/{id}/connect` | Create a connection to another asset |
| `GET /graph` | Fetch the full graph or a filtered subgraph |
| `GET /graph/paths?from=&to=` | Return attack paths between two assets |
| `POST /simulate` | Run compromise propagation and risk scoring |
| `POST /simulate/mitigate` | Apply a hypothetical mitigation and re-run a scenario |
| `POST /telemetry/ingest` | Ingest a normalized honeypot event |
| `POST /analyst/ask` | Ask the read-only LLM security analyst a question |
| `GET /assets/{id}/risk` | Get an asset's risk score and contributing factors |

## Suggested Repository Structure

```text
CYBER-TWIN/
├── backend/
│   ├── app/
│   │   ├── api/                 # REST and live-update endpoints
│   │   ├── core/                # Configuration, security, and shared utilities
│   │   ├── graph/               # Neo4j access and graph operations
│   │   ├── models/              # Domain and persistence models
│   │   ├── services/            # Discovery, CVE, attack, telemetry, and simulation
│   │   ├── ai/                  # Risk, path-ranking, and anomaly models
│   │   ├── analyst/             # Read-only LLM context and prompts
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── types/
│   └── package.json
├── honeypot/                    # Existing honeypot integration
├── infrastructure/             # Optional Terraform configuration
├── models/                      # Versioned ML artifacts and metadata
├── docs/                        # SRS, design, API, and demo documentation
├── docker-compose.yml
├── .env.example
└── README.md
```

This structure is the intended architecture and may be adjusted as implementation progresses.

## Getting Started

### Prerequisites

- Git
- Docker Engine and Docker Compose
- 8–16 GB RAM recommended for the complete local stack
- Optional AWS free-tier/sandbox account for cloud discovery
- Optional NVD and LLM API credentials

### 1. Clone the repository

```bash
git clone https://github.com/Divyanshu-Mishra-24/Netra.git
cd Netra
```

Update the repository URL and directory name if the project repository is renamed to `CYBER-TWIN`.

### 2. Configure environment variables

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure the values required by your implementation, including:

- Neo4j URI and credentials
- PostgreSQL connection details
- NVD API key, when used
- LLM provider and API key, when used
- AWS region and credentials, only for the team-owned sandbox account
- Authentication secrets

Never commit `.env`, database credentials, cloud keys, or LLM API keys.

### 3. Start the local stack

```bash
docker compose up --build
```

Once the services are healthy, open the frontend URL defined in `docker-compose.yml`. The FastAPI documentation is available from the backend at `/docs`.

### 4. Stop the stack

```bash
docker compose down
```

Add `-v` only when you intentionally want to remove local database volumes and reset stored data.

## Development and Testing

Typical checks should cover:

- Unit tests for typed graph operations and attack-path algorithms.
- API tests for asset, graph, simulation, telemetry, and analyst endpoints.
- Invariant tests proving scenario operations cannot mutate the live graph.
- Model evaluation for path ranking and anomaly detection.
- Malformed and partial telemetry handling.
- Role-based access control for all mutating endpoints.
- End-to-end execution of compromise → mitigation → re-simulation.

Performance targets for the academic system are:

- Graph queries over infrastructures of up to approximately 50 nodes within 2 seconds.
- What-if results displayed within 3 seconds.
- Full what-if demo completed by a first-time evaluator in fewer than 5 clicks.
- Local Docker Compose setup completed in under 15 minutes.

## User Roles

| Role | Access |
|---|---|
| Administrator | Configure assets, cloud integration, users, and honeypot connectivity |
| Security Analyst | Explore the twin, inspect findings, and run simulations |
| Evaluator | Read-only access to dashboards, scenarios, and reports |

## Security, Ethics, and Safety

- CYBER-TWIN performs **no real exploitation**.
- Simulated attacks operate only on the abstract graph model.
- The honeypot observes traffic only on systems owned and controlled by the team.
- The system does not initiate attacks or target third-party infrastructure.
- The LLM analyst is advisory and read-only.
- All demo cloud resources must be team-owned, isolated, and removed after evaluation.
- Credentials must be stored in environment variables or an approved secrets manager.
- All external and inter-service communication should use HTTPS/TLS.
- Synthetic or controlled data should be used when real telemetry is unavailable or unsafe.

## Development Roadmap

| Phase | Focus | Key deliverable |
|---|---|---|
| 0 | Setup | Repository, Docker Compose, FastAPI, React, Neo4j, and PostgreSQL skeleton |
| 1 | Core Twin | Manual asset entry, Neo4j graph, and basic graph visualization |
| 2 | Vulnerability Layer | CVE lookup, manual vulnerability entry, exposure, and risk fields |
| 3 | Attack Graph | Path computation, propagation simulation, and results panel |
| 4 | AI Engine v1 | Heuristic risk scoring and attack-path ranking |
| 5 | Honeypot Integration | Event ingestion and mapping to graph assets |
| 6 | What-If Engine | Compromise, mitigate, re-simulate, and show risk reduction |
| 7 | AI Engine v2 | Anomaly detection and model evaluation |
| 8 | LLM Analyst | Grounded, read-only security Q&A |
| 9 | Cloud Integration | AWS discovery and CloudWatch telemetry |
| 10 | Polish and Report | Dashboard polish, RBAC, Terraform, documentation, and final report |

The planned duration is approximately 26–30 weeks across two academic semesters.
