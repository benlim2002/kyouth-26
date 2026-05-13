import sqlite3
from pathlib import Path


def run_data_profile(db_path):
    db_path = Path(db_path)

    # handle db path not exist
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n--- 🔍 DATA QUALITY REPORT ---")


    # total records count
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_records = cursor.fetchone()[0]


    # missing values count for job_title, company, description
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN job_title IS NULL OR job_title = '' THEN 1 ELSE 0 END),
            SUM(CASE WHEN company IS NULL OR company = '' THEN 1 ELSE 0 END),
            SUM(CASE WHEN description IS NULL OR description = '' THEN 1 ELSE 0 END)
        FROM jobs
    """)
    missing_job_title, missing_company, missing_description = cursor.fetchone()


    # avg description length (exclude nulls)
    cursor.execute("""
        SELECT AVG(LENGTH(description))
        FROM jobs
        WHERE description IS NOT NULL
    """)
    avg_desc_length = cursor.fetchone()[0] or 0


    # shortest description    
    cursor.execute("""
        SELECT source_id, job_title, LENGTH(description)
        FROM jobs
        WHERE description IS NOT NULL
        ORDER BY LENGTH(description) ASC
        LIMIT 1
    """)
    shortest = cursor.fetchone()


    # description is not null and order by length desc to get longest description
    cursor.execute("""
        SELECT source_id, job_title, LENGTH(description)
        FROM jobs
        WHERE description IS NOT NULL
        ORDER BY LENGTH(description) DESC
        LIMIT 1
    """)
    longest = cursor.fetchone()


    # output report
    print(f"📈 Total Records: {total_records}")
    print(f"❓ Missing Values -> job_title: {missing_job_title or 0}, company: {missing_company or 0}, description: {missing_description or 0}")
    print(f"📝 Avg Description Length: {int(avg_desc_length)} chars")

    if shortest:
        print(f"⚠️ Shortest Description: {shortest[2]} chars")
        print(f"   ↳ source_id: {shortest[0]} | job_title: {shortest[1]}")

    if longest:
        print(f"🚨 Longest Description: {longest[2]} chars")
        print(f"   ↳ source_id: {longest[0]} | job_title: {longest[1]}")

    conn.close()