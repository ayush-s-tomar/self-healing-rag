FROM python:3.11-slim

WORKDIR /app

# System deps needed by chromadb / sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# --- Backend deps ---
COPY backend/requirements.txt ./backend-requirements.txt
RUN pip install --no-cache-dir -r backend-requirements.txt

# --- Frontend deps ---
COPY frontend/requirements.txt ./frontend-requirements.txt
RUN pip install --no-cache-dir -r frontend-requirements.txt

# --- Copy app code ---
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY start.sh ./start.sh
RUN chmod +x start.sh

# HF Spaces expects the app on port 7860
EXPOSE 7860

ENV BACKEND_URL=http://localhost:8000

CMD ["./start.sh"]