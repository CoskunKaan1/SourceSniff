"""
Search & Indexing API Routes
==============================
SourceSniff backend'inin 3 temel endpoint'ini icerir:

- ``POST /api/scan``   — Klasor tarama ve indeksleme (arka plan)
- ``GET  /api/search``  — Kelime arama
- ``GET  /api/status``  — Indeksleme durumu sorgulama
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from backend.models.schemas import (
    ScanRequest,
    ScanResponse,
    SearchPosting,
    SearchResponse,
    StatusResponse,
)
from core.indexer import (
    InvertedIndex,
    build_and_save,
    load_index,
)

router = APIRouter(prefix="/api", tags=["search"])

# ────────────────────────────────────────────────────────────────────
# Modul duzeyinde paylasilan durum (thread-safe)
# ────────────────────────────────────────────────────────────────────
_state_lock = threading.Lock()
_indexing_state = {
    "is_indexing": False,
    "indexed_path": None,
    "total_words": 0,
    "message": "Henuz indeksleme yapilmadi.",
}

# Proje kokundeki data/index.json
# __file__ = backend/routes/search.py  →  .parent = routes  →  .parent = backend  →  .parent = proje koku
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_INDEX_PATH = _PROJECT_ROOT / "data" / "index.json"


# ────────────────────────────────────────────────────────────────────
# Yardimci: indeksi yukle (cached, thread-safe)
# ────────────────────────────────────────────────────────────────────
_index_cache: InvertedIndex = {}
_index_cache_mtime: float = 0.0
_cache_lock = threading.Lock()


def _get_index() -> InvertedIndex:
    """``data/index.json`` dosyasini yukler.  Dosya degismediyse
    bellekteki onbellek dondurulur (disk I/O'dan kacinilir).
    """
    global _index_cache, _index_cache_mtime

    if not _INDEX_PATH.exists():
        return {}

    current_mtime = _INDEX_PATH.stat().st_mtime

    with _cache_lock:
        if current_mtime != _index_cache_mtime:
            with _INDEX_PATH.open("r", encoding="utf-8") as fh:
                _index_cache = json.load(fh)
            _index_cache_mtime = current_mtime

    return _index_cache


# ────────────────────────────────────────────────────────────────────
# Arka plan indeksleme gorevi
# ────────────────────────────────────────────────────────────────────
def _run_indexing(scan_path: str) -> None:
    """BackgroundTasks tarafindan cagrilir.  Tam tarama + indeksleme
    pipeline'ini calistirir ve durum bilgisini gunceller."""
    global _indexing_state

    with _state_lock:
        _indexing_state["is_indexing"] = True
        _indexing_state["indexed_path"] = scan_path
        _indexing_state["message"] = "Indeksleme devam ediyor..."

    try:
        t0 = time.perf_counter()
        index = build_and_save(scan_path, str(_INDEX_PATH))
        elapsed = time.perf_counter() - t0

        with _state_lock:
            _indexing_state["is_indexing"] = False
            _indexing_state["total_words"] = len(index)
            _indexing_state["message"] = (
                f"Tamamlandi: {len(index)} kelime indekslendi ({elapsed:.2f}s)"
            )

        # Onbellegi guncelle
        with _cache_lock:
            global _index_cache, _index_cache_mtime
            _index_cache = index
            _index_cache_mtime = _INDEX_PATH.stat().st_mtime

    except Exception as exc:
        with _state_lock:
            _indexing_state["is_indexing"] = False
            _indexing_state["message"] = f"Hata: {exc}"


# ────────────────────────────────────────────────────────────────────
# POST /api/scan
# ────────────────────────────────────────────────────────────────────
@router.post("/scan", response_model=ScanResponse)
async def scan_directory(request: ScanRequest, bg: BackgroundTasks):
    """Belirtilen klasor yolunu tarayip indekslemeyi **arka planda**
    baslatir.

    Islem uzun surebilecegi icin FastAPI ``BackgroundTasks`` kullanilir;
    yanit hemen doner, indeksleme arka planda devam eder.
    ``GET /api/status`` ile durum sorgulanabilir.
    """
    # ── Validasyon ────────────────────────────────────────────────
    target = Path(request.path).resolve()

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Dizin bulunamadi: {target}")

    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Gecerli bir dizin degil: {target}")

    # Zaten indeksleme yapiliyorsa reddet
    with _state_lock:
        if _indexing_state["is_indexing"]:
            raise HTTPException(
                status_code=409,
                detail="Bir indeksleme islemi zaten devam ediyor. "
                       "Bitmesini bekleyin veya GET /api/status ile kontrol edin.",
            )

    # ── Arka plan gorevini baslat ─────────────────────────────────
    bg.add_task(_run_indexing, str(target))

    return ScanResponse(
        success=True,
        message=f"Indeksleme arka planda baslatildi: {target}",
    )


# ────────────────────────────────────────────────────────────────────
# GET /api/search?q=...
# ────────────────────────────────────────────────────────────────────
@router.get("/search", response_model=SearchResponse)
async def search_index(
    q: str = Query(
        ...,
        min_length=1,
        description="Aranacak kelime",
        examples=["import"],
    ),
):
    """``data/index.json`` icerisinde kelime arar.

    Eslesen dosya yollarini, satir numaralarini ve kod onizlemelerini
    JSON olarak dondurur.  Arama buyuk/kucuk harf duyarsizdir.
    """
    index = _get_index()

    if not index:
        raise HTTPException(
            status_code=404,
            detail="Indeks dosyasi bulunamadi. Once POST /api/scan ile indeksleme yapin.",
        )

    # Case-insensitive arama
    query = q.strip().lower()

    postings: List[SearchPosting] = []

    if query in index:
        for entry in index[query]:
            postings.append(
                SearchPosting(
                    path=entry["path"],
                    lines=entry["lines"],
                    preview=entry["preview"],
                )
            )

    total_occurrences = sum(len(p.lines) for p in postings)

    return SearchResponse(
        query=query,
        total_files=len(postings),
        total_occurrences=total_occurrences,
        results=postings,
    )


# ────────────────────────────────────────────────────────────────────
# GET /api/status
# ────────────────────────────────────────────────────────────────────
@router.get("/status", response_model=StatusResponse)
async def indexing_status():
    """Indeksleme isleminin devam edip etmedigini dondurur.

    Returns
    -------
    StatusResponse
        ``is_indexing``: ``True`` ise indeksleme devam ediyor.
    """
    with _state_lock:
        return StatusResponse(**_indexing_state)
