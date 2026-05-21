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
    """Build a batched prompt for a list of jobs."""
    lines = []
    for job in jobs:
        lines.append(f"JOB_ID: {job['source_id']}")
        lines.append(f"DESCRIPTION: {job['description'][:1000]}")
        lines.append("")

    prompt = (
        "You are a technical recruiter assistant. "
        "For each job below, extract a comma-separated list of technical skills, tools, and frameworks "
        "mentioned or strongly implied in the description. Be concise. No explanations.\n\n"
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
                results[source_id] = tech_stack
            else:
                results[source_id] = "N/A"
        except Exception:
            continue
    return results


def estimate_tokens(text: str) -> int:
    """Fallback token estimator: 4 tokens per word."""
    return len(text.split()) * 4


# Get untagged jobs
def tag_data(db_url: str, model: str = "gemini-2.5-flash"):

    start_time = time.time()
    total_tokens = 0

    #Fetch untagged rows
    try:
        conn = sqlite3.connect(db_url)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT source_id, description FROM jobs WHERE tech_stack IS NULL OR tech_stack = ''"
        )
        rows = [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"[DB Error] Failed to read database: {e}")
        return 0, 0

    if not rows:
        print("No data to tag")
        elapsed = (time.time() - start_time) * 1000
        print(f"Total tokens used: 0, took {elapsed:.3f}ms")
        return 0, elapsed

    #Process in batches
    for batch_num in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_num: batch_num + BATCH_SIZE]
        expected_ids = [job["source_id"] for job in batch]
        prompt = build_prompt(batch)

        results = {}
        for attempt in range(1, RETRY_LIMIT + 1):
            try:
                response_text = prompt_model(model, prompt)

                #Check if prompt_model returned an error string
                if response_text.startswith("["):
                    raise RuntimeError(response_text)

                #Estimate tokens (fallback since prompt_model returns plain string)
                total_tokens += estimate_tokens(prompt) + estimate_tokens(response_text)

                results = parse_response(response_text, expected_ids)

                if len(results) != len(batch):
                    print(
                        f"[Batch {batch_num // BATCH_SIZE}] Attempt {attempt} failed: "
                        f"Mismatch between batch size and response"
                    )
                    if attempt < RETRY_LIMIT:
                        time.sleep(RETRY_DELAY)
                    continue

                break  # success

            except Exception as e:
                print(f"[Batch {batch_num // BATCH_SIZE}] Attempt {attempt} failed: {e}")
                if attempt < RETRY_LIMIT:
                    time.sleep(RETRY_DELAY)

        # Write results to DB
        for source_id, tech_stack in results.items():
            try:
                cur.execute(
                    "UPDATE jobs SET tech_stack = ? WHERE source_id = ?",
                    (tech_stack, source_id),
                )
                conn.commit()
                print(f"Analyzed Job {source_id}: {tech_stack}")
            except Exception as e:
                print(f"[DB Error] Failed to update job {source_id}: {e}")

        # Log any jobs that couldn't be parsed
        missing = set(expected_ids) - set(results.keys())
        for source_id in missing:
            print(f"[Warning] Could not parse tech stack for Job {source_id}, skipping.")

    conn.close()

    elapsed = (time.time() - start_time) * 1000
    print(f"Total tokens used: {total_tokens}, took {elapsed:.3f}ms")
    return total_tokens, elapsed


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/jobs_d1.db"

    print("Select a model:")
    print("  1. gemini-2.5-flash")
    print("  2. gemini-2.5-flash-lite")
    print("  3. gemini-3-flash-preview")
    print("  4. llama3.1")
    print("  5. phi3")
    print("  6. deepseek-r1:1.5b")

    choice = input("Enter choice (1-6): ").strip()

    models = {
        "1": "gemini-2.5-flash",
        "2": "gemini-2.5-flash-lite",
        "3": "gemini-3-flash-preview",
        "4": "llama3.1",
        "5": "phi3",
        "6": "deepseek-r1:1.5b",
    }

    selected_model = models.get(choice, "gemini-2.5-flash")
    print(f"Using model: {selected_model}\n")

    tag_data(db_path, selected_model)