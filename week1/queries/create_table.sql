CREATE TABLE IF NOT EXISTS jobs (
    source_id TEXT PRIMARY KEY,
    job_title TEXT,
    company TEXT,
    description TEXT,
    tech_stack TEXT DEFAULT NULL,
    content_hash TEXT,
    quality TEXT
)