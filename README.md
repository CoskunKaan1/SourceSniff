# SourceSniff 🔍

**SourceSniff** is a lightning-fast, locally hosted code search engine with a modern FastAPI backend and a sleek Dark Mode UI. It allows you to search through your project's source code instantly.

By utilizing an advanced "Inverted Index" architecture, it finds exactly which file and line your search query appears in within milliseconds, rather than scanning the entire project on every search. Thanks to `watchdog` integration, it actively monitors your files for changes in real-time and incrementally updates its index in the background only for the files that were modified.

![SourceSniff UI Preview]<img width="1919" height="905" alt="image" src="https://github.com/user-attachments/assets/4bdb9c47-e184-4963-9329-ecdd52ad0506" />


## ✨ Features

- 🚀 **Blazing Fast Search (Inverted Index):** Searches are executed in milliseconds using a cached inverted index instead of scanning through all files from scratch.
- 🔄 **Live File Watching (Watchdog):** When you add, modify, or delete a file in your project, SourceSniff detects it and incrementally updates the index for that specific file without having to rescan the entire directory.
- 🎨 **Modern Dark Mode UI:** A gorgeous, Glassmorphism-inspired UI designed with Tailwind CSS, featuring ambient background glow and smooth micro-animations.
- ⚡ **Live Search (Debounce):** The search automatically triggers as you type with a 400ms debounce, giving you instant, real-time results without pressing Enter.
- 🌈 **Syntax Highlighting:** The code preview panel automatically highlights the matched lines based on the file extension using Highlight.js, and highlights the search query with an amber accent.
- 🛡️ **Smart Ignored Directories:** Improves performance by skipping directories defined in `config.json` (such as `.git`, `node_modules`, `__pycache__`).

## 🛠️ Tech Stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn
- **Core Engine:** Python Standard Library (`pathlib`, `re`, `json`, `threading`), Watchdog
- **Frontend:** HTML5, Vanilla JavaScript, Tailwind CSS, Highlight.js

## 📂 Project Structure

```text
SourceSniff/
├── backend/
│   ├── main.py              # FastAPI entry point & static file serving
│   ├── models/
│   │   └── schemas.py       # Pydantic request/response data models
│   └── routes/
│       └── search.py        # /api/scan, /api/search, /api/status endpoints
├── core/
│   ├── indexer.py           # Inverted index generation, saving, and incremental updates
│   ├── parser.py            # Source code cleaning and tokenization (Regex)
│   └── watcher.py           # Watchdog daemon for live file system events
├── frontend/
│   ├── index.html           # SPA Main UI
│   ├── css/
│   │   └── style.css        # Custom Dark Mode & animation styles
│   └── js/
│       └── app.js           # API communication, UI logic, and search debounce
├── data/                    # Directory for the generated index.json
├── config.json              # Blacklist (ignore list) settings
└── requirements.txt         # Dependencies
```

## 🚀 Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/yourusername/sourcesniff.git
   cd sourcesniff
   ```

2. **Install Dependencies:**
   Ensure you have Python installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the Application:**
   ```bash
   python -m uvicorn backend.main:app --port 8000
   ```

4. **Start Searching:**
   Open your browser and navigate to **http://localhost:8000**.

## ⚙️ Usage Instructions

1. Enter the absolute path of any project folder on your machine (e.g., `C:\Projects\my_app`) into the "Scan Project Directory" input field at the top left of the UI.
2. Click the **Start Scan** button. The indexing process will run asynchronously in the background.
3. Once completed, type the class, function, or variable you are looking for into the large search bar.
4. View the matched files in the left panel, and click on any file to examine the syntax-highlighted code preview in the right panel!

## 🤝 Contributing

Pull requests are always welcome. For major changes, please open an *Issue* first to discuss what you would like to change.

## 📝 License

This project is licensed under the [MIT License](LICENSE).
