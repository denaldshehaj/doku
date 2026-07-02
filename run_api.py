"""Start the DOKU API + frontend server (local-only).

    .venv\\Scripts\\python run_api.py

Binds strictly to 127.0.0.1: nothing is ever exposed to the network.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, workers=1)
