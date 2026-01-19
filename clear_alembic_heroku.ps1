$cmd = @'
python -c "from database import engine; from sqlalchemy import text; c = engine.connect(); r = c.execute(text('DELETE FROM alembic_version')); c.commit(); print('OK')"
'@

& "C:\Program Files\heroku\bin\heroku.cmd" run $cmd --app metal-tracker-tn
