import sqlite3

def upgrade_db():
    conn = sqlite3.connect("dev.db")
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN channel_id BIGINT REFERENCES channels(id) ON DELETE SET NULL")
        print("Added channel_id to tasks.")
    except Exception as e:
        print("channel_id might exist:", e)
        
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN planned_date DATE")
        print("Added planned_date to tasks.")
    except Exception as e:
        print("planned_date might exist:", e)

    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN start_time TIME")
        print("Added start_time to tasks.")
    except Exception as e:
        print("start_time might exist:", e)

    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN end_time TIME")
        print("Added end_time to tasks.")
    except Exception as e:
        print("end_time might exist:", e)

    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN weekly_objective_id BIGINT REFERENCES weekly_objectives(id) ON DELETE SET NULL")
        print("Added weekly_objective_id to tasks.")
    except Exception as e:
        print("weekly_objective_id might exist:", e)

    conn.commit()
    conn.close()
    print("DB Upgrade Complete.")

if __name__ == "__main__":
    upgrade_db()
