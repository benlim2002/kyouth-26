# Week 3 — Resume Helper Chatbot

A full-stack containerized chat application that helps users analyze their resumes using a local LLM (llama3.1 via Ollama), with a job market dashboard powered by a SQLite database from Week 1.

---

## Project Overview

The application consists of two services:

- **Frontend** — FastAPI + Jinja2 serving a Bootstrap chat interface. Users can type messages and upload PDF resumes. Also displays a job market dashboard with charts and filters.
- **Backend** — FastAPI exposing a `POST /chat` endpoint that processes user messages using llama3.1 via Ollama, and a `GET /jobs` endpoint that reads job data from a SQLite database.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Ollama](https://ollama.com/) installed and running locally with `llama3.1` pulled
- (Optional for local dev) [uv](https://github.com/astral-sh/uv)

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone <https://github.com/benlim2002/kyouth-26>
cd week3
```

### 2. Configure secrets


This project uses Docker secrets. Create each secret with:

```bash
echo "http://backend:8001" | docker secret create backend_url -
echo "llama3.1" | docker secret create model -
echo "/data/jobs.db" | docker secret create db_path -
echo "http://host.docker.internal:11434/api/generate" | docker secret create ollama_url -
```

### 3. Start Ollama

Make sure Ollama is running on your machine with llama3.1:

```bash
ollama serve
ollama pull llama3.1
```

---

## Usage

### Run with Docker Compose

```bash
cd week3
```

```bash
docker stack deploy -c docker-compose.yml week3
```



```bash
docker compose build
docker stack deploy -c docker-compose.yml week3
```

- Frontend: [http://localhost:8000](http://localhost:8000)
- Backend: [http://localhost:8001](http://localhost:8001)


### Run locally (without Docker)
*Prefer to not run locally since it will get messy, you need 2 terminals open why have 2 terminals open when u can have one ^-^*

```bash
# Terminal 1 — Backend
cd week3/backend
uv sync
uv run uvicorn --app-dir src --host 0.0.0.0 --port 8001 app:app

# Terminal 2 — Frontend
cd week3/frontend
uv sync
uv run uvicorn --app-dir src --host 0.0.0.0 --port 8000 app:app
```

### Using the app

1. Open [http://localhost:8000](http://localhost:8000)
2. Type a message in the chat input and press **Send** or **Enter**
3. Optionally upload a PDF resume using the 📎 button — the text will be extracted client-side and sent with your message
4. Scroll down to view the **Job Market Dashboard** — filter jobs by category and view tech stack and company charts

---

## API Reference

### `POST /chat`

Sends a user message to the LLM and returns a response.

**Request:**
```json
{
  "message": "What jobs suit my resume?",
  "pdf_text": "Optional extracted text from uploaded PDF..."
}
```

**Response:**
```json
{
  "response": "Based on your resume...",
  "tokens_used": 512
}
```

### `GET /jobs`

Returns all job listings from the SQLite database.

**Response:**
```json
[
  {
    "source_id": "91237386",
    "job_title": "AI & Workflow Automation Associate",
    "company": "Grof Sdn Bhd",
    "description": "...",
    "tech_stack": "Python, AI, automation"
  }
]
```

### Frontend Key Functions

| Function | Description |
|---|---|
| `sendMessage()` | Reads user input, appends to chat, POSTs to `/chat`, renders response |
| `appendMessage(sender, text)` | Creates and appends a chat bubble to the history |
| `loadJobs()` | Fetches job data from `/jobs` and renders charts and job list |
| `renderCharts(jobs)` | Renders pie chart (tech stack) and bar chart (jobs per company) |
| `renderJobList(jobs)` | Renders filtered job listings |

### Service Communication

The frontend and backend share a Docker overlay network (`app-network`). The frontend calls `http://backend:8001` using the service name as hostname — this is resolved by Docker's internal DNS over the shared network.

---

## Data & Assumptions

### Data Flow

```
User types message → JS sends POST /chat → Backend calls Ollama → Response returned → Rendered in chat
User uploads PDF → pdfjs extracts text client-side → Sent as pdf_text in same POST request
Page loads → JS calls GET /jobs → Backend reads jobs.db → Charts and list rendered
```

### Assumptions

- PDF text extraction is done client-side using `pdfjs-dist` — no file is uploaded to the server
- The LLM has no memory between messages — each request is stateless
- `jobs.db` is a SQLite file copied into the backend image at `src/week2/jobs.db`, mounted to `/data/jobs.db`
- Ollama must be running on the host machine — the backend reaches it via `host.docker.internal:11434`
- PDF files should be text-based (not scanned images) for accurate extraction

### Message Format

```json
{ "message": "string", "pdf_text": "string | null" }
```

---

## Testing

### Test the backend manually

```bash
# Test /chat endpoint
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Python?", "pdf_text": null}'

# Test /jobs endpoint
curl http://localhost:8001/jobs
```

### Frontend test cases

| Test | Expected |
|---|---|
| Type a message and press Send | Message appears on right, bot responds on left |
| Press Enter | Same as Send |
| Upload a PDF and send a message | PDF filename shown, text sent with message |
| Backend offline | Error message shown in chat |
| Click filter buttons in dashboard | Job list updates to matching tech stack |

### Docker test

```bash
docker compose up --build
# Visit http://localhost:8000 and verify both chat and dashboard load
```

---

## Limitations

- **No chat history persistence** — refreshing the page clears all messages
- **LLM response quality** — llama3.1 responses may be inconsistent; no prompt engineering applied beyond basic context injection
- **PDF extraction accuracy** — scanned PDFs or image-based PDFs will return empty or garbled text, hence why I added 
```
div.innerHTML = text
  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  .replace(/\n\d+\.\s/g, '<br>• ')
  .replace(/\n/g, '<br>');
```
- **Job dashboard is static** — data comes from a fixed SQLite snapshot, not a live feed
- **Ollama must run on host** — the backend cannot start the Ollama process itself

---

## Architecture Reflection

### Design Choices

The frontend and backend are separated into two independent services. This makes each service independently deployable and testable, the frontend can be swapped out without touching the LLM logic, and the backend can serve multiple frontends. Docker containers enforce this boundary cleanly. Database from week1 was moved into week3/backend/src/week2 due to use of Docker secrets.

FastAPI was chosen for both services for consistency and because it handles async requests well, which matters when waiting on slow LLM responses.

### Trade-offs

Simplicity was prioritized over performance. LLM has no context from previous messages in the same session.

PDF text extraction happens client-side in the browser using `pdfjs-dist`. This avoids storing files on the server but means extraction quality depends on the browser and PDF structure.

### Improvements

Given more time, the following would improve the system significantly:

- **Conversation memory** — pass the full message history to the LLM on each request.
- **Frontend framework** — React or Vue would make the chat state easier to manage.
- **Cloud deployment** — if more time were given, would have definitely attempted bonus 1 on day 4 to deploy this into cloud.
- **Database for chat history** — store conversations in SQLite or Postgres so users can resume sessions.
