import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="src/templates")


MODEL = os.getenv("MODEL")
DB_PATH = os.getenv("DB_PATH")
BACKEND_URL = os.getenv("BACKEND_URL")
OLLAMA_URL = os.getenv("OLLAMA_URL")

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request, "chat_page.html", {"backend_url": BACKEND_URL}
    )