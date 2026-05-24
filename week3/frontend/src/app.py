from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory="src/templates")


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "chat_page.html")