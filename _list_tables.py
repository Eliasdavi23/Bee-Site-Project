from config.database import get_connection

conn = get_connection()
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
for t in tables:
    name = t['name']
    c = conn.execute(f"SELECT COUNT(*) as c FROM {name}").fetchone()['c']
    print(f"- {name}: {c} registros")
