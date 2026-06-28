"""
Token Parser — SourceSniff Core
=================================
Kaynak kod satırlarını anlamlı kelimelere (token) ayırır.  Regex ile
programlama diline özgü noktalama ve operatör karakterleri temizlenir;
geriye yalnızca aranabilir kelimeler kalır.

Kullanim
--------
>>> from core.parser import tokenize_line
>>> tokenize_line("def hello_world(name: str) -> None:")
['def', 'hello_world', 'name', 'str', 'None']
"""

from __future__ import annotations

import re
from typing import List

# ────────────────────────────────────────────────────────────────────
# Derlenmis regex kaliplari (modul yuklenirken bir kez derlenir)
# ────────────────────────────────────────────────────────────────────

# Temizlenecek karakterler:  { } ( ) [ ] ; , . = + - * / \ : < > ! & | ^ ~ @ # % ? " '
_STRIP_PATTERN: re.Pattern = re.compile(
    r'[{}\(\)\[\];,\.=+\-*/\\:<>!&|^~@#%?\"\']'
)

# Bosluk ve tab ile ayirma
_SPLIT_PATTERN: re.Pattern = re.compile(r"\s+")

# Minimum token uzunlugu — tek karakterli tokenlar genelde anlamli degil
_MIN_TOKEN_LENGTH: int = 2


# ────────────────────────────────────────────────────────────────────
# Ana tokenizer fonksiyonu
# ────────────────────────────────────────────────────────────────────
def tokenize_line(line: str, *, min_length: int = _MIN_TOKEN_LENGTH) -> List[str]:
    """Bir kaynak kod satirini temizleyip anlamli kelimelere ayirir.

    Islem adimlari
    ---------------
    1. Regex ile ``{ } ( ) [ ] ; , . = + - * / \\ : < > ! & | ^ ~ @ # % ? " '``
       karakterleri bosluga donusturulur.
    2. Satir bosluk karakterlerinden bolunur.
    3. ``min_length`` degerinden kisa tokenlar elenir.
    4. Tum tokenlar **kucuk harfe** cevrilerek dondurulur (case-insensitive
       arama icin).

    Parameters
    ----------
    line : str
        Islenecek kaynak kod satiri.
    min_length : int, optional
        Minimum token uzunlugu.  Varsayilan ``2``.

    Returns
    -------
    list[str]
        Temizlenmis ve kucuk harfe cevrilmis token listesi.

    Examples
    --------
    >>> tokenize_line("for i in range(10):")
    ['for', 'in', 'range', '10']

    >>> tokenize_line("self.data[key] = value + 1")
    ['self', 'data', 'key', 'value']

    >>> tokenize_line("import os, sys, json")
    ['import', 'os', 'sys', 'json']
    """
    # 1. Ozel karakterleri bosluga cevir
    cleaned: str = _STRIP_PATTERN.sub(" ", line)

    # 2. Bosluklardan bol
    raw_tokens: List[str] = _SPLIT_PATTERN.split(cleaned.strip())

    # 3-4. Filtrele ve kucuk harfe cevir
    return [
        token.lower()
        for token in raw_tokens
        if len(token) >= min_length
    ]


def tokenize_file(filepath: str, *, min_length: int = _MIN_TOKEN_LENGTH) -> dict:
    """Bir dosyayi satir satir okuyarak her satirdaki tokenlari cikarir.

    Parameters
    ----------
    filepath : str
        Okunacak dosyanin mutlak yolu.
    min_length : int, optional
        Minimum token uzunlugu.

    Returns
    -------
    dict
        ``{satir_numarasi: {"tokens": [...], "preview": "..."}}``
        biciminde sozluk.  ``satir_numarasi`` 1-tabanlidir.

    Examples
    --------
    >>> result = tokenize_file("main.py")
    >>> result[1]
    {'tokens': ['import', 'json'], 'preview': 'import json'}
    """
    result: dict = {}

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            for line_no, raw_line in enumerate(fh, start=1):
                stripped = raw_line.rstrip("\n\r")
                tokens = tokenize_line(stripped, min_length=min_length)

                if tokens:
                    result[line_no] = {
                        "tokens": tokens,
                        "preview": stripped.strip(),
                    }
    except (OSError, IOError):
        # Okunamayan dosyalari sessizce atla
        pass

    return result


# ────────────────────────────────────────────────────────────────────
# Dogrudan calistirma destegi
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Kullanim: python -m core.parser <dosya_yolu>")
        sys.exit(1)

    target = sys.argv[1]
    parsed = tokenize_file(target)

    print(f"\n[*] '{target}' dosyasindan {len(parsed)} satir tokenize edildi:\n")
    for lno, data in list(parsed.items())[:15]:
        print(f"  Satir {lno:>4d}: {data['tokens']}")
    if len(parsed) > 15:
        print(f"  ... ve {len(parsed) - 15} satir daha.")
