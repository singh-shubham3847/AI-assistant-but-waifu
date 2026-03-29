# 🧠 Rem AI Waifu (Local LLM + VRM Avatar + Voice)

A fully local AI waifu system featuring a 3D anime avatar, voice interaction, and a custom personality powered by a local LLM.

---

## ✨ Features

* 🎭 **3D VRM Character** (Web-based with Three.js)
* 🧠 **Local LLM (Mistral / llama.cpp API)**
* 🎤 **Speech-to-Text (STT)** input
* 🔊 **Text-to-Speech (TTS)** output
* 💋 **Lip Sync (auto-driven)**
* 👀 **Idle Animations**

  * Breathing
  * Head movement
  * Looking around
  * Shy behavior
* 🎨 **Custom Background Support**
* ⚡ Fully **offline / local**

---

## 🖥️ Minimum System Requirements

### ⚙️ Bare Minimum (Will Run, Not Smooth)

* **CPU:** 4 cores (e.g. Intel i5 8th gen / Ryzen 3)
* **RAM:** 8 GB
* **GPU:** Integrated graphics (Intel UHD / Vega)
* **Storage:** ~5–10 GB free
* **OS:** Windows / Linux
* **Browser:** Chrome / Edge (WebGL required)

👉 Expect:

* Slow LLM responses
* Slight lag in avatar
* Lower FPS

---

### 🚀 Recommended (Smooth Experience)

* **CPU:** 6–8 cores (e.g. Intel i5 12th gen / Ryzen 5)
* **RAM:** 12–16 GB
* **GPU:** Dedicated GPU (RTX 2050 or better)
* **Storage:** SSD (important for model loading)
* **VRAM:** 4 GB+ (if using GPU acceleration)

👉 Expect:

* Fast responses
* Smooth animations
* Better TTS quality

---

### 🔥 Ideal (Best Experience)

* **CPU:** 8+ cores (i7 / Ryzen 7)
* **RAM:** 16–32 GB
* **GPU:** RTX 3060+
* **VRAM:** 6–12 GB
* **Storage:** NVMe SSD

👉 Enables:

* Larger LLM models
* Real-time interaction
* Advanced features (future upgrades)

---

## 🏗️ Project Structure

```
project/
│
├── main.py              # Python backend (LLM + STT + TTS)
├── index.html          # Web frontend
├── script.js           # 3D avatar + animations
├── model.vrm           # VRM character
├── bg.jpg              # Background image
├── rem_output.wav      # Generated voice output
```

---

## 🚀 Setup Guide

### 1️⃣ Install Python dependencies

```bash
pip install requests sounddevice whisper TTS
```

*(Adjust based on your setup)*

---

### 2️⃣ Run Local LLM Server

Using llama.cpp:

```bash
llama-server --model mistral.gguf --port 8080
```

Make sure this works:

```
http://localhost:8080/v1/chat/completions
```

---

### 3️⃣ Run Backend

```bash
python main.py
```

---

### 4️⃣ Run Frontend

Use a simple server:

```bash
python -m http.server 8000
```

Open:

```
http://localhost:8000
```

---

## 🧠 System Prompt

The AI uses a custom personality:

* Short replies (1–2 sentences)
* Natural, casual tone
* Not an assistant
* Slightly emotional / human-like

---

## 💋 Lip Sync System

* Detects when new audio (`rem_output.wav`) is generated
* Simulates natural mouth movement using:

  * Sine waves
  * Random variation
* Uses VRM `expressionManager.mouthExpressionNames`

---

## 🎭 Animations

### Idle Behavior:

* Subtle breathing (no floating)
* Head movement
* Random idle states:

  * Normal
  * Looking around
  * Shy

### Talking:

* Dynamic mouth movement
* Auto stops after speech

---

## ⚠️ Common Issues

### ❌ No lip sync

* Ensure VRM has mouth blendshapes
* Check console:

  ```js
  currentVrm.expressionManager.mouthExpressionNames
  ```

---

### ❌ Audio repeating

* Fixed via file change detection (size-based)

---

### ❌ STT hears TTS

* Add delay / speaking lock in Python

---

### ❌ LLM errors

* Ensure correct endpoint:

  ```
  http://localhost:8080/v1/chat/completions
  ```

---

## 🔧 Customization

### Change character

Replace:

```
model.vrm
```

---

### Change background

Replace:

```
bg.jpg
```

---

### Adjust lip sync strength

In `script.js`:

```js
mouth = Math.pow(mouth, 0.7) * 2.5;
```

---

## 🧪 Future Improvements

* 🎤 Real audio-driven lip sync
* 👀 Eye tracking (cursor follow)
* 😊 Emotion system (happy/sad)
* 🧠 Memory system
* 🗣️ Wake word detection

---

## 📜 License

For personal / experimental use.

---

## 💬 Credits

* Three.js
* three-vrm
* llama.cpp
* Coqui TTS / Whisper

---

## 😏 Final Note

This project is meant to feel alive — not just functional.

Tweak animations, voice, and personality to make her truly yours.
