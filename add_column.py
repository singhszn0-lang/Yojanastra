
from sqlalchemy import text
from database import engine

with engine.begin() as conn:
    conn.execute(
        text("""
            ALTER TABLE applications
            ADD COLUMN IF NOT EXISTS household_id VARCHAR(100)
        """)
    )

print("household_id column ready")
