import sqlite3
import time
import os
import sys
from dotenv import load_dotenv
from prompt_model import prompt_model

load_dotenv()

BATCH_SIZE = 5
RETRY_LIMIT = 3
RETRY_DELAY = 5


def build_prompt(jobs: list[dict]) -> str:
    lines = []
    for job in jobs:
        lines.append(f"JOB_ID: {job['source_id']}")
        lines.append(f"DESCRIPTION: {job['description'][:1000]}")
        lines.append("")
    prompt = (
        "You are a technical recruiter assistant. "
        "For each job below, extract a comma-separated list of technical skills, tools, frameworks, and programming languages "
        "mentioned or strongly implied in the description. Be concise. No explanations.\n"
        "Use official standardized names (e.g. 'Spring Boot' not 'Spring Framework/Spring Boot', 'PostgreSQL' not 'relational databases'). "
        "Do not combine multiple skills into one entry. "
        "Exclude job responsibilities, soft skills, and vague terms like 'design', 'deployment', 'security', 'testing'.\n\n"
        "Respond ONLY in this exact format, one line per job:\n"
        "JOB_ID: <id> | TECH: <comma separated skills>\n\n"
        + "\n".join(lines)
    )
    return prompt


# Parse back response into tech_stack according to their source_id
def parse_response(response_text: str, expected_ids: list[str]) -> dict[str, str]:
    results = {}
    for line in response_text.strip().splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        try:
            id_part, tech_part = line.split("|", 1)
            source_id = id_part.replace("JOB_ID:", "").strip()
            tech_stack = tech_part.replace("TECH:", "").strip()
            if source_id in expected_ids and tech_stack:  # check for empty tech stack upon parsing back to db 
                results[source_id] = tech_stack if tech_stack else "N/A"
        except Exception:
            continue
    return results


def estimate_tokens(text: str) -> int:
    """Fallback token estimator: 4 tokens per word."""
    return len(text.split()) * 4


# Get untagged jobs
def tag_data(db_url: str, model: str):

    start_time = time.time()
    total_tokens = 0

    try:
        with sqlite3.connect(db_url) as conn:  # Fix #4: context manager
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                "SELECT source_id, description FROM jobs WHERE tech_stack IS NULL OR tech_stack = ''"
            )
            rows = [dict(row) for row in cur.fetchall()]

            if not rows:
                print("No data to tag")
                elapsed = (time.time() - start_time) * 1000
                print(f"Total tokens used: 0, took {elapsed:.3f}ms")
                return 0, elapsed

            for batch_num in range(0, len(rows), BATCH_SIZE):
                batch = rows[batch_num: batch_num + BATCH_SIZE]
                remaining = {job["source_id"]: job for job in batch}  # Fix #2: track remaining

                for attempt in range(1, RETRY_LIMIT + 1):
                    if not remaining:
                        break

                    prompt = build_prompt(list(remaining.values()))

                    try:
                        response_text, tokens = prompt_model(model, prompt)  # Fix #5: real tokens
                        total_tokens += tokens

                        if response_text.startswith("["):
                            raise RuntimeError(response_text)

                        results = parse_response(response_text, list(remaining.keys()))

                        # Write successful results immediately  # Fix #2: partial writes
                        for source_id, tech_stack in results.items():
                            try:
                                cur.execute(
                                    "UPDATE jobs SET tech_stack = ? WHERE source_id = ?",
                                    (tech_stack, source_id),
                                )
                                conn.commit()
                                print(f"Analyzed Job {source_id}: {tech_stack}")
                                remaining.pop(source_id, None)  # Remove from retry pool
                            except Exception as e:
                                print(f"[DB Error] Failed to update job {source_id}: {e}")

                        if remaining:
                            print(
                                f"[Batch {batch_num // BATCH_SIZE}] Attempt {attempt}: "
                                f"{len(remaining)} job(s) still missing, retrying..."
                            )
                            if attempt < RETRY_LIMIT:
                                time.sleep(RETRY_DELAY)

                    except Exception as e:
                        print(f"[Batch {batch_num // BATCH_SIZE}] Attempt {attempt} failed: {e}")
                        if attempt < RETRY_LIMIT:
                            time.sleep(RETRY_DELAY)

                for source_id in remaining:
                    print(f"[Warning] Could not parse tech stack for Job {source_id}, skipping.")
                    try:
                        cur.execute(
                            "UPDATE jobs SET tech_stack = ? WHERE source_id = ?",
                            ("N/A", source_id),
                        )
                        conn.commit()
                    except Exception as e:
                        print(f"[DB Error] Failed to set N/A for job {source_id}: {e}")

    except Exception as e:
        print(f"[DB Error] Failed to read database: {e}")
        return 0, 0

    elapsed = (time.time() - start_time) * 1000
    print(f"Total tokens used: {total_tokens}, took {elapsed:.3f}ms")
    return total_tokens, elapsed


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/jobs_d1.db"

    selected_model = "llama3.1"
    print(f"Using model: {selected_model}\n")

    tag_data(db_path, selected_model)