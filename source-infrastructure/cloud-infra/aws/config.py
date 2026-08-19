"""Cloud discovery configuration constants and environment loader."""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Directory paths
# ---------------------------------------------------------------------------
CLOUD_INFRA_DIR = Path(__file__).resolve().parent.parent
FIXTURE_DIR = CLOUD_INFRA_DIR / "fixtures"
INVENTORY_DIR = CLOUD_INFRA_DIR / "inventory"

# ---------------------------------------------------------------------------
# AWS settings
# ---------------------------------------------------------------------------
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# ---------------------------------------------------------------------------
# Neo4j settings (for graph importer)
# ---------------------------------------------------------------------------
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "netra_password")

# ---------------------------------------------------------------------------
# NETRA cloud infrastructure identifiers
# ---------------------------------------------------------------------------
NETRA_VPC_ID = "vpc-0ddb37d784b88bc5b"
NETRA_REGION = "ap-south-1"
