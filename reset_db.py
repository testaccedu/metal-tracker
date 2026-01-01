"""Reset database tables and run migration"""
from database import engine
from models import Base
import models

print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("Creating all tables...")
Base.metadata.create_all(bind=engine)
print("Tables recreated!")
