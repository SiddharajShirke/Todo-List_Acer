import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Load environment variables from .env
load_dotenv()

db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("DATABASE_URL not found in .env")
    exit(1)

print(f"Connecting to database...")
engine = create_engine(db_url)

with open('supabase_schema.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

print("Wiping existing schema to ensure a completely fresh start...")
# Use raw connection to execute multiple statements safely
conn = engine.raw_connection()
try:
    cursor = conn.cursor()
    cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO postgres; GRANT ALL ON SCHEMA public TO public;")
    
    print("Applying schema (tables, indexes, triggers, RLS)...")
    cursor.execute(sql)
    conn.commit()
    print("Schema applied successfully!")
except Exception as e:
    conn.rollback()
    print(f"Error applying schema: {e}")
    exit(1)
finally:
    conn.close()
