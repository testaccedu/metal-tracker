# release: alembic upgrade head  # TEMPORARILY DISABLED for cleanup
web: gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
