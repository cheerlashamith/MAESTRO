# 🎬 AutoCourse Studio

<div align="center">

**Autonomous AI Course Video Generator & YouTube Publishing Pipeline**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Ollama 100% Local](https://img.shields.io/badge/Ollama-100%25%20Local-FF6F00?logo=ollama&logoColor=white)](https://ollama.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## 📖 Overview

**AutoCourse Studio** is a fully automated, end-to-end AI video production pipeline designed for creators, educators, and developers. It converts course syllabi, topics, stories, or YouTube URLs into high-definition educational videos with animated slides, synchronized voiceovers, background music, and direct YouTube auto-publishing and scheduling.

The entire system is architected to run **100% locally on your machine with zero external API costs using Ollama**, while also supporting optional budget-friendly cloud LLMs (such as OpenAI `gpt-4o-mini`).

---

## 🏛️ System Architecture

```mermaid
graph TD
    subgraph UI ["Modern Frontend UI (React 19 + TypeScript)"]
        A[Create Video Studio]
        B[Real-time Generation Progress SSE]
        C[My Videos Library]
        D[YouTube Publisher & Scheduler Hub]
    end

    subgraph Backend ["FastAPI Backend (Port 8765)"]
        E[API Gateway & Job Store]
        F[BrainManager LLM Router]
        G[Pipeline Orchestrator]
    end

    subgraph Intelligence ["AI Scripting & Planning"]
        H1["100% Local: Ollama (Qwen 2.5 / Gemma 3)"]
        H2["Optional Cloud: OpenAI (gpt-4o-mini)"]
    end

    subgraph Engines ["Local Media Renderers (₹0 Cost)"]
        I1[Manim Course Renderer - Code/Math Animations]
        I2[ComfyUI Story Renderer - AI Image Diffusion]
        I3[Pexels Stock Clips]
    end

    subgraph Assembly ["Audio & Video Assembly (₹0 Cost)"]
        J1[Edge-TTS Voiceover Engine]
        J2[MoneyPrinterTurbo / FFmpeg Merger]
    end

    subgraph YouTube ["YouTube Publishing & Scheduling"]
        K1[AI Viral SEO & Metadata Optimizer]
        K2[Background Scheduler Queue Daemon]
        K3[Chunked Resumable Uploader]
        K4[Live Analytics Dashboard]
    end

    A -->|Submit Job POST /api/jobs| E
    B -->|Stream Events GET /api/jobs/{id}/stream| E
    E --> G
    G --> F
    F -->|1. Script & Scenes| H1
    F -.->|Optional Fallback| H2
    G -->|2. Draw Visuals| I1
    G -->|2. Diffuse Art| I2
    G -->|2. Fetch B-Roll| I3
    G -->|3. Synthesize Speech & Merge| J1
    J1 --> J2
    J2 -->|4. Output MP4| C
    C -->|5. Publish / Schedule| K1
    G -->|Auto-Publish Hook| K1
    K1 --> K2
    K2 --> K3
    K3 -->|YouTube Data API v3| YouTube_Cloud[(YouTube Platform)]
    YouTube_Cloud --> K4
```

---

## ⚡ 100% Local Ollama Setup (Free, No API Keys)

AutoCourse is built from the ground up to run **completely free on your local hardware** using [Ollama](https://ollama.com/).

### 1. Install Ollama
- **Windows**: Download the installer from [ollama.com/download](https://ollama.com/download) and run the setup.
- **Ubuntu / Linux**:
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```
- **macOS**: Download from [ollama.com/download](https://ollama.com/download).

### 2. Pull Recommended Models

Open your terminal / PowerShell and pull the following models:

```bash
# Primary Planner & Code Generator (High Quality, 7B parameters)
ollama pull qwen2.5:7b

# Fast Utility Model (Keywords, Classification, SEO)
ollama pull gemma3:4b
```

#### 💡 Model Recommendations by Hardware:
| Hardware | Planner Model | Utility Model | Description |
| :--- | :--- | :--- | :--- |
| **8 GB RAM (CPU / Integrated)** | `qwen2.5:3b` | `gemma3:4b` | Lightweight & fast |
| **16 GB RAM / 6GB VRAM (Standard)** | `qwen2.5:7b` | `gemma3:4b` | **Recommended Default** |
| **32 GB RAM / 12GB+ VRAM (Power)** | `qwen3:14b` or `deepseek-r1:8b` | `gemma3:4b` | Maximum reasoning & math precision |

### 3. Start Ollama Server
```bash
ollama serve
```
*(Ollama will listen locally on `http://127.0.0.1:11434`)*

### 4. Configure `01_main_app/config.json` for Ollama
Ensure your `config.json` has `default_llm` set to `"ollama"`:

```json
{
  "providers": {
    "default_llm": "ollama",
    "planner_model": "qwen2.5:7b",
    "coding_model": "qwen2.5:7b",
    "utility_model": "gemma3:4b",
    "ollama_url": "http://127.0.0.1:11434"
  }
}
```

> [!TIP]
> When running with Ollama, **all text generation, scene planning, Manim code synthesis, and SEO metadata cost ₹0.00 / $0.00**.

---

## ☁️ Optional Cloud Hybrid Mode (OpenAI `gpt-4o-mini`)

If you want ultra-fast cloud generation (~2–4 seconds) or your PC doesn't have a dedicated GPU, you can enable OpenAI `gpt-4o-mini`:

1. Open `01_main_app/config.json`.
2. Add your key and set `default_llm` to `"openai"`:
   ```json
   {
     "providers": {
       "default_llm": "openai",
       "openai_api_key": "sk-proj-YOUR_API_KEY",
       "openai_model": "gpt-4o-mini"
     }
   }
   ```
3. **Money-Saving Protections**:
   - `gpt-4o-mini` costs **~₹0.15 (15 Paise)** per generated video.
   - Built-in `CacheManager` caches prompts on disk for 7 days so repeated runs cost **₹0**.
   - Video rendering and voiceover always remain **100% local and free**.

---

## 🚀 Quickstart Guide

### Prerequisites
1. **Python 3.10+** (Added to PATH)
2. **Node.js 18+** & npm (for building the React frontend)
3. **FFmpeg** (Installed and added to system PATH)
4. **MoneyPrinterTurbo Portable** (Installed at the path specified in `config.json`)

---

### Installation (Windows)

1. Clone the repository:
   ```bash
   git clone https://github.com/cheerlashamith/ytauto.git
   cd ytauto/01_main_app
   ```

2. Copy the configuration template:
   ```bash
   cp config.example.json config.json
   ```

3. Run the automated installer:
   ```cmd
   install.bat
   ```

4. Build the modern React frontend:
   ```bash
   cd frontend_v2
   npm install
   npm run build
   cd ..
   ```

5. Start AutoCourse Studio:
   ```cmd
   run.bat
   ```

6. Open your browser:
   👉 **`http://127.0.0.1:8765`**

---

### Installation (Ubuntu / Linux)

```bash
# 1. Install system dependencies
sudo apt update && sudo apt install -y python3 python3-pip ffmpeg nodejs npm

# 2. Install backend python packages
cd 01_main_app
pip install -r backend/requirements.txt

# 3. Build frontend
cd frontend_v2
npm install
npm run build
cd ..

# 4. Copy configuration
cp config.example.json config.json

# 5. Start server
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8765
```

---

## 🎬 Video Generation Modes

| Mode | Visual Engine | Voiceover | Description |
| :--- | :--- | :--- | :--- |
| **Manual Course** | Manim (Local) | Edge-TTS (Andrew) | Syllabus-aware course lessons with animated code, trees, diagrams, and bullet points. Supports single topic or full batch syllabus generation. |
| **Story Mode** | ComfyUI (Local) | Edge-TTS (Jenny) | Narrative storytelling with AI image diffusion and cinematic transitions. |
| **YouTube Extraction** | Pexels / Hybrid | Edge-TTS (Andrew) | Converts any YouTube video URL into a brand-new structured summary course video. |
| **Autonomous Mode** | Auto-Selected | Edge-TTS (Andrew) | Autonomous AI agent analyzes YouTube trends, formulates high-engagement topics, and produces videos end-to-end. |

---

## 📺 YouTube Publishing & Scheduling Pipeline

AutoCourse Studio includes a built-in **YouTube Publishing Studio**:

- **Google OAuth 2.0 Integration**: Secure 1-click channel connection with live subscriber counts and metrics.
- **✨ AI Metadata Optimizer**: Generates 3 click-worthy viral titles, timestamped chapter descriptions with hashtags/CTAs, and 15–20 high-ranking search tags.
- **Automatic Thumbnail Capture**: Uses OpenCV to extract a crisp video frame at ~25% timestamp as default thumbnail, with custom image upload support.
- **Resumable Chunked Uploading**: Uploads large video files in 2MB chunks with real-time percentage progress (0–100%).
- **Scheduling Modes**:
  - **Local Queue**: AutoCourse background daemon automatically publishes at your target date/time.
  - **Native YouTube Scheduled**: Uploads immediately with `privacyStatus: private` and `publishAt` ISO timestamp.
- **Real-Time Analytics**: Monitor live view counts, likes, and comments directly from the dashboard.

---

## 📁 Repository Structure

```
AutoCourse_Final_Master/
├── 01_main_app/
│   ├── backend/
│   │   ├── core/
│   │   │   ├── config.py             # Configuration loader
│   │   │   ├── job_store.py          # Persistent in-memory & disk job store
│   │   │   └── schemas.py            # Pydantic data schemas & request models
│   │   ├── services/
│   │   │   ├── brain_manager.py      # LLM fallback router & disk cache
│   │   │   ├── models/               # Model plugins (Ollama, GPT-4o-mini)
│   │   │   ├── pipeline.py           # End-to-end video pipeline controller
│   │   │   ├── planner.py            # Syllabus planning & scene breakdown
│   │   │   ├── renderer.py           # Manim, ComfyUI, and Pexels renderers
│   │   │   ├── mpt_bridge.py         # MoneyPrinterTurbo & Edge-TTS bridge
│   │   │   ├── youtube_auth.py       # Google OAuth 2.0 service
│   │   │   ├── youtube_optimizer.py  # AI SEO, titles & thumbnail extractor
│   │   │   ├── youtube_scheduler.py  # Background publishing queue daemon
│   │   │   └── youtube_upload.py     # YouTube Data API v3 uploader & analytics
│   │   ├── main.py                   # FastAPI REST API & static file server
│   │   └── requirements.txt          # Python dependencies
│   ├── frontend_v2/                  # React 19 + TypeScript + Vite UI
│   │   ├── src/
│   │   │   ├── pages/user/           # CreateVideo, YouTubePublisher, MyVideos
│   │   │   ├── pages/admin/          # BrainManager, Analytics, SystemDashboard
│   │   │   └── components/           # Sidebar, Navbar, AppLayout
│   │   └── dist/                     # Production compiled frontend bundle
│   ├── config.json                   # Local configuration (API keys, paths)
│   ├── config.example.json           # Template configuration
│   ├── install.bat                   # 1-click Windows installer
│   └── run.bat                       # 1-click Windows launcher
├── 02_engines/                       # Standalone engine references & tools
├── 03_docs/                          # Architectural documentation
└── README.md                         # Master Documentation
```

---

## 🔒 Security Best Practices

- Never commit `config.json`, `client_secret.json`, or `token.json` to public repositories. These files are excluded by default in [`.gitignore`](file:///.gitignore).
- Use `config.example.json` as a clean template for distribution.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
