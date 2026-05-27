import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="src/templates")

def read_secret(name, default=None):
    try:
        with open(f"/run/secrets/{name}") as f:
            return f.read().strip()
    except FileNotFoundError:
        return os.getenv(name.upper(), default)

MODEL = read_secret("model", "llama3.1")
DB_PATH = read_secret("db_path", "/data/jobs.db")
BACKEND_URL = read_secret("BACKEND_URL", "http://localhost:8001")
OLLAMA_URL = read_secret("ollama_url", "http://host.docker.internal:11434/api/generate")

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request, "chat_page.html", {"backend_url": BACKEND_URL}
    )