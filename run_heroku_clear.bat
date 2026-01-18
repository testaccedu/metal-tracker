@echo off
"C:\Program Files\heroku\bin\heroku.cmd" run "python -c \"from database import engine; from sqlalchemy import text; conn = engine.connect(); result = conn.execute(text('DELETE FROM alembic_version')); conn.commit(); print(f'Deleted {result.rowcount} rows')\"" --app metal-tracker-tn
