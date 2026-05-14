SELECT source_id, job_title, LENGTH(description)
FROM jobs
WHERE description IS NOT NULL
ORDER BY LENGTH(description) DESC
LIMIT 1;