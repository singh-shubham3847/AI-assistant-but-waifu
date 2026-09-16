# 💙 Rem AI Waifu — 3D Desktop AI Assistant

A local, private, and expressive 3D AI companion featuring a WebGL-based VRM avatar, GPU-accelerated Speech-to-Text, local LLM intelligence (with reasoning-model support), and a dual-stage **Edge-TTS + RVC v2.3** voice synthesis pipeline.

---

## ✨ Features

* 🎭 **3D VRM Avatar** (Three.js + `@pixiv/three-vrm`):
  * Supports VRM 1.0 and 0.X blendshapes.
  * Organic procedural animations: natural breathing, head tilts, eye darts, and idle states (shy, curious, listening).
  * Auto-driven procedural lip-sync with smoothed decay and dynamic mouth shapes (`aa`, `oh`, `ih`, `ou`, `ee`).
* 🧠 **Local LLM Intelligence (`llama.cpp`)**:
  * Compatible with any GGUF model (`llama-server.exe` on port `8080`).
  * Built-in support for **reasoning models** (Bonsai-27B, DeepSeek-R1) via automatic `<think>` bypass so responses remain fast and purely conversational.
  * Contextual multi-turn memory (`memory.json`).
* 🎤 **GPU-Accelerated Speech-to-Text**:
  * Powered by `faster-whisper` (`small.en` / `base.en`) on CUDA int8.
  * Voice Activity Detection (`vad_filter=True`) to filter out background noise.
* 🎙️ **Studio-Quality Voice Pipeline (Edge-TTS + RVC v2.3)**:
  * **Stage 1:** Crystal-clear speech generated in milliseconds via Microsoft Edge-TTS (`en-US-JennyNeural` / `en-US-AvaNeural`).
  * **Stage 2:** Real-time AI voice conversion via RVC v2.3 (`Rem.pth` + `Rem.index`) powered by `rmvpe` pitch extraction on GPU.
* 🌐 **Lightweight Web Interface**:
  * Zero-lag HTTP `HEAD` polling to avoid heavy network loops.
  * Interactive live status HUD (`Ready`, `Listening...`, `Speaking...`).
  * One-click audio unlock for strict browser autoplay policies.

---

## 🏗️ Architecture

```
[User Mic]
    │
    ▼ (PySoundDevice / 16kHz)
[faster-whisper GPU (CUDA int8 + VAD)]
    │
    ▼ (Transcribed Text)
[llama-server (Bonsai-27B / Mistral / Llama-3)]
    │  ↳ Bypasses <think> tags for natural dialogue
    ▼ (LLM Dialogue Response)
[Edge-TTS] ──> Fast intermediate speech (WAV)
    │
    ▼
[RVC v2.3 Bridge (Rem.pth + rmvpe on CUDA)]
    │
    ▼ (48kHz High-Fidelity Audio)
[rem_output.wav]
    ├──> Local Audio Output (PySoundDevice)
    └──> Web UI (Three.js VRM Lip Sync & Animations)
```

---

## 📁 Project Structure

```
AI-assistant-but-waifu/
│
├── main.py              # Main application loop (STT -> LLM -> TTS -> RVC -> Audio Playback)
├── rvc_bridge.py        # Independent bridge invoking RVC v2.3 runtime on GPU
├── index.html           # Web interface container for 3D avatar
├── script.js            # Three.js VRM loader, animation engine, and lip-sync handler
├── model.vrm            # 3D VRM avatar model
├── bg.jpg               # Background image for the web interface
├── memory.json          # Multi-turn chat history persistence
├── rem_output.wav       # Generated 48kHz audio output
└── README.md            # Documentation
```

---

## 🖥️ System Requirements

| Component | Minimum | Recommended | High Performance |
| :--- | :--- | :--- | :--- |
| **OS** | Windows 10 / 11 | Windows 10 / 11 (64-bit) | Windows 10 / 11 (64-bit) |
| **GPU** | NVIDIA GTX 1650 (4 GB) | NVIDIA RTX 3060 (12 GB) | NVIDIA RTX 4070+ (16+ GB) |
| **VRAM** | 4 GB | 8–12 GB | 16+ GB |
| **RAM** | 16 GB | 32 GB | 32+ GB |
| **Storage** | 10 GB SSD free | 25 GB NVMe SSD | 50+ GB NVMe SSD |
| **Python** | 3.10 or 3.11 | 3.11 (64-bit) | 3.11 (64-bit) |

---

## 🚀 Quick Start Guide

### 1️⃣ Clone the Repository & Install Dependencies

```bash
git clone https://github.com/singh-shubham3847/AI-assistant-but-waifu.git
cd AI-assistant-but-waifu
```

Install the required Python packages:

```bash
pip install faster-whisper edge-tts sounddevice scipy soundfile requests torch
```

> **Note for CUDA STT on Windows:**
> If `ctranslate2` cannot locate CUDA DLLs (`cublas64_12.dll`), `main.py` automatically registers your PyTorch CUDA directory:
> ```python
> import torch, os
> os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
> ```

---

### 2️⃣ Start Local LLM Server (`llama.cpp`)

Download a GGUF model (e.g. `Bonsai-27B-Q1_0.gguf`, `Mistral-7B-Instruct`, or `Llama-3-8B`) and run:

```powershell
.\llama-server.exe -m "path\to\your_model.gguf" -ngl 999 -c 8192 --host 127.0.0.1 --port 8080
```

Verify that the server is responding at:
```
http://127.0.0.1:8080/completion
```

---

### 3️⃣ Configure RVC (Voice Conversion)

1. Download or extract the standalone [RVC WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI/releases) package (e.g., `RVC20260718Nvidia`).
2. Place your target voice weights and index files into the RVC folders:
   - Voice model (`.pth`): `RVC.../assets/weights/Rem.pth`
   - Feature index (`.index`): `RVC.../logs/Rem.index`
3. In [`rvc_bridge.py`](rvc_bridge.py), confirm the `rvc_dir` path points to your RVC root:
   ```python
   rvc_dir = r"C:\path\to\RVC20260718Nvidia"
   ```

---

### 4️⃣ Launch the System

Open two terminal tabs:

**Terminal 1 — Python Assistant Backend:**
```powershell
python main.py
```

**Terminal 2 — 3D Avatar Web Server:**
```powershell
python -m http.server 8000
```

Open your browser to:
```
http://localhost:8000
```
*Click anywhere on the web page to unlock audio playback and initialize avatar interaction.*

---

## ⚙️ Configuration & Customization

### 🎙️ Changing the Base Voice (Edge-TTS)
In [`main.py`](main.py), you can customize the base TTS voice and tone:
```python
EDGE_VOICE = "en-US-JennyNeural"  # or "en-US-AvaNeural", "en-GB-SoniaNeural"
VOICE_RATE = "-4%"                # Speed adjustment
VOICE_PITCH = "-2Hz"              # Pitch adjustment
```

### 🗣️ Switching RVC Models
Pass any `.pth` model located in your RVC `assets/weights` folder into `synthesize_speech()` in [`main.py`](main.py):
```python
subprocess.run([sys.executable, "rvc_bridge.py", RAW_TTS_FILE, OUTPUT_FILE, "Rem.pth"], ...)
```
`rvc_bridge.py` will automatically resolve matching `.index` files in the `logs/` directory.

### 🎭 Replacing 3D Avatar & Background
- **Avatar:** Replace `model.vrm` with your own VRM 0.X or VRM 1.0 character file.
- **Background:** Replace `bg.jpg` with any image or wallpaper.

### 🧠 Tuning Personality & System Prompt
Edit `combined_system` in [`main.py`](main.py) to customize Rem's personality, conversation style, and response length.

---

## 🛠️ Troubleshooting

### ❓ Rem outputs "Hmm... I'm listening, tell me more." (Fallback Reply)
- Check that your `llama-server.exe` is running on port `8080`.
- If you are running a reasoning model (Bonsai, DeepSeek), ensure the prompt includes `<think>\n</think>` prefill (already configured in `main.py`).

### ❓ Audio repeating or stuttering in browser
- The browser polls `rem_output.wav` using HTTP `HEAD` requests. If the file timestamp updates, it plays once. If it loops, verify browser cache settings or ensure no other process is repeatedly modifying `rem_output.wav`.

### ❓ Microphone not picking up speech
- Ensure `input_mic.wav` is written to disk and has content.
- Check Windows microphone privacy settings to allow Python and terminal access.

---

## 📜 License & Credits

Distributed under the MIT License for experimental and personal use.

Special thanks to:
* [Three.js](https://threejs.org/) & [@pixiv/three-vrm](https://github.com/pixiv/three-vrm) for 3D avatar rendering.
* [llama.cpp](https://github.com/ggerganov/llama.cpp) for lightning-fast local LLM inference.
* [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for GPU-accelerated STT.
* [Edge-TTS](https://github.com/rany2/edge-tts) for high-speed speech synthesis.
* [RVC Project](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) for voice conversion.
