import os
from pathlib import Path

# Load .env from api/ root before anything else
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import health, auth, orchards, supply, lots, farmers
from app.seed import seed_database, engine
from sqlmodel import Session, select
from app.models import Farmer

app = FastAPI(
    title="AvoPulse API",
    description="Digital Verification and Aggregation Hub for Kisii Avocado Value Chain",
    version="1.0.0"
)

# CORS configuration for Next.js web application and phone testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static media files mount
MEDIA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "media")
os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(os.path.join(MEDIA_DIR, "uploads"), exist_ok=True)
os.makedirs(os.path.join(MEDIA_DIR, "samples"), exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# Include Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(orchards.router)
app.include_router(supply.router)
app.include_router(lots.router)
app.include_router(farmers.router)

@app.on_event("startup")
def on_startup():
    """Ensure database is seeded on startup if empty."""
    try:
        with Session(engine) as session:
            first_farmer = session.exec(select(Farmer)).first()
            if not first_farmer:
                seed_database()
    except Exception as e:
        seed_database()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

