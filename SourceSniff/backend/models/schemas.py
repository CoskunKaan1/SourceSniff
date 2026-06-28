"""
Pydantic Schemas — API Request / Response Modelleri
=====================================================
Tum endpoint'lerin giris ve cikis veri yapilari burada tanimlanir.
FastAPI bu semalari otomatik dokumantasyon (Swagger UI) ve
veri dogrulama icin kullanir.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ────────────────────────────────────────────────────────────────────
# POST /api/scan
# ────────────────────────────────────────────────────────────────────
class ScanRequest(BaseModel):
    """Tarama istegi govdesi."""

    path: str = Field(
        ...,
        description="Taranacak kok dizinin mutlak yolu",
        examples=["C:/Projects/my_app"],
    )


class ScanResponse(BaseModel):
    """Tarama istegi yaniti."""

    success: bool
    message: str


# ────────────────────────────────────────────────────────────────────
# GET /api/search?q=...
# ────────────────────────────────────────────────────────────────────
class SearchPosting(BaseModel):
    """Tek bir dosyadaki eslesme bilgisi."""

    path: str = Field(..., description="Dosyanin mutlak yolu")
    lines: List[int] = Field(..., description="Eslesmen satir numaralari")
    preview: str = Field(..., description="Ilk gecis satirinin onizlemesi")


class SearchResponse(BaseModel):
    """Arama yaniti."""

    query: str
    total_files: int = Field(..., description="Eslesen dosya sayisi")
    total_occurrences: int = Field(..., description="Toplam gecis sayisi")
    results: List[SearchPosting]


# ────────────────────────────────────────────────────────────────────
# GET /api/status
# ────────────────────────────────────────────────────────────────────
class StatusResponse(BaseModel):
    """Indeksleme durum yaniti."""

    is_indexing: bool = Field(
        ..., description="Indeksleme islemi devam ediyor mu"
    )
    indexed_path: Optional[str] = Field(
        None, description="Su an indekslenen dizin yolu"
    )
    total_words: int = Field(0, description="Indeksteki benzersiz kelime sayisi")
    message: str = Field("", description="Durum mesaji")
