import os
import sqlite3
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from week2.prompt_model import prompt_model

load_dotenv("../.env")


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL = os.getenv("MODEL", "gemini-2.5-flash")
DB_PATH = os.getenv("DB_PATH", "C:\\Users\\benlc\\Desktop\\K-Youth\\kyouth-26\\week1\\data\\3_gold\\jobs.db")
print(f"DB_PATH: {DB_PATH}")

class ChatRequest(BaseModel):
    message: str
    pdf_text: str | None = None


@app.post("/chat")
async def chat(req: ChatRequest):
    prompt = req.message
    if req.pdf_text:
        prompt = f"The user has uploaded a resume/document:\n\n{req.pdf_text}\n\nUser message: {req.message}"

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