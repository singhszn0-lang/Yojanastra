
from sqlalchemy import text
from database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database(), version()")
        )
        row = result.fetchone()
        print("Database connected successfully!")
        print("Database:", row[0])
        print("PostgreSQL:", row[1])
except Exception as error:
    print("Database connection failed:", error)
