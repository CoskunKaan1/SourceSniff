"""
File Indexer — SourceSniff Core
================================
Iki temel sorumlulugu vardir:

1. **Dizin Tarama** — Kullanicinin belirttigi kok dizinden asagiya dogru
   ozyinelemeli tarama yaparak hedef uzantilara sahip kaynak kod dosyalarinin
   mutlak yollarini dondurur.  ``config.json`` icerisindeki kara liste
   sayesinde gereksiz dizinler budanir.

2. **Inverted Index (Ters Dizin)** — Taranan dosyalari satir satir okuyup
   tokenize eder ve asagidaki yapiyi olusturur::

       {
           "kelime": [
               {
                   "path":    "/mutlak/dosya/yolu.py",
                   "lines":   [5, 12, 38],
                   "preview": "ilk gecis satirinin onizlemesi"
               },
               ...
           ],
           ...
       }

   Olusturulan indeks ``data/index.json`` dosyasina serializasyon ile
   kaydedilir ve geri okunabilir.

Kullanim
--------
>>> from core.indexer import scan_directory, build_inverted_index, save_index
>>> files   = scan_directory(r"C:\\Projects\\my_app")
>>> index   = build_inverted_index(files)
>>> save_index(index, "data/index.json")
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Set

from core.parser import tokenize_file

# ────────────────────────────────────────────────────────────────────
# Sabitler
# ────────────────────────────────────────────────────────────────────
_CONFIG_PATH: Path = Path(__file__).resolve().parent.parent / "config.json"

_TARGET_EXTENSIONS: Set[str] = {".py", ".java", ".cpp", ".js"}


# ────────────────────────────────────────────────────────────────────
# Yardımcı fonksiyonlar
# ────────────────────────────────────────────────────────────────────
def _load_ignore_list(config_path: Path = _CONFIG_PATH) -> List[str]:
    """``config.json`` dosyasından kara listeyi (ignore_list) yükler.

    Parameters
    ----------
    config_path : Path
        Yapılandırma dosyasının yolu.  Varsayılan olarak proje kök
        dizinindeki ``config.json`` kullanılır.

    Returns
    -------
    list[str]
        Göz ardı edilecek dizin / dosya kalıplarının listesi.

    Raises
    ------
    FileNotFoundError
        ``config.json`` bulunamazsa.
    KeyError
        JSON içinde ``ignore_list`` anahtarı yoksa.
    """
    with config_path.open("r", encoding="utf-8") as fh:
        config: dict = json.load(fh)
    return config["ignore_list"]


def _is_ignored(name: str, ignore_patterns: List[str]) -> bool:
    """Bir dosya/dizin adının kara listedeki kalıplardan biriyle eşleşip
    eşleşmediğini kontrol eder.

    Hem sabit isim eşleşmesi (``node_modules``) hem de glob kalıpları
    (``*.egg-info``) desteklenir.

    Parameters
    ----------
    name : str
        Kontrol edilecek dosya veya dizin adı (sadece basename).
    ignore_patterns : list[str]
        Kara liste kalıpları.

    Returns
    -------
    bool
        Eşleşme varsa ``True``.
    """
    for pattern in ignore_patterns:
        # Glob karakteri içeren kalıplar için fnmatch kullan
        if "*" in pattern or "?" in pattern:
            if fnmatch(name, pattern):
                return True
        else:
            # Sabit isim karşılaştırması (büyük/küçük harf duyarsız)
            if name.lower() == pattern.lower():
                return True
    return False


# ────────────────────────────────────────────────────────────────────
# Ana tarama fonksiyonu
# ────────────────────────────────────────────────────────────────────
def scan_directory(
    root: str | Path,
    *,
    extensions: Set[str] | None = None,
    config_path: Path | None = None,
) -> List[str]:
    """Belirtilen kök dizinden başlayarak özyinelemeli tarama yapar ve
    hedef uzantılara sahip kaynak kod dosyalarının **mutlak yollarını**
    döndürür.

    ``config.json`` içindeki ``ignore_list`` kara listesinde bulunan
    dizinler tarama sırasında budanır (prune); bu sayede ``node_modules``,
    ``.git`` gibi büyük/gereksiz dizinlere hiç girilmez ve performans
    korunur.

    Parameters
    ----------
    root : str | Path
        Taramanın başlayacağı kök dizin yolu.
    extensions : set[str] | None, optional
        Taranacak dosya uzantıları kümesi.  ``None`` verilirse varsayılan
        olarak ``{".py", ".java", ".cpp", ".js"}`` kullanılır.
    config_path : Path | None, optional
        Alternatif bir ``config.json`` yolu.  ``None`` ise proje kökündeki
        dosya kullanılır.

    Returns
    -------
    list[str]
        Bulunan kaynak kod dosyalarının mutlak yollarını içeren liste.

    Raises
    ------
    NotADirectoryError
        ``root`` geçerli bir dizin değilse.

    Examples
    --------
    >>> results = scan_directory(r"C:\\Projects\\my_app")
    >>> print(f"{len(results)} dosya bulundu.")
    42 dosya bulundu.

    >>> results = scan_directory(
    ...     "/home/user/project",
    ...     extensions={".py", ".js"},
    ... )
    """
    # ── Parametreleri hazırla ──────────────────────────────────────
    root_path = Path(root).resolve()

    if not root_path.is_dir():
        raise NotADirectoryError(
            f"Belirtilen yol geçerli bir dizin değil: {root_path}"
        )

    target_ext: Set[str] = extensions if extensions is not None else _TARGET_EXTENSIONS
    ignore_patterns: List[str] = _load_ignore_list(
        config_path if config_path is not None else _CONFIG_PATH
    )

    # ── Özyinelemeli tarama (generator → list) ────────────────────
    return list(_walk(root_path, target_ext, ignore_patterns))


def _walk(
    directory: Path,
    target_ext: Set[str],
    ignore_patterns: List[str],
) -> List[str]:
    """Verilen dizini özyinelemeli olarak tarar.

    * Kara listedeki alt dizinlere **girilmez** (budama / pruning).
    * Yalnızca ``target_ext`` kümesindeki uzantılara sahip dosyalar
      sonuç listesine eklenir.

    Parameters
    ----------
    directory : Path
        Taranacak dizin.
    target_ext : set[str]
        Kabul edilen dosya uzantıları.
    ignore_patterns : list[str]
        Kara liste kalıpları.

    Yields
    ------
    str
        Eşleşen dosyanın mutlak yolu.
    """
    results: List[str] = []

    try:
        entries = sorted(directory.iterdir())
    except PermissionError:
        # Erişim izni olmayan dizinleri sessizce atla
        return results

    for entry in entries:
        # ── Kara liste kontrolü ──────────────────────────────────
        if _is_ignored(entry.name, ignore_patterns):
            continue

        if entry.is_dir():
            # Alt dizine dal (özyineleme)
            results.extend(_walk(entry, target_ext, ignore_patterns))

        elif entry.is_file() and entry.suffix.lower() in target_ext:
            results.append(str(entry))

    return results



# ────────────────────────────────────────────────────────────────────
# Inverted Index (Ters Dizin) Olusturma
# ────────────────────────────────────────────────────────────────────

# Posting yapisi tipi:  {"path": str, "lines": list[int], "preview": str}
Posting = Dict[str, Any]

# Indeks yapisi tipi:   {"kelime": [Posting, ...]}
InvertedIndex = Dict[str, List[Posting]]


def build_inverted_index(file_paths: List[str]) -> InvertedIndex:
    """Dosya yollarindan olusan bir listeyi satir satir okuyarak
    **Inverted Index** (ters dizin) olusturur.

    Her dosya ``core.parser.tokenize_file`` ile tokenize edilir.
    Ayni kelimenin ayni dosyadaki tum gecisleri tek bir ``Posting``
    nesnesinde birlestirilir.

    Cikti Yapisi
    -------------
    ::

        {
            "import": [
                {
                    "path":    "C:/project/main.py",
                    "lines":   [1, 5],
                    "preview": "import json"       # ilk gecis satiri
                },
                ...
            ],
            ...
        }

    Parameters
    ----------
    file_paths : list[str]
        Taranacak dosyalarin mutlak yol listesi
        (``scan_directory`` ciktisi).

    Returns
    -------
    InvertedIndex
        ``{kelime: [Posting, ...]}`` biciminde ters dizin sozlugu.

    Examples
    --------
    >>> files = scan_directory(".")
    >>> index = build_inverted_index(files)
    >>> len(index)             # benzersiz kelime sayisi
    347
    >>> index["import"][0]
    {'path': '...main.py', 'lines': [1, 5], 'preview': 'import json'}
    """
    # Ana indeks:  kelime -> dosya_yolu -> {"lines": [...], "preview": ...}
    # Once ic ice defaultdict ile topla, sonra son formata donustur.
    temp: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(
        lambda: defaultdict(lambda: {"lines": [], "preview": ""})
    )

    total_files = len(file_paths)

    for file_idx, filepath in enumerate(file_paths, start=1):
        # Dosya ilerleme bilgisi (buyuk projelerde faydali)
        if total_files > 50 and file_idx % 100 == 0:
            print(f"  [{file_idx}/{total_files}] indeksleniyor...")

        parsed = tokenize_file(filepath)

        for line_no, data in parsed.items():
            preview: str = data["preview"]
            tokens: List[str] = data["tokens"]

            for token in tokens:
                entry = temp[token][filepath]

                # Satir numarasini ekle (tekrar kontrolu)
                if not entry["lines"] or entry["lines"][-1] != line_no:
                    entry["lines"].append(line_no)

                # Onizleme — yalnizca ilk gecis satirini sakla
                if not entry["preview"]:
                    entry["preview"] = (
                        preview[:120] + "..." if len(preview) > 120 else preview
                    )

    # ── Son formata donustur ──────────────────────────────────────
    index: InvertedIndex = {}
    for word, file_map in temp.items():
        postings: List[Posting] = [
            {
                "path": path,
                "lines": info["lines"],
                "preview": info["preview"],
            }
            for path, info in file_map.items()
        ]
        index[word] = postings

    return index


# ────────────────────────────────────────────────────────────────────
# Incremental (Artimsal) Indeks Guncelleme
# ────────────────────────────────────────────────────────────────────
def remove_file_from_index(index: InvertedIndex, filepath: str) -> int:
    """Belirtilen dosyaya ait tum posting'leri indeksten cikarir.

    Bir dosya silindiginde veya guncellenmeden once eski kayitlarin
    temizlenmesi icin kullanilir.  Bos kalan kelime girislerini de
    sozlukten siler.

    Parameters
    ----------
    index : InvertedIndex
        Mevcut ters dizin (yerinde degistirilir / mutate).
    filepath : str
        Cikarilacak dosyanin mutlak yolu.

    Returns
    -------
    int
        Cikarilan posting sayisi (kac kelimeden kaldirildi).
    """
    normalized = str(Path(filepath).resolve())
    removed_count = 0
    empty_keys: List[str] = []

    for word, postings in index.items():
        original_len = len(postings)
        index[word] = [p for p in postings if p["path"] != normalized]

        if len(index[word]) < original_len:
            removed_count += 1

        if not index[word]:
            empty_keys.append(word)

    # Bos kalan kelimeleri temizle
    for key in empty_keys:
        del index[key]

    return removed_count


def add_file_to_index(index: InvertedIndex, filepath: str) -> int:
    """Tek bir dosyayi tokenize edip mevcut indekse ekler.

    Dosya satir satir okunur, tokenize edilir ve her token icin
    uygun posting olusturularak indekse eklenir.

    Parameters
    ----------
    index : InvertedIndex
        Mevcut ters dizin (yerinde degistirilir / mutate).
    filepath : str
        Eklenecek dosyanin mutlak yolu.

    Returns
    -------
    int
        Eklenen benzersiz kelime sayisi (bu dosyadan).
    """
    normalized = str(Path(filepath).resolve())
    parsed = tokenize_file(normalized)

    if not parsed:
        return 0

    # Gecici olarak dosya bazinda token → {lines, preview} topla
    file_tokens: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"lines": [], "preview": ""}
    )

    for line_no, data in parsed.items():
        preview: str = data["preview"]
        for token in data["tokens"]:
            entry = file_tokens[token]
            if not entry["lines"] or entry["lines"][-1] != line_no:
                entry["lines"].append(line_no)
            if not entry["preview"]:
                entry["preview"] = (
                    preview[:120] + "..." if len(preview) > 120 else preview
                )

    # Ana indekse ekle
    added = 0
    for word, info in file_tokens.items():
        posting: Posting = {
            "path": normalized,
            "lines": info["lines"],
            "preview": info["preview"],
        }
        if word not in index:
            index[word] = []
            added += 1
        index[word].append(posting)

    return added


def update_file_in_index(index: InvertedIndex, filepath: str) -> None:
    """Tek bir dosyanin indeks kaydini gunceller (sil + yeniden ekle).

    Tum projeyi bastan taramak yerine yalnizca degisen dosyanin
    eski kayitlari cikarilir ve yeni icerigi tekrar parse edilip
    indekse eklenir.  Watcher tarafindan kullanilir.

    Parameters
    ----------
    index : InvertedIndex
        Mevcut ters dizin (yerinde degistirilir / mutate).
    filepath : str
        Guncellenecek dosyanin mutlak yolu.
    """
    remove_file_from_index(index, filepath)
    add_file_to_index(index, filepath)


# ────────────────────────────────────────────────────────────────────
# Serializasyon / Deserializasyon
# ────────────────────────────────────────────────────────────────────
def save_index(index: InvertedIndex, output_path: str | Path = "data/index.json") -> Path:
    """Olusturulan inverted index'i JSON dosyasina kaydeder.

    Ust dizinler otomatik olusturulur.  Dosya UTF-8 kodlamasi ile
    yazilir ve Turkce / Unicode karakterler korunur.

    Parameters
    ----------
    index : InvertedIndex
        ``build_inverted_index`` ciktisi.
    output_path : str | Path, optional
        Hedef dosya yolu.  Varsayilan ``data/index.json``.

    Returns
    -------
    Path
        Kaydedilen dosyanin mutlak yolu.

    Examples
    --------
    >>> saved = save_index(index)
    >>> print(saved)
    C:\\Projects\\SourceSniff\\data\\index.json
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as fh:
        json.dump(
            index,
            fh,
            ensure_ascii=False,
            indent=2,
        )

    size_kb = path.stat().st_size / 1024
    print(f"[+] Indeks kaydedildi: {path}  ({size_kb:.1f} KB)")
    return path


def load_index(index_path: str | Path = "data/index.json") -> InvertedIndex:
    """Daha once diske kaydedilmis inverted index'i JSON dosyasindan
    geri yukler.

    Parameters
    ----------
    index_path : str | Path, optional
        Okunacak indeks dosyasinin yolu.  Varsayilan ``data/index.json``.

    Returns
    -------
    InvertedIndex
        ``{kelime: [Posting, ...]}`` biciminde ters dizin sozlugu.

    Raises
    ------
    FileNotFoundError
        Belirtilen dosya bulunamazsa.

    Examples
    --------
    >>> index = load_index("data/index.json")
    >>> print(f"{len(index)} benzersiz kelime yuklendi.")
    347 benzersiz kelime yuklendi.
    """
    path = Path(index_path).resolve()

    with path.open("r", encoding="utf-8") as fh:
        index: InvertedIndex = json.load(fh)

    print(f"[+] Indeks yuklendi: {path}  ({len(index)} benzersiz kelime)")
    return index


# ────────────────────────────────────────────────────────────────────
# Kolaylik fonksiyonu:  Tara → Indeksle → Kaydet
# ────────────────────────────────────────────────────────────────────
def build_and_save(
    root: str | Path,
    output_path: str | Path = "data/index.json",
    **scan_kwargs,
) -> InvertedIndex:
    """Tek satirda tam pipeline calistirir:
    ``scan_directory`` -> ``build_inverted_index`` -> ``save_index``.

    Parameters
    ----------
    root : str | Path
        Taranacak kok dizin.
    output_path : str | Path, optional
        Indeks dosyasinin kaydedilecegi yol.
    **scan_kwargs
        ``scan_directory`` fonksiyonuna iletilecek ek parametreler
        (``extensions``, ``config_path``).

    Returns
    -------
    InvertedIndex
        Olusturulan ve kaydedilen indeks.
    """
    t0 = time.perf_counter()

    files = scan_directory(root, **scan_kwargs)
    print(f"[1/3] {len(files)} dosya bulundu.")

    index = build_inverted_index(files)
    print(f"[2/3] {len(index)} benzersiz kelime indekslendi.")

    save_index(index, output_path)
    elapsed = time.perf_counter() - t0
    print(f"[3/3] Tamamlandi! ({elapsed:.2f}s)")

    return index


# ────────────────────────────────────────────────────────────────────
# Dogrudan calistirma destegi (test / demo)
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Kullanim: python -m core.indexer <dizin_yolu> [cikti_yolu]")
        print("Ornek  : python -m core.indexer .  data/index.json")
        sys.exit(1)

    target_dir = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) >= 3 else "data/index.json"

    print(f"\n{'='*60}")
    print(f"  SourceSniff — Inverted Index Builder")
    print(f"{'='*60}\n")

    index = build_and_save(target_dir, out_path)

    # ── Ornek cikti ────────────────────────────────────────────────
    print(f"\n--- Ornek girisler (ilk 10 kelime) ---\n")
    for word in list(index.keys())[:10]:
        postings = index[word]
        total_lines = sum(len(p["lines"]) for p in postings)
        print(f'  "{word}"  ->  {len(postings)} dosya, {total_lines} gecis')
        for p in postings[:2]:
            short_path = Path(p["path"]).name
            print(f'      {short_path}  satirlar: {p["lines"][:5]}')
            print(f'      preview: {p["preview"][:80]}')

    # ── Geri yukleme testi ─────────────────────────────────────────
    print(f"\n--- Deserializasyon testi ---\n")
    reloaded = load_index(out_path)
    assert len(reloaded) == len(index), "Veri kaybi tespit edildi!"
    print("[OK] Serializasyon / deserializasyon basarili.")

