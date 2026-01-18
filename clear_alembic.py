"""Clear alembic_version table to resolve multiple heads issue"""
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("DELETE FROM alembic_version"))
    conn.commit()
    print(f"[OK] Deleted {result.rowcount} rows from alembic_version")
