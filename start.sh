#!/bin/bash
set -e

# Start the FastAPI backend in the background on port 8000
cd /app/backend
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Give the backend a moment to boot before the frontend tries to hit /health
sleep 3

# Start the Streamlit frontend in the foreground on HF Spaces' required port 7860
cd /app/frontend
streamlit run app.py \
    --server.port=7860 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false