#!/usr/bin/env python3
"""
Minimal test server to verify FastAPI setup works
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, '.')

# Set environment variables
os.environ['SECRET_KEY'] = 'test-secret-key-123'
os.environ['DB_CONNECTION_STRING'] = 'sqlite:///test.db'

from fastapi import FastAPI
import uvicorn

# Create a simple FastAPI app
app = FastAPI(title="ForestFinal Test Server", version="1.0")

@app.get("/")
async def root():
    return {"message": "🎉 ForestFinal Test Server is running!", "status": "success"}

@app.get("/health")
async def health():
    return {"status": "healthy", "app": "ForestFinal"}

if __name__ == "__main__":
    print("🚀 Starting ForestFinal Test Server...")
    print("✅ Server will be available at: http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info") 