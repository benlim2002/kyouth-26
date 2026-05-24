import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="src/templates")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request, "chat_page.html", {"backend_url": BACKEND_URL}
    )