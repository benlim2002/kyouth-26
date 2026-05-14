import sqlite3
from pathlib import Path
import logging


def load_sql(path):
    return open(path, "r", encoding="utf-8").read()


def compute_quality(job_title, company, description):
    if not job_title or not company or not description:
        return "LOW"

    if len(description) < 100:
        return "LOW"

    if "!!!!" in description or "####" in description:
        return "LOW"

    return "HIGH"


def run_data_profile(db_path):
    db_path = Path(db_path)

    # handle db path not exist
    if not db_path.exists():
        logging.error(f"PROFILE | ❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    logging.info("PROFILE | 🔍 Starting data quality report")

    # total records count
    cursor.execute(load_sql("queries/count.sql"))
    total_records = cursor.fetchone()[0]


    # missing values count for job_title, company, description
    cursor.execute(load_sql("queries/missing.sql"))
    missing_job_title, missing_company, missing_description = cursor.fetchone()


    # avg description length (exclude nulls)
    cursor.execute(load_sql("queries/avg.sql"))
    avg_desc_length = cursor.fetchone()[0] or 0


    # shortest description    
    cursor.execute(load_sql("queries/shortest.sql"))
    shortest = cursor.fetchone()


    # description is not null and order by length desc to get longest description
    cursor.execute(load_sql("queries/longest.sql"))
    longest = cursor.fetchone()


    # output report
    logging.info(f"PROFILE | 📈 Total Records: {total_records}")
    logging.info(
    f"PROFILE | Missing Values -> job_title: {missing_job_title or 0}, "
    f"company: {missing_company or 0}, description: {missing_description or 0}"
    )
    logging.info(f"PROFILE | 📝 Avg Description Length: {int(avg_desc_length)} chars")

    if shortest:
        logging.info(f"PROFILE | ⚠️ Shortest Description: {shortest[2]} chars")
        logging.info(f"PROFILE |    ↳ source_id: {shortest[0]} | job_title: {shortest[1]}")

    if longest:
        logging.info(f"PROFILE | 🚨 Longest Description: {longest[2]} chars")
        logging.info(f"PROFILE |    ↳ source_id: {longest[0]} | job_title: {longest[1]}")


    # bonus 4: quality labelling
    logging.info("PROFILE | 🏷️ Starting quality labelling")
    
    cursor.execute("""
    SELECT source_id, job_title, company, description
    FROM jobs
    """)

    rows = cursor.fetchall()

    for source_id, job_title, company, description in rows:
        quality = compute_quality(job_title, company, description)

        cursor.execute("""
            UPDATE jobs
            SET quality = ?
            WHERE source_id = ?
        """, (quality, source_id))

    conn.commit()
    
    # count quality labels
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE quality = 'LOW'")
    low_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE quality = 'HIGH'")
    high_count = cursor.fetchone()[0]
    
    logging.info(f"PROFILE | Quality Labels -> HIGH: {high_count}, LOW: {low_count}")
        
    # quarantine low quality records
    cursor.execute("DROP TABLE IF EXISTS jobs_quarantine")

    cursor.execute("""
        CREATE TABLE jobs_quarantine (
            source_id TEXT PRIMARY KEY,
            job_title TEXT,
            company TEXT,
            description TEXT,
            tech_stack TEXT,
            quality TEXT
        )
    """)

    cursor.execute("""
        INSERT INTO jobs_quarantine (
            source_id,
            job_title,
            company,
            description,
            tech_stack,
            quality
        )
        SELECT
            source_id,
            job_title,
            company,
            description,
            tech_stack,
            quality
        FROM jobs
        WHERE quality = 'LOW'
    """)

    cursor.execute("""
        DELETE FROM jobs WHERE quality = 'LOW'
    """)

    conn.commit()
    
    logging.info(f"PROFILE | ✅ Moved {low_count} LOW quality records to jobs_quarantine")
    logging.info(f"PROFILE | ✅ Remaining HIGH quality records: {high_count}")


    conn.close()