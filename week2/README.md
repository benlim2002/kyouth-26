# Week 2: Job Tagging and Analyze

## Project Overview

This project is a two-part AI-assisted pipeline for job market analysis:

1. **Tag Data (`tag_data.py`)** — Reads raw job descriptions from a SQLite database and uses an LLM to extract and populate a `tech_stack` column with a comma-separated list of technical skills per job posting.
2. **Find Skill Gaps (`find_skill_gaps.py`)** — Reads a candidate's resume and the tagged job database to deterministically identify which technical skills are in demand across job listings but absent from the resume.

---

## Setup Instructions

### Prerequisites

- Python **3.14**
- [`uv`](https://docs.astral.sh/uv/) package manager (DOWNLOADED IN WEEK1)
- An [Ollama](https://ollama.com/) instance running locally (for local models), **or** a Google Gemini API key (for cloud models)


### 1. Clone the Repository

```bash
git clone [https://github.com/benlim2002/kyouth-26)]
cd <repo-folder>
```

### 2. Install Dependencies

```bash
uv sync
```

This will install all dependencies declared in `pyproject.toml` (or `requirements.txt`).

### 3. Configure Google API Key

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=
```


### 4. Set Up Ollama (if using local models)

```bash
# Install Ollama from https://ollama.com, then pull the required model:
ollama pull llama3.1
```

Ollama running at `http://127.0.0.1:11434` before executing any script.

---

## Usage

### Tag Job Data

Populates the `tech_stack` column for all untagged rows in the `jobs` table:

```bash
uv run tag_data.py 
```



### Find Skill Gaps

Compares a resume against all tagged job tech stacks and outputs missing skills:

```bash
uv run find_skill_gaps.py 
```


## API / Function Reference

### `prompt_model.py`

Unified interface for querying LLM backends.

#### `prompt_model(model: str, prompt: str) -> tuple[str, int]`
- Purpose: Routes a prompt to either a local Ollama model or Google Gemini, during testing it would prompt the models based on the names, but now is hardcoded to llama3.1 model.
- Inputs: `model` — model identifier string; `prompt` — the full prompt text.
- Outputs: `(response_text, token_count)` — the model's raw text response and total tokens used.

#### `prompt_google(model, prompt) -> tuple[str, int]`
- Prompts google model using the cached `genai.Client`. Returns response text and token usage.

#### `prompt_ollama(model, prompt) -> tuple[str, int]`
- Prompts ollama models.
  
---

### `tag_data.py`

#### `tag_data(db_url: str, model: str = "")`
- Purpose: Reads all untagged jobs from the `jobs` table and uses an LLM to extract their technical stacks, then writing back to db.
- Inputs: `db_url` — path to the SQLite database file; `model` — LLM model name.
- Outputs: `(total_tokens, elapsed_ms)` — usage statistics.
- Behavior:
  - Processes rows in batches of `BATCH_SIZE = 5`.
  - Retries up to `RETRY_LIMIT = 3` times per batch with a `RETRY_DELAY = 5`s pause.
  - Partially failed batches are retried with only the unresolved rows.
  - Rows that cannot be resolved after all retries are marked `"N/A"`.

#### `build_prompt(jobs: list[dict]) -> str`
- Constructs a structured prompt asking the LLM to extract tech stacks for a batch of jobs.

#### `parse_response(response_text: str, expected_ids: list[str]) -> dict[str, str]`
- Parses the LLM's line-by-line response into a `{source_id: tech_stack}` mapping.

---

### `find_skill_gaps.py`

#### `find_skill_gaps(input_file_path: str, db_url: str, model: str = "llama3.1") -> SkillGapResult`
- Purpose: Identifies which technical skills appear in job listings but not in the candidate's resume.
- Inputs: `input_file_path` — path to the resume `.txt` file; `db_url` — path to the tagged SQLite database; `model` — LLM model name.
- Outputs: `SkillGapResult` Pydantic model with `gaps` (sorted list of missing skills), `tokens_used`, and `time_ms`.

#### `SkillGapResult` (Pydantic BaseModel)
```python
class SkillGapResult(BaseModel):
    gaps: List[str]         # Sorted lowercase list of missing skills
    tokens_used: int        # Total LLM tokens consumed
    time_ms: float          # Wall-clock time in milliseconds
```

#### `extract_resume_skills(resume_text, model) -> tuple[list[str], int]`
- Use LLM to extract a flat list of technical skills from the resume text.

#### `deterministic_filter(resume_skills, job_skills) -> list[str]`
- Normalizes both skill lists and returns job skills whose normalized form is absent from the resume.

#### `normalize(skill: str) -> str`
- Lowercases, strips whitespace, and removes all characters except `a-z`, `0-9`, `.`, `/`, `+`. Preserves skills like `c/c++`, `asp.net`, `node.js`.

#### `is_vague_term(skill: str) -> bool`
- Heuristic filter that removes process-oriented or non-tool terms (e.g., `testing`, `deployment`, `ci/cd`) from the gap list.

---

## Data / Assumptions

### Database Schema

Database (from resources.zip):

```sql
CREATE TABLE jobs (
    source_id   TEXT PRIMARY KEY,
    job_title   TEXT,
    company     TEXT,
    description TEXT,
    tech_stack  TEXT  -- NULL or empty for untagged rows
);
```

### Input Files

- `resume.txt`: Plain text extracted from a resume.

### Assumptions

- Job descriptions are truncated to 1000 characters per job in the tagging prompt to manage token usage.
- Certifications and soft skills are intentionally excluded from skill gap analysis.
- A skill present in the resume in any casing or formatting variant is considered a match (via normalization).
- Skills marked `"N/A"` in the database are treated as untagged and excluded from gap analysis.
- The determinism guarantee applies only to the gap comparison step.


### Data Flow

```
jobs_d1.db (raw)
    └─► tag_data.py ──[LLM batch tagging]──► jobs_d1.db (tech_stack populated)
              │                                   
              ┤────────  resume.txt
              │
find_skill_gaps.py 
             │
              ├─ LLM: extract resume skills
                ├─ DB: fetch all job tech stacks
                  ├─ deterministic_filter()
                    └─► output
```

---

## Testing

### Manual Testing

Both scripts were tested using `jobs_d1.db` and `resume.txt`:

```bash
uv run tag_data.py
uv run find_skill_gaps.py
```

### Correctness Checks

| Scenario | Expected Behaviour 
|---|---|
| All rows already tagged | Prints "No data to tag", exits cleanly |
| LLM returns malformed response | Retries up to 3 times, marks as `N/A` |
| Empty resume file | Returns `SkillGapResult(gaps=[])` without crash |
| DB not found | Catches exception, prints error, returns safely |
| Skill with `/` or `+` in name (e.g. `c/c++`) | Preserved through normalize(), not split |
| Same skill in different casing (e.g. `Python` vs `python`) | Treated as match via lowercasing |

### Determinism Verification

The gap detection is deterministic by design: the LLM is used only to extract resume skills (run once per invocation). All subsequent matching is done via `deterministic_filter()`, a pure string function. Running `find_skill_gaps.py` multiple times on the same inputs produces identical `gaps` output.

---

## Limitations

- **LLM accuracy**: Tech stack extraction quality depends on model capability.
- **Description truncation**: Job descriptions are capped at 1000 characters to reduce token usage.
- **Vague term filtering is heuristic**: The `is_vague_term()` function is harcoded.

---

## Architecture Reflection

### Design Choices

The project is split into three distinct layers: 
- model input (`prompt_model.py`)
- data transformation (`tag_data.py`)
- analysis (`find_skill_gaps.py`). 

Batch processing in `tag_data.py` is main point to the design.
For skill gap detection, the key design decision was to isolate LLM usage to the resume extraction step only, then perform all matching deterministically.

### Trade-offs
- Speed vs. reliability: While adding retry delays increases overall runtime, this was a conscious decision to prioritise data integrity over throughput.
- Accuracy vs. determinism: A fully LLM-driven approach to gap detection would handle semantic equivalence better, for example, recognising sklearn and scikit-learn as the same library. However, non-deterministic outputs make it difficult to validate or reason about results consistently, so a rule-based matching step was used instead to guarantee reproducibility, even at the cost of some precision.


### Improvements
- Synonym normalisation: Maintain a canonical skills dictionary (e.g., `sklearn → scikit-learn`) to eliminate duplicate gap entries caused by naming inconsistencies across job postings.
- Structured output / JSON mode: Use Gemini's native JSON output mode or tool-use to enforce structured responses.
- Hardcoding: Currently the deterministic of the outputs are hardcoded and rule-based.
