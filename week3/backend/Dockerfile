FROM python:3.14.5-bookworm
 
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
 
WORKDIR /app
 
COPY pyproject.toml .python-version ./
 
RUN uv sync --no-dev
 
COPY src/ src/
 
ENTRYPOINT ["uv", "run", "uvicorn"]
CMD ["--app-dir", "src", "--host", "0.0.0.0", "--port", "8001", "app:app"]
