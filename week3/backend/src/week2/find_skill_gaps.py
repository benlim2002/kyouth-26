import os
import sqlite3
import sys
import re
import time
from typing import List
from pydantic import BaseModel
from dotenv import load_dotenv
from week2.prompt_model import prompt_model 

load_dotenv()

BATCH_SIZE = 10
RETRY_LIMIT = 3
RETRY_DELAY = 5


MODEL = os.getenv("MODEL")
DB_PATH = os.getenv("DB_PATH")


SKILL_ALIASES = {
    "restful api": "rest api",
    "restful apis": "rest api",
    "rest api development": "rest api",
    "restful api design": "rest api",
    "javascript/typescript": "typescript",
    "javascriptypescript": "typescript",
    "pyspark/sparksql": "pyspark",
    "ci/cd pipeline": "ci/cd",
    "ci/cd pipelines": "ci/cd",
    "large language models": "llm",
    "enterprise large language models": "llm",
    "llms": "llm",
    "react (v18+)": "react",
    "reactjs": "react",
    "spring framework/spring boot": "spring boot",
    "spring framework": "spring boot",
    "linux (rhel / centos / ubuntu)": "linux",
    "nosql databases": "nosql",
    "relational databases": "rdbms",
    "retrieval-augmented generation (rag)": "rag",
    "rag systems": "rag",
    "generative ai": "gen ai",
    "node.js": "nodejs",
}

VAGUE_TERMS = {
    "testing", "deployment", "design", "development", "management",
    "optimization", "monitoring", "implementation", "integration",
    "query", "report", "operational", "automation", "scripting",
    "programming", "analytics", "diagnostics", "generalization",
    "robustness", "predictive", "fetch", "crud", "pipelines",
    "security", "maintenance", "leadership", "communication",
    "collaboration", "apis", "http", "unix", "windows", "bios",
    "bmc", "tls", "json", "html", "css", "api", "web development",
    "databases", "back-end web development", "front-end development",
    "full stack", "full stack development", "full-stack development",
    "agile", "agile methodology", "devops", "ci/cd", "ci/cd pipeline",
    "ci/cd pipelines", "cicd", "test driven development", "domain driven design",
    "object oriented principle", "peer review", "code review",
    "ai", "ai strategy", "ai tools", "ai services", "ai research",
    "ai model development", "ai-driven automation",
    "intelligent automation", "autonomous factory operations",
    "agentic orchestration", "content generation", "model accuracy",
    "model deployment", "attention mechanism", "mixed-precision training",
    "model parallelism", "generalization", "robustness",
    "data pipelines", "data transformation", "data lake solution",
    "data virtualization", "data warehouse", "data architecture",
    "data engineering", "data flows", "data insights", "data models",
    "system architecture", "cloud platforms", "cloud services",
    "automation scripts", "async processes", "log analysis",
    "big data analytics", "structured datasets",
    "integration testing", "unit testing",
    "network os validation", "open networking platforms",
    "digital transformation", "erp systems", "control systems",
    "defect detection", "robotics software", "autonomous ai agents",
    "bearer token", "token-based authentication", "http api",
    "http protocols", "jwt authentication", "oauth",
    "containerization", "web automation", "automation platforms",
}

class SkillGapResult(BaseModel):
    gaps: List[str]
    tokens_used: int = 0  # Added for bonus
    time_ms: float = 0.0  # Added for bonus


def read_resume(input_file_path: str) -> str:
    try:
        with open(input_file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"[Error] Failed to read resume: {e}")
        return ""


def fetch_tech_stacks(db_url: str) -> list[str]:
    try:
        with sqlite3.connect(db_url) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT tech_stack FROM jobs WHERE tech_stack IS NOT NULL AND tech_stack != '' AND tech_stack != 'N/A'"
            )
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"[DB Error] Failed to fetch tech stacks: {e}")
        return []


def extract_all_skills(tech_stacks: list[str]) -> list[str]:
    seen = set()
    skills = []
    for stack in tech_stacks:
        for skill in stack.split(","):
            normalized = skill.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                skills.append(normalized)
    return sorted(skills)


def extract_resume_skills(resume_text: str, model: str) -> tuple[list[str], int]:
    prompt = (
        "You are a technical recruiter assistant. "
        "Extract all technical skills, tools, frameworks, and programming languages from the resume below. "
        "Return ONLY a comma-separated list of skills in lowercase. No explanations, no categories, no bullet points.\n"
        "Ignore certifications, soft skills, and non-technical skills like leadership or management.\n"
        "Keep exact formatting for skills with special characters (e.g., 'c/c++', 'asp.net', 'node.js').\n\n"
        f"RESUME:\n{resume_text}\n\n"
        "Respond ONLY in this format:\n"
        "SKILLS: <comma separated skills>"
    )
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            response_text, tokens = prompt_model(model, prompt)
            if response_text.startswith("["):
                raise RuntimeError(response_text)
            match = re.search(r"SKILLS:\s*(.+)", response_text, re.IGNORECASE)
            if not match:
                raise ValueError("Could not parse SKILLS from response")
            skills = [s.strip().lower() for s in match.group(1).split(",") if s.strip()]
            if skills:
                return skills, tokens
        except Exception as e:
            print(f"[Resume Extraction] Attempt {attempt} failed: {e}")
            if attempt < RETRY_LIMIT:
                time.sleep(RETRY_DELAY)
    return [], 0


def normalize(skill: str) -> str:
    skill = skill.lower().strip()
    skill = SKILL_ALIASES.get(skill, skill)  # alias FIRST
    skill = re.sub(r'[^a-z0-9./+#]', ' ', skill).strip()
    skill = re.sub(r'\s+', ' ', skill)
    return skill


def build_gap_prompt(resume_skills: list[str], job_skills_batch: list[str]) -> str:
    return (
        "You are a technical recruiter assistant. "
        "Given a list of skills from a candidate's resume and a list of skills required by jobs, "
        "identify which job skills are NOT present in the resume. "
        "Only flag concrete technical skills, tools, frameworks, programming languages, or platforms. "
        "Exclude job responsibilities, soft skills, certifications, and vague terms like 'design', 'deployment', 'security', 'testing', 'maintenance'.\n"
        "Keep exact formatting for skills with special characters (e.g., 'c/c++', 'asp.net').\n\n"
        f"RESUME SKILLS: {', '.join(resume_skills)}\n\n"
        f"JOB SKILLS: {', '.join(job_skills_batch)}\n\n"
        "Respond ONLY in this format:\n"
        "GAPS: <comma separated missing skills, or NONE if no gaps>"
    )


def parse_gap_response(response_text: str) -> list[str]:
    match = re.search(r"GAPS:\s*(.+)", response_text, re.IGNORECASE)
    if not match:
        return []
    raw = match.group(1).strip()
    if raw.upper() == "NONE":
        return []
    return [s.strip().lower() for s in raw.split(",") if s.strip()]


def deterministic_filter(resume_skills: list[str], job_skills: list[str]) -> list[str]:
    resume_normalized = {normalize(s) for s in resume_skills}
    seen = set()
    gaps = []
    for skill in job_skills:
        norm = normalize(skill)
        if norm not in resume_normalized and norm not in seen:
            seen.add(norm)
            gaps.append(skill.lower())
    return gaps

def is_vague_term(skill: str) -> bool:
    skill_lower = skill.lower().strip()
    if skill_lower in VAGUE_TERMS:
        return True
    if len(skill_lower) <= 2:
        return True
    generic_suffixes = [
        'methodologies', 'strategies', 'patterns', 'practices',
        'principles', 'concepts', 'workflows', 'capabilities',
        'requirements', 'professionals', 'teams', 'implied',
    ]
    if any(suffix in skill_lower for suffix in generic_suffixes):
        return True
    return False


def find_skill_gaps(
    input_file_path: str,
    db_url: str,
    model: str = "llama3.1"
) -> SkillGapResult:

    start_time = time.time()
    total_tokens = 0

    resume_text = read_resume(input_file_path)
    if not resume_text:
        return SkillGapResult(gaps=[], tokens_used=0, time_ms=0.0)

    resume_skills, tokens = extract_resume_skills(resume_text, model)
    total_tokens += tokens
    if not resume_skills:
        print("[Warning] Could not extract skills from resume.")
        return SkillGapResult(gaps=[], tokens_used=total_tokens, time_ms=(time.time() - start_time) * 1000)

    tech_stacks = fetch_tech_stacks(db_url)
    if not tech_stacks:
        print("[Warning] No tech stacks found in database.")
        return SkillGapResult(gaps=[], tokens_used=total_tokens, time_ms=(time.time() - start_time) * 1000)

    # get all unique job skills
    all_job_skills = extract_all_skills(tech_stacks)
    
    # deterministic filtering
    candidate_gaps = deterministic_filter(resume_skills, all_job_skills)
    
    # filter out vague terms using heuristic rules (100% deterministic)
    confirmed_gaps = [g for g in candidate_gaps if not is_vague_term(g)]

    elapsed = (time.time() - start_time) * 1000
    result = SkillGapResult(
        gaps=sorted(confirmed_gaps),
        tokens_used=total_tokens,
        time_ms=elapsed
    )
    print(f"\n{result}")
    return result


if __name__ == "__main__":
    resume_path = sys.argv[1] if len(sys.argv) > 1 else "data/resume.txt"
    db_path = sys.argv[2] if len(sys.argv) > 2 else DB_PATH

    print(f"Using model: {MODEL}\n")
    result = find_skill_gaps(resume_path, db_path, MODEL)