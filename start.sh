#!/bin/bash
if [ "$INIT_DB" = "true" ]; then
    echo "Running database initialization..."
    # Give postgres a few seconds to start accepting connections
    sleep 5 
    python3 dataset/generate.py
    python3 dataset/load.py
fi
echo "Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
