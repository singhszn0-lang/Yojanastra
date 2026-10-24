
from sqlalchemy import text
from database import engine

with engine.begin() as conn:
    conn.execute(
        text("""
            ALTER TABLE applications
            ADD COLUMN IF NOT EXISTS household_id VARCHAR(100)
        """)
    )
    conn.execute(
        text("""
            ALTER TABLE citizens
            ADD COLUMN IF NOT EXISTS household_id VARCHAR(100)
        """)
    )
    conn.execute(
        text("""
            ALTER TABLE citizens
            ADD COLUMN IF NOT EXISTS phone VARCHAR(20),
            ADD COLUMN IF NOT EXISTS aadhaar_last4 VARCHAR(4),
            ADD COLUMN IF NOT EXISTS family_annual_income NUMERIC(12, 2),
            ADD COLUMN IF NOT EXISTS class_12_percentile NUMERIC(5, 2),
            ADD COLUMN IF NOT EXISTS regular_course BOOLEAN,
            ADD COLUMN IF NOT EXISTS receives_other_scholarship BOOLEAN
        """)
    )

print("application and family profile columns ready")
