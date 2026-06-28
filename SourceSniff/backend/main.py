"""
SourceSniff — FastAPI Application Entry Point
================================================
Yerel kod arama motoru backend sunucusu.

Endpointler
-----------
- ``POST /api/scan``    — Dizin tarama & indeksleme (BackgroundTasks)
- ``GET  /api/search``  — Inverted index uzerinde kelime arama
- ``GET  /api/status``  — Indeksleme durum sorgulama
- ``GET  /api/health``  — Saglik kontrolu

Calistirma
----------
::

    uvicorn backend.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.routes.search import router as search_router

# ────────────────────────────────────────────────────────────────────
# Uygulama olusturma
# ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SourceSniff",
    description="Yerel Kod Arama Motoru — Projelerinizdeki kaynak kodlari "
                "hizlica arayin ve bulun.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ────────────────────────────────────────────────────────────────────
# CORS — Frontend'den istek atilabilecek sekilde yapilandirildi
# ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ────────────────────────────────────────────────────────────────────
# Router kaydi
# ────────────────────────────────────────────────────────────────────
app.include_router(search_router)


# ────────────────────────────────────────────────────────────────────
# Saglik kontrolu
# ────────────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["system"])
async def health_check():
    """Sunucunun ayakta olup olmadigini kontrol eder."""
    return {"status": "ok", "project": "SourceSniff", "version": "0.1.0"}


# ────────────────────────────────────────────────────────────────────
# Frontend statik dosya servisi
# ────────────────────────────────────────────────────────────────────
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/", tags=["frontend"])
async def serve_frontend():
    """Ana sayfayi (frontend/index.html) sunar."""
    index_file = _FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Frontend henuz yapilandirilmadi."}


# CSS, JS ve diger statik dosyalar
app.mount("/css", StaticFiles(directory=str(_FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(_FRONTEND_DIR / "js")), name="js")
