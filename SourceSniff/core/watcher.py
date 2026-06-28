"""
File Watcher — SourceSniff Core
=================================
Python ``watchdog`` kutuphanesini kullanarak belirtilen klasordeki dosya
degisikliklerini (olusturma, silme, guncelleme, tasima) anlik izler.

Bir dosya degistiginde tum projeyi bastan taramak yerine **yalnizca o
dosyanin** icerigi regex ile tekrar parse edilir ve mevcut
``data/index.json`` dosyasindaki Inverted Index artimsal olarak
guncellenir.

Kullanim
--------
Komut satirindan::

    python -m core.watcher C:\\Projects\\my_app

veya Python icinden::

    from core.watcher import start_watching
    start_watching("C:/Projects/my_app")
"""

from __future__ import annotations

import time
import threading
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, Set

from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
)

from core.indexer import (
    InvertedIndex,
    load_index,
    save_index,
    add_file_to_index,
    remove_file_from_index,
    update_file_in_index,
    _load_ignore_list,
    _is_ignored,
    _CONFIG_PATH,
    _TARGET_EXTENSIONS,
)


# ────────────────────────────────────────────────────────────────────
# Debouncer — Hizli ardisik degisiklikleri birlestirme
# ────────────────────────────────────────────────────────────────────
class _DebouncedSaver:
    """Kisa sureli ardisik degisiklikleri birlestirerek diske yazma
    islemini optimize eder.

    Her degisiklik geldiginde zamanlayici sifirlenir.  Belirlenen
    ``delay`` suresi boyunca yeni bir degisiklik gelmezse indeks
    diske kaydedilir.

    Parameters
    ----------
    index : InvertedIndex
        Kaydedilecek indeks referansi.
    output_path : str
        Hedef ``index.json`` dosya yolu.
    delay : float
        Bekleme suresi (saniye).  Varsayilan 2.0s.
    """

    def __init__(
        self,
        index: InvertedIndex,
        output_path: str,
        delay: float = 2.0,
    ) -> None:
        self._index = index
        self._output_path = output_path
        self._delay = delay
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._pending_count = 0

    def trigger(self) -> None:
        """Kaydetme zamanlayicisini (yeniden) baslat."""
        with self._lock:
            self._pending_count += 1

            if self._timer is not None:
                self._timer.cancel()

            self._timer = threading.Timer(self._delay, self._save)
            self._timer.daemon = True
            self._timer.start()

    def _save(self) -> None:
        """Indeksi diske yaz ve sayaci sifirla."""
        with self._lock:
            count = self._pending_count
            self._pending_count = 0

        now = datetime.now().strftime("%H:%M:%S")
        print(f"  [{now}] {count} degisiklik birikti, indeks kaydediliyor...")
        save_index(self._index, self._output_path)

    def flush(self) -> None:
        """Bekleyen kaydetme islemini hemen calistir."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        if self._pending_count > 0:
            self._save()


# ────────────────────────────────────────────────────────────────────
# Watchdog Event Handler
# ────────────────────────────────────────────────────────────────────
class _IndexUpdateHandler(FileSystemEventHandler):
    """Dosya sistemi olaylarini yakalayarak indeksi artimsal gunceller.

    Yalnizca hedef uzantilara sahip dosyalari isler.
    Kara listedeki dizinlerdeki olaylari yok sayar.

    Parameters
    ----------
    index : InvertedIndex
        Bellekteki ters dizin referansi.
    saver : _DebouncedSaver
        Debounced kaydetme nesnesi.
    extensions : set[str]
        Izlenecek dosya uzantilari.
    ignore_patterns : list[str]
        Kara liste kaliplari.
    """

    def __init__(
        self,
        index: InvertedIndex,
        saver: _DebouncedSaver,
        extensions: Set[str],
        ignore_patterns: list[str],
    ) -> None:
        super().__init__()
        self._index = index
        self._saver = saver
        self._extensions = extensions
        self._ignore_patterns = ignore_patterns

    # ── Yardimci metodlar ─────────────────────────────────────────

    def _should_process(self, path: str) -> bool:
        """Dosyanin islenip islenmeyecegini belirler."""
        p = Path(path)

        # Uzanti kontrolu
        if p.suffix.lower() not in self._extensions:
            return False

        # Kara liste kontrolu — yolun herhangi bir parcasi kara listede mi?
        for part in p.parts:
            if _is_ignored(part, self._ignore_patterns):
                return False

        return True

    def _now(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    # ── Olay isleyicileri ─────────────────────────────────────────

    def on_created(self, event: FileCreatedEvent) -> None:
        """Yeni dosya olusturuldu -> indekse ekle."""
        if event.is_directory or not self._should_process(event.src_path):
            return

        # Dosyanin yazilmasini bitirmesi icin kisa bekleme
        time.sleep(0.1)

        name = Path(event.src_path).name
        added = add_file_to_index(self._index, event.src_path)
        print(f"  [{self._now()}] [+] OLUSTURULDU: {name}  ({added} yeni kelime)")
        self._saver.trigger()

    def on_deleted(self, event: FileDeletedEvent) -> None:
        """Dosya silindi -> indeksten cikar."""
        if event.is_directory or not self._should_process(event.src_path):
            return

        name = Path(event.src_path).name
        removed = remove_file_from_index(self._index, event.src_path)
        print(f"  [{self._now()}] [-] SILINDI: {name}  ({removed} kelimeden cikarildi)")
        self._saver.trigger()

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Dosya guncellendi -> yalnizca bu dosyayi yeniden parse et."""
        if event.is_directory or not self._should_process(event.src_path):
            return

        # Dosyanin yazilmasini bitirmesi icin kisa bekleme
        time.sleep(0.1)

        name = Path(event.src_path).name
        update_file_in_index(self._index, event.src_path)
        print(f"  [{self._now()}] [~] GUNCELLENDI: {name}")
        self._saver.trigger()

    def on_moved(self, event: FileMovedEvent) -> None:
        """Dosya tasindi / yeniden adlandirildi."""
        if event.is_directory:
            return

        src_ok = self._should_process(event.src_path)
        dst_ok = self._should_process(event.dest_path)

        old_name = Path(event.src_path).name
        new_name = Path(event.dest_path).name

        if src_ok:
            remove_file_from_index(self._index, event.src_path)
            print(f"  [{self._now()}] [-] TASINDI (eski): {old_name}")

        if dst_ok:
            add_file_to_index(self._index, event.dest_path)
            print(f"  [{self._now()}] [+] TASINDI (yeni): {new_name}")

        if src_ok or dst_ok:
            self._saver.trigger()


# ────────────────────────────────────────────────────────────────────
# Ana baslatma fonksiyonu
# ────────────────────────────────────────────────────────────────────
def start_watching(
    root: str | Path,
    *,
    index_path: str | Path = "data/index.json",
    extensions: Set[str] | None = None,
    config_path: Path | None = None,
    debounce_delay: float = 2.0,
) -> None:
    """Belirtilen dizini canli olarak izlemeye baslar.

    Mevcut ``index.json`` dosyasini yukler ve dosya degisikliklerini
    anlik takip ederek indeksi artimsal gunceller.

    Parameters
    ----------
    root : str | Path
        Izlenecek kok dizin.
    index_path : str | Path, optional
        Mevcut indeks dosyasinin yolu.  Varsayilan ``data/index.json``.
    extensions : set[str] | None, optional
        Izlenecek dosya uzantilari.  ``None`` ise varsayilan kume kullanilir.
    config_path : Path | None, optional
        Alternatif ``config.json`` yolu.
    debounce_delay : float, optional
        Diske yazma gecikmesi (saniye).  Varsayilan 2.0s.

    Notes
    -----
    Ctrl+C ile durdurulabilir.  Durdurmadan once bekleyen degisiklikler
    otomatik olarak diske yazilir (flush).
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise NotADirectoryError(f"Gecersiz dizin: {root_path}")

    cfg = config_path if config_path is not None else _CONFIG_PATH
    ext = extensions if extensions is not None else _TARGET_EXTENSIONS
    ignore_patterns = _load_ignore_list(cfg)

    # ── Mevcut indeksi yukle ──────────────────────────────────────
    idx_file = Path(index_path).resolve()
    if idx_file.exists():
        index = load_index(index_path)
    else:
        print("[!] Mevcut indeks bulunamadi, bos indeks ile baslatiliyor.")
        print("    Ipucu: Once 'python -m core.indexer <dizin>' ile indeks olusturun.")
        index = {}

    # ── Bilesenler ────────────────────────────────────────────────
    saver = _DebouncedSaver(index, str(index_path), debounce_delay)
    handler = _IndexUpdateHandler(index, saver, ext, ignore_patterns)
    observer = Observer()
    observer.schedule(handler, str(root_path), recursive=True)

    # ── Basla ─────────────────────────────────────────────────────
    observer.start()

    print(f"\n{'='*60}")
    print(f"  SourceSniff File Watcher")
    print(f"{'='*60}")
    print(f"  Dizin     : {root_path}")
    print(f"  Indeks    : {idx_file}")
    print(f"  Uzantilar : {', '.join(sorted(ext))}")
    print(f"  Debounce  : {debounce_delay}s")
    print(f"  Kelime    : {len(index)} benzersiz kelime")
    print(f"{'='*60}")
    print(f"  Degisiklikler izleniyor... (Ctrl+C ile durdur)\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[!] Durduruluyor...")
    finally:
        observer.stop()
        observer.join()
        saver.flush()
        print("[OK] Watcher durduruldu.")


# ────────────────────────────────────────────────────────────────────
# Dogrudan calistirma destegi
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Kullanim: python -m core.watcher <dizin_yolu> [indeks_yolu]")
        print("Ornek  : python -m core.watcher .  data/index.json")
        sys.exit(1)

    watch_dir = sys.argv[1]
    idx_path = sys.argv[2] if len(sys.argv) >= 3 else "data/index.json"

    start_watching(watch_dir, index_path=idx_path)
