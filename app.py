"""
Code Rex Assessment Application
This is the main entry point for the FastAPI application.
Author: Wahid Sadique Koly
"""

from modules.config import app

# Import route modules to register routes with the app
from modules import main, admin

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
