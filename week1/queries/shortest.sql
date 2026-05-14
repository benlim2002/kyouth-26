SELECT source_id, job_title, LENGTH(description)
FROM jobs
WHERE description IS NOT NULL
ORDER BY LENGTH(description) ASC
LIMIT 1;