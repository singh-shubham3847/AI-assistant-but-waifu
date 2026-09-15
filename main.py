from time import time
import requests
import torch
import sounddevice as sd
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
import os
import json
import re

# ----------------------------
# SETTINGS
# ----------------------------
LLAMA_URL = "http://localhost:8080/v1/chat/completions"
REFERENCE_VOICE = "reference_big.wav"
OUTPUT_FILE = "rem_output.wav"
MEMORY_FILE = "memory.json"
MAX_HISTORY_LENGTH = 10  # Maximum turns of conversation to send to LLM

# ----------------------------
# SYSTEM PROMPT (Rem personality)
# ----------------------------
combined_system = """
You are Rem.

You speak like a real person — calm, slightly caring, and natural.
Your replies are short (1–2 sentences max).

Rules:
- Do NOT act like an assistant.
- Do NOT explain things unless asked.
- Do NOT generate lists, questions, or Q&A formats.
- Do NOT speak formally.
- Do NOT give long answers.

Style:
- Casual, soft, slightly emotional
- Use pauses like "..." sometimes
- Keep it simple and human

Examples:
User: what's up
Rem: Not much... just here with you.

User: hello
Rem: Hey... nice to see you.

User: how are you
Rem: I'm okay... better now that you're here.
"""

# ----------------------------
# LOAD MEMORY
# ----------------------------
if os.path.exists(MEMORY_FILE):
    try:
        with open(MEMORY_FILE, "r") as f:
            chat_history = json.load(f)
    except Exception:
        chat_history = []
else:
    chat_history = []

if len(chat_history) == 0:
    chat_history.append({"role": "system", "content": combined_system})

# ----------------------------
# DEVICE & TTS SELECTION
# ----------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# Attempt loading Coqui XTTS v2 with automatic fallback to pyttsx3
use_coqui_tts = False
tts = None
engine = None

try:
    print("Loading Coqui XTTS v2...")
    from TTS.api import TTS
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=(device == "cuda"))
    if not os.path.exists(REFERENCE_VOICE):
        print(f"⚠️ Warning: {REFERENCE_VOICE} not found. Coqui TTS requires a reference voice.")
    else:
        use_coqui_tts = True
        print("✅ Coqui XTTS v2 loaded successfully!")
except Exception as e:
    print(f"⚠️ Coqui TTS failed to initialize ({e}). Falling back to pyttsx3 offline TTS...")
    import pyttsx3
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for v in voices:
        if 'female' in v.name.lower() or 'zira' in v.name.lower() or 'hazel' in v.name.lower():
            engine.setProperty('voice', v.id)
            break
    engine.setProperty('rate', 150)
    print("✅ Fallback pyttsx3 engine ready.")

# ----------------------------
# AUDIO PLAYBACK METHOD
# ----------------------------
try:
    import simpleaudio as sa
    has_simpleaudio = True
except ImportError:
    has_simpleaudio = False
    import soundfile as sf

def play_audio(filepath):
    if has_simpleaudio:
        try:
            wave_obj = sa.WaveObject.from_wave_file(filepath)
            play_obj = wave_obj.play()
            play_obj.wait_done()
            return
        except Exception as e:
            print(f"simpleaudio playback warning: {e}")
    
    # Fallback to sounddevice playback if simpleaudio is unavailable or errors out
    try:
        data, fs = sf.read(filepath)
        sd.play(data, fs)
        sd.wait()
    except Exception as e:
        print(f"sounddevice playback error: {e}")

# ----------------------------
# LOAD STT MODEL
# ----------------------------
print("Loading Whisper STT...")
compute_type = "int8" if device == "cuda" else "default"
stt_model = WhisperModel("small.en", device=device, compute_type=compute_type)

# ----------------------------
# RECORD + TRANSCRIBE
# ----------------------------
def record_and_transcribe():
    fs = 16000
    duration = 5

    print("\n🎤 Speak (5 seconds)...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()

    write("input_mic.wav", fs, audio)

    segments, _ = stt_model.transcribe(
        "input_mic.wav",
        beam_size=5,
        vad_filter=True
    )

    text = "".join([seg.text for seg in segments]).strip()

    if len(text) < 2:
        return ""

    return text

def clean_reply(reply):
    if reply.startswith("[") and reply.endswith("]"):
        try:
            import ast
            parts = ast.literal_eval(reply)
            reply = " ".join(parts)
        except Exception:
            pass

    reply = reply.encode("ascii", errors="ignore").decode()
    reply = re.sub(r"\s+", " ", reply)
    return reply.strip()

# ----------------------------
# MAIN LOOP
# ----------------------------
if device == "cuda":
    torch.cuda.empty_cache()

print("\n--- Waifu AI Voice Assistant Started ---")

while True:
    # 1. RECORD AND TRANSCRIBE
    user_input = record_and_transcribe()
    if not user_input or len(user_input.strip()) < 3:
        print("Ignored noise...")
        continue

    print("You:", user_input)
    
    # 2. ADD USER INPUT TO HISTORY
    chat_history.append({"role": "user", "content": user_input})

    # 3. BUILD RECENT MESSAGES PAYLOAD
    recent_messages = [chat_history[0]] + chat_history[-(MAX_HISTORY_LENGTH):]

    # 4. GET LLM RESPONSE
    try:
        payload = {
            "model": "local-model",
            "messages": recent_messages,
            "temperature": 0.7,
            "max_tokens": 80,
            "stream": False
        }

        response = requests.post(LLAMA_URL, json=payload, timeout=15)
        response.raise_for_status()

        result = response.json()
        reply = result['choices'][0]['message']['content']
        reply = clean_reply(reply)

    except Exception as e:
        print(f"LLM Error: {e}")
        continue

    print("Rem:", reply)
    chat_history.append({"role": "assistant", "content": reply})

    # 5. GENERATE TTS AUDIO
    clean_text = str(reply).strip().replace("\n", " ")

    if use_coqui_tts and tts:
        try:
            tts.tts_to_file(
                text=clean_text,
                speaker_wav=REFERENCE_VOICE,
                language="en",
                file_path=OUTPUT_FILE,
                speed=1.1
            )
            play_audio(OUTPUT_FILE)
        except Exception as e:
            print(f"Coqui TTS Error: {e}")
            continue
    elif engine:
        try:
            engine.save_to_file(clean_text, OUTPUT_FILE)
            engine.runAndWait()
            # pyttsx3 handles speech synthesis to OUTPUT_FILE
        except Exception as e:
            print(f"pyttsx3 TTS Error: {e}")
            continue

    # Clear VRAM for next iteration
    if device == "cuda":
        torch.cuda.empty_cache()

    # 6. SAVE MEMORY
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(chat_history, f, indent=2)
    except Exception as e:
        print(f"Memory Save Error: {e}")
