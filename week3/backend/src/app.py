import os
import sqlite3
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from week2.prompt_model import prompt_model
from week2.find_skill_gaps import find_skill_gaps, MODEL, DB_PATH
import tempfile, os

load_dotenv("../.env")


app = FastAPI()

class ResumeRequest(BaseModel):
    pdf_text: str

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


MODEL = os.getenv("MODEL")
DB_PATH = os.getenv("DB_PATH")
OLLAMA_URL = os.getenv("OLLAMA_URL")

class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None
    pdf_text: str | None = None

@app.post("/chat")
async def chat(req: ChatRequest):
    history = req.history or []
    
    # build messages array with history
    messages = []
    for turn in history[:-1]:  # exclude last since we add it fresh
        messages.append({"role": turn["role"], "content": turn["content"]})
    
    # add current message
    messages.append({"role": "user", "content": req.message})
    
    # flatten to single prompt for ollama
    prompt = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages
    ) + "\nAssistant:"
    
    response, tokens = prompt_model(MODEL, prompt)
    return {"response": response, "tokens_used": tokens}


@app.get("/jobs")
async def get_jobs():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM jobs")
        jobs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jobs
    except Exception as e:
        return {"error": str(e)}
    

@app.post("/resume")
async def resume(req: ResumeRequest):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(req.pdf_text)
        tmp_path = f.name
    try:
        result = find_skill_gaps(tmp_path, DB_PATH, MODEL)
        
        # also summarize the resume via LLM
        summary_prompt = (
            "You are a helpful career assistant. "
            "Summarize the following resume clearly and concisely. "
            "Include: name, current role, years of experience, key skills, and notable achievements.\n\n"
            f"RESUME:\n{req.pdf_text}"
        )
        summary, _ = prompt_model(MODEL, summary_prompt)
        
        return {
            "gaps": result.gaps,
            "tokens_used": result.tokens_used,
            "summary": summary
        }
    finally:
        os.unlink(tmp_path)