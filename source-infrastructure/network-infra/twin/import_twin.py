import json
import os
from pathlib import Path
from neo4j import GraphDatabase

INVENTORY = Path('/app/inventory')

def load_json(name):
    return json.loads((INVENTORY / name).read_text(encoding='utf-8'))

def main():
    driver = GraphDatabase.driver(os.getenv('NEO4J_URI', 'bolt://neo4j:7687'), auth=(os.getenv('NEO4J_USER', 'neo4j'), os.getenv('NEO4J_PASSWORD', 'netra_password')))
    with driver.session() as session:
        session.run('CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (asset:Asset) REQUIRE asset.id IS UNIQUE')
        for asset in load_json('assets.json'):
            session.run("MERGE (asset:Asset {id: $id}) SET asset.name=$name, asset.type=$type, asset.ip=$ip, asset.ports=$ports, asset.exposure=$exposure, asset.criticality=$criticality, asset.source='network-fixture'", **asset)
        for connection in load_json('connections.json'):
            session.run('MATCH (source:Asset {id: $source}) MATCH (target:Asset {id: $target}) MERGE (source)-[link:CONNECTS_TO]->(target) SET link.protocol=$protocol, link.port=$port, link.allowed=$allowed, link.evidence=$evidence', **connection)
    driver.close()

if __name__ == '__main__':
    main()
