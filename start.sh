#!/bin/bash
if [ "$INIT_DB" = "true" ]; then
    echo "Running database initialization..."
    # Give postgres a few seconds to start accepting connections
    sleep 5 
    
    if [ ! -f "dataset/queries.csv" ]; then
        echo "dataset/queries.csv not found! Downloading and generating dataset..."
        python3 dataset/generate.py
    else
        echo "dataset/queries.csv already exists! Skipping download."
    fi
    
    python3 dataset/load.py
fi
echo "Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
