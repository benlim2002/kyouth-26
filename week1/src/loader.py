from pathlib import Path
import json
import sqlite3
import logging
import hashlib


def load_sql(path):
    return open(path, "r", encoding="utf-8").read()

# setup db schema
def init_db(conn):
    cursor = conn.cursor()

    cursor.execute(load_sql("queries/create_table.sql"))

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

    logging.info("🥇 GOLD | Starting SQLite load process")

    for file in json_files:
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            hash_input = f"{data['job_title']}|{data['company']}|{data['description']}"
            content_hash = hashlib.sha256(hash_input.encode()).hexdigest()

            cursor.execute(load_sql("queries/insert_job.sql"), (
                data["source_id"],
                data["job_title"],
                data["company"],
                data["description"],
                content_hash,
                None
            ))

            if cursor.rowcount == 0:
                logging.warning(f"GOLD | ⏭️ Skipped duplicate record: {file.name}")
                skipped += 1
            else:
                logging.info(f"GOLD | ✅ Inserted: {file.name}")
                inserted += 1

        except Exception as e:
            logging.error(f"GOLD | ❌ Failed to process {file.name} | {e}")


    conn.commit()
    conn.close()

    print("\n📊 Gold Summary:")
    print(f"Total: {total} | Inserted: {inserted} | Skipped: {skipped} \n\n")