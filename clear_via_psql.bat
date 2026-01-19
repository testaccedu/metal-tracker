@echo off
"C:\Program Files\heroku\bin\heroku.cmd" pg:psql --app metal-tracker-tn --command "DELETE FROM alembic_version;"
