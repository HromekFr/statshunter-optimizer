#!/usr/bin/env python3
"""
Startup script for Statshunters Route Optimizer
"""
import os
import sys

def main():
    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    os.chdir(backend_dir)
    
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_file):
        print("⚠️  WARNING: .env file not found!")
        print("Please copy .env.example to .env and add your API keys:")
        print("1. Statshunters share link")
        print("2. OpenRouteService API key")
        print()
    
    # Run the server
    print("🚴 Starting Statshunters Route Optimizer...")
    print("Server will be available at: http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    print()
    
    # Import and run
    sys.path.insert(0, '.')
    from main import app
    import uvicorn
    
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    main()