/**
 * SourceSniff — Frontend Application
 * ====================================
 * FastAPI backend ile iletisim kuran tek sayfalik uygulama.
 *
 * API Endpointleri:
 *   POST /api/scan    → Dizin tarama baslat
 *   GET  /api/search  → Kelime ara
 *   GET  /api/status  → Indeksleme durumu
 */

// ────────────────────────────────────────────────────────────────
// Yapilandirma
// ────────────────────────────────────────────────────────────────
const API_BASE = window.location.origin;

// ────────────────────────────────────────────────────────────────
// DOM Referanslari
// ────────────────────────────────────────────────────────────────
const $scanPath     = document.getElementById("scanPathInput");
const $scanBtn      = document.getElementById("scanBtn");
const $scanMessage  = document.getElementById("scanMessage");
const $searchInput  = document.getElementById("searchInput");
const $statusBadge  = document.getElementById("statusBadge");
const $statusText   = document.getElementById("statusText");
const $statsBar     = document.getElementById("statsBar");
const $statFiles    = document.getElementById("statFiles");
const $statOccur    = document.getElementById("statOccurrences");
const $statQuery    = document.getElementById("statQuery");
const $fileList     = document.getElementById("fileList");
const $fileCount    = document.getElementById("fileCount");
const $codePreview  = document.getElementById("codePreview");
const $previewTitle = document.getElementById("previewTitle");
const $lineCount    = document.getElementById("lineCount");

// ────────────────────────────────────────────────────────────────
// Durum
// ────────────────────────────────────────────────────────────────
let currentResults  = [];      // Arama sonuclari
let selectedFileIdx = -1;      // Secili dosya indeksi
let statusPollTimer = null;    // Durum sorgulama zamanlayicisi
let searchDebounce  = null;    // Arama gecikme zamanlayicisi
let searchQuery     = "";      // Son aranan kelime

// ────────────────────────────────────────────────────────────────
// API Yardimcilari
// ────────────────────────────────────────────────────────────────
async function apiGet(path) {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

async function apiPost(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

// ────────────────────────────────────────────────────────────────
// POST /api/scan — Tarama Baslat
// ────────────────────────────────────────────────────────────────
async function startScan() {
    const path = $scanPath.value.trim();
    if (!path) {
        showScanMsg("Lutfen bir klasor yolu girin.", "var(--accent-red)");
        $scanPath.focus();
        return;
    }

    $scanBtn.disabled = true;
    $scanBtn.innerHTML = '<span class="spinner"></span> Baslatiliyor...';

    try {
        const data = await apiPost("/api/scan", { path });
        showScanMsg(data.message, "var(--accent-green)");
        startStatusPolling();
    } catch (err) {
        showScanMsg(err.message, "var(--accent-red)");
    } finally {
        $scanBtn.disabled = false;
        $scanBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
            Taramayi Baslat`;
    }
}

function showScanMsg(text, color) {
    $scanMessage.textContent = text;
    $scanMessage.style.color = color;
    $scanMessage.style.display = "block";
    setTimeout(() => { $scanMessage.style.display = "none"; }, 6000);
}

// ────────────────────────────────────────────────────────────────
// GET /api/status — Durum Sorgulama (Polling)
// ────────────────────────────────────────────────────────────────
function startStatusPolling() {
    stopStatusPolling();
    pollStatus();
    statusPollTimer = setInterval(pollStatus, 1500);
}

function stopStatusPolling() {
    if (statusPollTimer) {
        clearInterval(statusPollTimer);
        statusPollTimer = null;
    }
}

async function pollStatus() {
    try {
        const data = await apiGet("/api/status");
        updateStatusBadge(data);

        if (!data.is_indexing && statusPollTimer) {
            stopStatusPolling();
        }
    } catch {
        // Sessizce devam et
    }
}

function updateStatusBadge(data) {
    $statusBadge.className = "status-badge";

    if (data.is_indexing) {
        $statusBadge.classList.add("status-indexing");
        $statusText.textContent = "Indeksleniyor...";
    } else if (data.total_words > 0) {
        $statusBadge.classList.add("status-done");
        $statusText.textContent = `${data.total_words.toLocaleString("tr-TR")} kelime`;
    } else if (data.message && data.message.startsWith("Hata")) {
        $statusBadge.classList.add("status-error");
        $statusText.textContent = "Hata";
    } else {
        $statusBadge.classList.add("status-idle");
        $statusText.textContent = "Hazir";
    }
}

// ────────────────────────────────────────────────────────────────
// GET /api/search — Arama
// ────────────────────────────────────────────────────────────────
async function performSearch(query) {
    query = query.trim();
    if (!query) {
        clearResults();
        return;
    }

    searchQuery = query;

    try {
        const data = await apiGet(`/api/search?q=${encodeURIComponent(query)}`);
        currentResults = data.results || [];
        selectedFileIdx = -1;

        // Stats bar
        $statsBar.style.display = "flex";
        $statFiles.textContent = data.total_files;
        $statOccur.textContent = data.total_occurrences;
        $statQuery.textContent = data.query;

        renderFileList();

        // Ilk dosyayi otomatik sec
        if (currentResults.length > 0) {
            selectFile(0);
        } else {
            renderEmptyCodePreview("Sonuc bulunamadi",
                `"${escapeHtml(query)}" icin eslesen dosya yok.`);
        }
    } catch (err) {
        clearResults();
        renderEmptyCodePreview("Hata", err.message);
    }
}

function clearResults() {
    currentResults = [];
    selectedFileIdx = -1;
    $statsBar.style.display = "none";

    $fileList.innerHTML = `
        <div class="empty-state">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
            </svg>
            <p>Arama yaparak<br>dosyalari kesfet</p>
        </div>`;
    $fileCount.textContent = "0";

    renderEmptyCodePreview("Kod Onizleme",
        "Sol panelden bir dosya secerek<br>kod satirlarini goruntuleyebilirsiniz");
}

// ────────────────────────────────────────────────────────────────
// Sol Panel: Dosya Listesi
// ────────────────────────────────────────────────────────────────
function renderFileList() {
    $fileCount.textContent = currentResults.length;

    if (currentResults.length === 0) {
        $fileList.innerHTML = `
            <div class="empty-state">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>
                </svg>
                <p>Sonuc bulunamadi</p>
            </div>`;
        return;
    }

    let html = "";
    currentResults.forEach((result, idx) => {
        const fileName = result.path.split(/[/\\]/).pop();
        const dirPath  = result.path.split(/[/\\]/).slice(-3, -1).join("/");
        const ext      = fileName.split(".").pop().toUpperCase();
        const lineCount = result.lines.length;

        html += `
            <div class="file-item fade-in-up ${idx === selectedFileIdx ? "active" : ""}"
                 onclick="selectFile(${idx})"
                 style="animation-delay: ${idx * 30}ms;">
                <div class="file-name">
                    <span>${getFileIcon(ext)}</span>
                    <span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(fileName)}</span>
                    <span class="file-badge">${lineCount} satir</span>
                </div>
                <div class="file-path">${escapeHtml(dirPath)}</div>
            </div>`;
    });

    $fileList.innerHTML = html;
}

function getFileIcon(ext) {
    const icons = {
        PY:   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/></svg>',
        JS:   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/></svg>',
        JAVA: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/></svg>',
        CPP:  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/></svg>',
    };
    return icons[ext] || '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>';
}

// ────────────────────────────────────────────────────────────────
// Sag Panel: Kod Onizleme
// ────────────────────────────────────────────────────────────────
function getLanguageFromExt(ext) {
    const map = {
        'PY': 'python',
        'JS': 'javascript',
        'TS': 'typescript',
        'JAVA': 'java',
        'CPP': 'cpp',
        'C': 'c',
        'CS': 'csharp',
        'HTML': 'html',
        'CSS': 'css',
        'JSON': 'json',
        'MD': 'markdown',
        'SQL': 'sql'
    };
    return map[ext] || 'plaintext';
}
function selectFile(idx) {
    selectedFileIdx = idx;
    const result = currentResults[idx];

    if (!result) return;

    // Sol panelde aktif dosyayi guncelle
    document.querySelectorAll(".file-item").forEach((el, i) => {
        el.classList.toggle("active", i === idx);
    });

    // Baslik
    const fileName = result.path.split(/[/\\]/).pop();
    $previewTitle.innerHTML = `
        <span style="display:flex; align-items:center; gap:6px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" stroke-width="2">
                <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
            </svg>
            ${escapeHtml(fileName)}
        </span>`;
    $lineCount.textContent = `${result.lines.length} satir`;

    // Kod satirlari
    const ext = fileName.split(".").pop().toUpperCase();
    const lang = getLanguageFromExt(ext);

    let html = "";
    result.lines.forEach((lineNo, i) => {
        // Preview, tum satirlar icin ayni (ilk gecis) ama her satir numarasi farkli
        const preview = result.preview || "";
        
        let syntaxHighlighted = escapeHtml(preview);
        try {
            // Highlight.js ile renklendirme
            if (lang !== 'plaintext' && window.hljs) {
                syntaxHighlighted = hljs.highlight(preview, { language: lang, ignoreIllegals: true }).value;
            }
        } catch (e) {
            // Fallback: Normal HTML escaping (hata olursa)
        }

        // Arama sorgusunu (sadece tag disindaki metinleri) vurgula
        const highlighted = highlightQuery(syntaxHighlighted, searchQuery);

        html += `
            <div class="code-line fade-in-up" style="animation-delay: ${i * 25}ms;">
                <span class="line-number">${lineNo}</span>
                <span class="line-content">${highlighted}</span>
            </div>`;
    });

    $codePreview.innerHTML = html;
}

function highlightQuery(htmlString, query) {
    if (!query) return htmlString;
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    // Regex: Sadece HTML tag'leri disindaki (< ... > arasinda olmayan) metinleri eslestirir
    const regex = new RegExp(`(${escaped})(?![^<]*>)`, "gi");
    return htmlString.replace(regex, '<span class="search-highlight">$1</span>');
}

function renderEmptyCodePreview(title, message) {
    $previewTitle.textContent = title;
    $lineCount.textContent = "0 satir";
    $codePreview.innerHTML = `
        <div class="empty-state">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
            </svg>
            <p>${message}</p>
        </div>`;
}

// ────────────────────────────────────────────────────────────────
// Yardimci
// ────────────────────────────────────────────────────────────────
function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// ────────────────────────────────────────────────────────────────
// Olay Dinleyiciler
// ────────────────────────────────────────────────────────────────

// Arama cubugu — Enter ile ara, debounce ile canli arama
$searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        if (searchDebounce) clearTimeout(searchDebounce);
        performSearch($searchInput.value);
    }
});

$searchInput.addEventListener("input", () => {
    if (searchDebounce) clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
        performSearch($searchInput.value);
    }, 400);
});

// Tarama — Enter ile baslat
$scanPath.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        startScan();
    }
});

// Klavye kisayollari
document.addEventListener("keydown", (e) => {
    // Ctrl+K veya / → Arama kutusuna odaklan
    if ((e.ctrlKey && e.key === "k") || (e.key === "/" && document.activeElement === document.body)) {
        e.preventDefault();
        $searchInput.focus();
        $searchInput.select();
    }

    // Escape → Odagi kaldir
    if (e.key === "Escape") {
        document.activeElement.blur();
    }

    // Arrow Up/Down → Dosya listesinde gezin
    if (currentResults.length > 0) {
        if (e.key === "ArrowDown" && document.activeElement === $searchInput) {
            e.preventDefault();
            selectFile(Math.min(selectedFileIdx + 1, currentResults.length - 1));
        }
        if (e.key === "ArrowUp" && document.activeElement === $searchInput) {
            e.preventDefault();
            selectFile(Math.max(selectedFileIdx - 1, 0));
        }
    }
});

// ────────────────────────────────────────────────────────────────
// Baslangic
// ────────────────────────────────────────────────────────────────
(async function init() {
    // Baslangicta durumu kontrol et
    try {
        const status = await apiGet("/api/status");
        updateStatusBadge(status);

        if (status.is_indexing) {
            startStatusPolling();
        }
    } catch {
        // Sunucu baglantisi yok
    }

    // Arama kutusuna odaklan
    $searchInput.focus();
})();
