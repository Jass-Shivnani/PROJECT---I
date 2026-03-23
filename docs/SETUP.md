# 🚀 DIONE AI — Complete Setup & Running Guide

**Getting DIONE AI running from scratch on your machine**

> This guide covers full stack setup: backend server, mobile app, LLM integration, and plugins.

---

## 📋 Prerequisites

Before you start, ensure you have:

- **Python 3.10+** (tested with Python 3.14)
- **Git** (for cloning)
- **Flutter SDK 3.2+** (only if running mobile app)
- **RAM:** 8GB+ (LLM models need memory)
- **Disk Space:** 20GB+ (for models and data)
- **Network:** Local machine or same network (backend runs on localhost)

### Optional but Recommended:
- **Ollama** (simplified LLM management)
- **Docker** (for containerized deployment)
- **VS Code** (for development)

---

## ⚡ Quick Start (5 minutes)

**Just want it running fast?**

```bash
# 1. Clone
git clone https://github.com/Jass-Shivnani/PROJECT---I.git
cd "PROJECT - I"

# 2. Setup Python backend
python -m venv .venv
.venv\Scripts\activate              # Windows: or source .venv/bin/activate on Mac/Linux
cd server
pip install -r requirements.txt

# 3. Start Ollama (separate terminal)
# Download from https://ollama.ai, then:
ollama serve
ollama pull mistral

# 4. Start Dione server
cd server
python -m server.main --port 8000

# 5. Open in browser
# http://localhost:8000/docs
```

Then jump to **[Part 2: Mobile App Setup](#part-2-mobile-app-setup-flutter)** if you want the app.

---

## 📦 Part 1: Backend Server Setup (Python)

### Step 1: Clone the Repository

```bash
git clone https://github.com/Jass-Shivnani/PROJECT---I.git
cd "PROJECT - I"
```

### Step 2: Create Python Virtual Environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your terminal prefix now.

### Step 3: Install Python Dependencies

```bash
cd server
pip install -r requirements.txt
```

**What it installs:**
- FastAPI & Uvicorn (web server)
- Ollama / llama-cpp (LLM backends)
- ChromaDB (vector store)
- Transformers (sentiment analysis)
- NetworkX (knowledge graph)
- Plus plugins, auth, and utility libraries

> ⏱️ This takes 3-5 minutes depending on internet speed

### Step 4: Set Up Environment Variables

Create a `.env` file in the **project root** (not in `server/`):

```env
# ===== Server Configuration =====
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_RELOAD=true              # Enable hot-reload for development

# ===== LLM Configuration =====
LLM_BACKEND=ollama              # Options: "ollama" or "llamacpp"
LLM_MODEL=mistral              # Model name (for Ollama)
LLM_BASE_URL=http://localhost:11434  # Ollama default URL
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.7

# ===== Knowledge Graph =====
GRAPH_DB_PATH=data/knowledge/graph.json
GRAPH_DB_TYPE=json              # Options: "json" or "neo4j"

# ===== Vector Store & Embeddings =====
VECTOR_STORE_PATH=data/vectors/chroma.sqlite3
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHROMA_PERSIST_DIR=data/vectors

# ===== Sentiment Analysis =====
SENTIMENT_MODEL=distilbert-base-uncased-finetuned-sst-2-english
SENTIMENT_DEVICE=cpu            # Options: "cpu" or "cuda"

# ===== Logging =====
LOG_LEVEL=info                  # Options: debug, info, warning, error
LOG_DIR=data/logs

# ===== API Keys (for plugins) =====
# Gmail - Get from: https://myaccount.google.com/
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret

# WhatsApp - Optional
WHATSAPP_PHONE_ID=your_phone_id

# ===== Security =====
SECRET_KEY=your-super-secret-key-change-this
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# ===== Development =====
DEBUG=false
ALLOWED_ORIGINS=http://localhost:*,http://10.0.2.2:*
```

### Step 5: Set Up LLM Backend

**You MUST choose one:**

#### **Option A: Ollama (Recommended - Easiest)**

1. Download Ollama from [ollama.ai](https://ollama.ai)
2. Install and run:
   ```bash
   ollama serve
   ```
3. In another terminal, pull a model:
   ```bash
   ollama pull mistral
   ```
   > Other models: `ollama pull llama2`, `ollama pull neural-chat`, etc.
4. Verify it works:
   ```bash
   curl http://localhost:11434/api/tags
   ```

**That's it!** The server will auto-connect to Ollama.

#### **Option B: llama.cpp (For Direct Model Control)**

1. Uncomment in `server/requirements.txt`:
   ```
   llama-cpp-python>=0.2.0
   ```

2. Download a GGUF model:
   - Mistral 7B: [huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF)
   - Save to `models/mistral-7b.gguf`

3. Update `.env`:
   ```env
   LLM_BACKEND=llamacpp
   LLM_MODEL_PATH=models/mistral-7b.gguf
   ```

4. Reinstall:
   ```bash
   pip install -r requirements.txt
   ```

### Step 6: Create Data Directories

```bash
cd ..  # Go back to project root
mkdir -p data/logs data/knowledge data/vectors data/memories data/plugins data/credentials
```

This creates folders for:
- `logs/` — Server logs
- `knowledge/` — Knowledge graph data
- `vectors/` — Embedding databases (ChromaDB)
- `memories/` — Conversation memories
- `plugins/` — Plugin data
- `credentials/` — API keys for plugins

### Step 7: Start the Server

```bash
cd server
python -m server.main --port 8000
```

**Expected output:**
```
2026-03-23T10:30:45.123 | INFO | dione | Server starting...
2026-03-23T10:30:47.456 | INFO | dione | Connected to LLM backend (Ollama)
2026-03-23T10:30:48.789 | INFO | uvicorn | Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

✅ **Backend is ready!**

### Verify Backend is Working

Open in browser or curl:
```bash
# Browser
http://localhost:8000/docs                    # Interactive API docs
http://localhost:8000/health                  # Health check

# Terminal
curl http://localhost:8000/health
# Expected: {"status": "healthy", "llm": "connected"}
```

---

## 📱 Part 2: Mobile App Setup (Flutter)

### Step 1: Install Flutter SDK

1. Download from [flutter.dev](https://flutter.dev/docs/get-started/install)
2. Extract to a location (e.g., `C:\flutter` on Windows)
3. Add to PATH:
   - **Windows:** Add `C:\flutter\bin` to System Environment Variables
   - **macOS/Linux:** Add to `~/.bashrc` or `~/.zshrc`:
     ```bash
     export PATH="$PATH:$HOME/flutter/bin"
     ```
4. Verify installation:
   ```bash
   flutter --version
   flutter doctor
   ```

### Step 2: Get Project Dependencies

```bash
cd mobile/dione_app
flutter pub get
```

**What it downloads:**
- UI framework (Cupertino, Google Fonts)
- State management (Provider)
- Networking (WebSocket, HTTP)
- Local storage (Hive, SharedPreferences)

### Step 3: Configure Backend URL

Edit `lib/config/api_config.dart` (create if doesn't exist):

```dart
// lib/config/api_config.dart
class ApiConfig {
  // For local development on PC
  static const String API_BASE_URL = 'http://localhost:8000';
  static const String WS_BASE_URL = 'ws://localhost:8000';
  
  // Uncomment these for Android Emulator
  // static const String API_BASE_URL = 'http://10.0.2.2:8000';
  // static const String WS_BASE_URL = 'ws://10.0.2.2:8000';
  
  // For production, use your server IP
  // static const String API_BASE_URL = 'http://192.168.1.100:8000';
}
```

**Important Network Notes:**

| Device | URL |
|--------|-----|
| Windows Desktop | `http://localhost:8000` |
| macOS Desktop | `http://localhost:8000` |
| Android Emulator | `http://10.0.2.2:8000` (special host) |
| Physical Android Phone | `http://<YOUR_PC_IP>:8000` |
| iOS Simulator | `http://localhost:8000` |

### Step 4: Run the Mobile App

**On Windows Desktop:**
```bash
flutter run -d windows
```

**On Android Emulator:**
```bash
# Start emulator first
emulator -avd Pixel_4_API_30

# Then run
flutter run
```

**On Physical Android Device:**
```bash
# Enable Developer Mode on phone, then:
flutter run
```

**On macOS Desktop:**
```bash
flutter run -d macos
```

**On iOS Simulator:**
```bash
open -a Simulator
flutter run -d all
```

### Step 5: Hot Reload (Development)

While the app is running:
- Press `r` → Hot reload (code changes only)
- Press `R` → Full restart (reset state)
- Press `q` → Quit

---

## 🔌 Part 3: Configure Plugins (Optional)

### Gmail Integration

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (type: Web Application)
5. Download credentials as JSON
6. Save to: `data/credentials/gmail.json`
7. Add to `.env`:
   ```env
   GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GMAIL_CLIENT_SECRET=your-secret
   ```

### WhatsApp Integration

1. Get WhatsApp Business Account & Phone Number ID
2. Generate API token from Meta for Developers
3. Add to `.env`:
   ```env
   WHATSAPP_PHONE_ID=your-phone-id
   WHATSAPP_API_TOKEN=your-access-token
   ```

---

## 🎯 Full Stack: Running Everything

### Terminal 1: Backend Server

```bash
cd "PROJECT - I"
.venv\Scripts\activate              # Activate virtual environment
cd server
python -m server.main
```

### Terminal 2: LLM Backend (if using Ollama)

```bash
ollama serve
```

### Terminal 3: Mobile App

```bash
cd "PROJECT - I"/mobile/dione_app
flutter run -d windows              # or android, ios, etc.
```

### Open in Browser

- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **WebSocket Chat:** http://localhost:8000/ws

---

## 🧪 Testing the Integration

### 1. Test Backend Health

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "llm_connected": true,
  "model": "mistral",
  "knowledge_graph_ready": true
}
```

### 2. Test Chat Endpoint

Open http://localhost:8000/docs, find the `/chat` endpoint, and test:

```json
{
  "message": "Hello, Dione! What's your name?",
  "user_id": "jass"
}
```

### 3. Test Mobile App

1. Open app
2. Go through onboarding
3. Type a message
4. Should receive response from server

---

## 🐛 Troubleshooting

### "Connection refused: 8000"
- **Problem:** Backend not running
- **Solution:** 
  ```bash
  cd server
  python -m server.main
  ```

### "LLM model not found / LLM not responding"
- **Problem:** Ollama not running
- **Solution:**
  ```bash
  ollama serve
  ollama pull mistral
  ```

### "Mobile app can't reach backend"
- **Problem:** Wrong URL configured
- **Solution:**
  - Check `.env` ServerPort matches app URL
  - For emulator: use `10.0.2.2` instead of `localhost`
  - For physical phone: use PC's local IP (e.g., `192.168.1.100`)
  - Test: `curl http://<SERVER_URL>:8000/health`

### "Port 8000 already in use"
- **Problem:** Another app using port 8000
- **Solution:**
  ```bash
  python -m server.main --port 9000
  # Update .env and app config to use port 9000
  ```

### "Out of memory / Slow performance"
- **Problem:** LLM model too large
- **Solution:**
  - Use smaller model: `ollama pull tinyllama`
  - Or increase RAM
  - Check: `ollama list` for available models

### "Flutter SDK not found"
- **Problem:** Flutter not in PATH
- **Solution:**
  1. Download Flutter
  2. Add to PATH
  3. Restart terminal
  4. Run `flutter doctor`

### "Dart/Flutter version mismatch"
- **Problem:** SDK version incompatible
- **Solution:**
  ```bash
  flutter upgrade
  flutter clean
  flutter pub get
  ```

### Permission errors in `data/` folders
- **Problem:** Can't write to data directories
- **Solution:**
  ```bash
  # Ensure data folder is writable
  # Windows: Right-click → Properties → Security → Edit Permissions
  # Mac/Linux: chmod -R 755 data/
  ```

---

## 📝 Development Workflow

### Hot Reload (Backend)

```bash
python -m server.main --reload     # Auto-restarts on file changes
```

### Hot Reload (Mobile)

Press `r` while app is running in terminal.

### Running Tests

```bash
# Backend tests
cd server
pytest

# Flutter tests
cd mobile/dione_app
flutter test
```

### Building for Production

**Backend (create executable):**
```bash
# Windows
pyinstaller --onefile server/main.py

# Result: dist/main.exe
```

**Mobile (create APK for Android):**
```bash
cd mobile/dione_app
flutter build apk --release

# Result: build/app/outputs/flutter-apk/app-release.apk
```

---

## 🚀 Production Deployment

For deploying to a server/VPS:

1. **Use Docker:**
   ```bash
   docker build -t dione .
   docker run -p 8000:8000 dione
   ```

2. **Use systemd (Linux):**
   Create `/etc/systemd/system/dione.service`
   ```ini
   [Unit]
   Description=Dione AI Server
   After=network.target

   [Service]
   User=dione
   WorkingDirectory=/opt/dione
   ExecStart=/opt/dione/.venv/bin/python -m server.main
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. **Use Reverse Proxy (Nginx):**
   ```nginx
   server {
       listen 80;
       server_name dione.example.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

---

## 📚 Project Structure Reference

```
PROJECT - I/
├── server/                    # Python backend
│   ├── main.py               # Entry point
│   ├── requirements.txt       # Dependencies
│   ├── api/                  # REST API routes
│   ├── core/                 # Engine core (ReAct loop)
│   ├── knowledge/            # Knowledge graph
│   ├── llm/                  # LLM adapters
│   ├── sentiment/            # Sentiment analysis
│   ├── plugins/              # Plugin system
│   └── config/               # Configuration
│
├── mobile/dione_app/         # Flutter app
│   ├── lib/
│   │   ├── main.dart         # App entry point
│   │   ├── screens/          # UI screens
│   │   ├── services/         # Backend communication
│   │   └── config/           # App config
│   └── pubspec.yaml          # Dependencies
│
├── data/                      # Runtime data (created by app)
│   ├── logs/
│   ├── knowledge/
│   ├── vectors/
│   ├── memories/
│   └── credentials/
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # System design
│   ├── SETUP.md              # This file
│   └── OPENCLAW_ANALYSIS.md
│
├── .env                       # Environment variables
├── .gitignore                # Git ignore rules
└── README.md                 # Project overview
```

---

## ✅ Checklist: Everything Working?

- [ ] Backend server running on `http://localhost:8000`
- [ ] API docs accessible at `http://localhost:8000/docs`
- [ ] LLM backend connected (check health endpoint)
- [ ] Mobile app connects to backend (no connection errors)
- [ ] Can send a message in mobile app and get response
- [ ] Data folders (`data/logs/`, etc.) are being written to
- [ ] `.env` file configured with your settings

---

## 🆘 Still Having Issues?

1. **Check logs:**
   ```bash
   # Server logs
   tail -f data/logs/dione_*.log
   
   # Mobile app logs
   flutter logs
   ```

2. **Verify network:**
   ```bash
   # Test backend is accessible
   curl -v http://localhost:8000/health
   
   # Test LLM
   curl http://localhost:11434/api/tags
   ```

3. **Restart everything:**
   ```bash
   # Kill all processes
   # Restart server, Ollama, app
   ```

---

## 📖 Additional Resources

- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Flutter Docs:** https://flutter.dev/docs
- **Ollama Models:** https://ollama.ai/library
- **PyTorch Installation:** https://pytorch.org/get-started/locally

---

**Happy coding! 🚀**

For questions or issues, open a GitHub issue: https://github.com/Jass-Shivnani/PROJECT---I/issues
