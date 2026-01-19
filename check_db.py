"""Quick DB check script"""
from database import SessionLocal
from models import User, Position, PortfolioSnapshot
import sys

db = SessionLocal()

try:
    users = db.query(User).all()
    positions = db.query(Position).all()
    snapshots = db.query(PortfolioSnapshot).all()

    print(f"Users: {len(users)}")
    for u in users:
        print(f"  - {u.email} (ID: {u.id})")

    print(f"\nPositions: {len(positions)}")
    for p in positions:
        print(f"  - User {p.user_id}: {p.metal_type} {p.weight_grams}g")

    print(f"\nSnapshots: {len(snapshots)}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    db.close()
