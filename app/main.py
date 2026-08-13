#!/usr/bin/env python3
"""
app/main.py
-----------
FastAPI application entrypoint for Multilingual PDF Triage and Text Extractor.
Configures CORS middleware, registers MVC controllers, and mounts static view assets.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.controllers.extract_controller import router as extract_router
from app.controllers.view_controller import router as view_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-ready PDF copyability analyzer and multi-format text extractor.",
    version=settings.VERSION
)

# Security Fix S-01: Restricted CORS Policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include Controller Routers
app.include_router(extract_router)
app.include_router(view_router)

# Serve static frontend assets (Views)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
