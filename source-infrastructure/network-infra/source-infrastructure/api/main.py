import os
import psycopg
from fastapi import FastAPI

app = FastAPI(title="NETRA Source API")

def connection_string() -> str:
    return f"host={os.getenv('DB_HOST', 'source-db')} port={os.getenv('DB_PORT', '5432')} dbname={os.getenv('DB_NAME', 'college_app')} user={os.getenv('DB_USER', 'app_user')} password={os.getenv('DB_PASSWORD', 'local_demo_password')}"

@app.get('/health')
def health():
    return {"status": "healthy"}

@app.get('/students')
def students():
    with psycopg.connect(connection_string()) as connection, connection.cursor() as cursor:
        cursor.execute('SELECT id, name, department FROM students ORDER BY id')
        return [{"id": row[0], "name": row[1], "department": row[2]} for row in cursor.fetchall()]
