from pathlib import Path
import json
import sqlite3


# setup db schema
def init_db(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            source_id TEXT PRIMARY KEY,
            job_title TEXT,
            company TEXT,
            description TEXT,
            tech_stack TEXT DEFAULT NULL
        )
    """)

    conn.commit()


# main loader function
def load_all_jsons(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    db_path = output_dir / "jobs.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    init_db(conn)

    json_files = list(input_dir.glob("*.json"))

    total = len(json_files)
    inserted = 0
    skipped = 0

    print("🥇 Gold: Loading data into SQLite...\n")

    for file in json_files:
        try:
            data = json.loads(file.read_text(encoding="utf-8"))

            cursor.execute("""
                INSERT OR IGNORE INTO jobs (source_id, job_title, company, description)
                VALUES (?, ?, ?, ?)
            """, (
                data["source_id"],
                data["job_title"],
                data["company"],
                data["description"]
            ))

            if cursor.rowcount == 0:
                print(f"⏭️ Skipped (duplicate): {file.name}")
                skipped += 1
            else:
                print(f"✅ Inserted: {file.name}")
                inserted += 1

        except Exception as e:
            print(f"❌ Failed: {file.name} | {e}")

    conn.commit()
    conn.close()

    print("\n📊 Gold Summary:")
    print(f"Total: {total} | Inserted: {inserted} | Skipped: {skipped}")