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
# llama.cpp server endpoints
COMPLETION_URL = "http://127.0.0.1:8080/completion"
CHAT_URL = "http://127.0.0.1:8080/v1/chat/completions"

REFERENCE_VOICE = "reference_big.wav"
OUTPUT_FILE = "rem_output.wav"
MEMORY_FILE = "memory.json"
MAX_HISTORY_LENGTH = 8  # Keep last 8 turns for fast context

# ----------------------------
# SYSTEM PROMPT (Rem personality)
# ----------------------------
combined_system = """You are Rem.
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
Rem: I'm okay... better now that you're here."""

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

# ----------------------------
# DEVICE & COQUI TTS LOADING
# ----------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

print("Loading Coqui XTTS v2 model...")
from TTS.api import TTS

if not os.path.exists(REFERENCE_VOICE):
    raise FileNotFoundError(f"Reference voice file '{REFERENCE_VOICE}' missing! Please ensure reference_big.wav is in the project directory.")

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=(device == "cuda"))
print("✅ Coqui XTTS v2 loaded successfully!")

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

    # Remove any leaked prompt tags
    reply = re.sub(r"^(Rem|Assistant|AI):\s*", "", reply, flags=re.IGNORECASE)
    reply = reply.encode("ascii", errors="ignore").decode()
    reply = re.sub(r"\s+", " ", reply)
    return reply.strip()

def generate_llm_reply(user_msg):
    """
    Generates response using llama.cpp /completion endpoint.
    This avoids slow reasoning loops that exhaust max_tokens on thinking models like Bonsai-27B.
    """
    # Build history prompt
    conversation_prompt = combined_system + "\n\n"
    for item in chat_history[-MAX_HISTORY_LENGTH:]:
        role = "User" if item["role"] == "user" else "Rem"
        conversation_prompt += f"{role}: {item['content']}\n"
    conversation_prompt += f"User: {user_msg}\nRem:"

    try:
        # 1. Primary: Fast direct prompt completion
        res = requests.post(
            COMPLETION_URL,
            json={
                "prompt": conversation_prompt,
                "n_predict": 60,
                "temperature": 0.7,
                "stop": ["\nUser:", "User:", "\n\n", "Rem:"]
            },
            timeout=30
        )
        if res.status_code == 200:
            content = res.json().get("content", "").strip()
            if content:
                return clean_reply(content)
    except Exception as e:
        print(f"Completion endpoint fallback triggered: {e}")

    # 2. Fallback: OpenAI-compatible chat endpoint with reasoning extraction
    try:
        messages = [{"role": "system", "content": combined_system}] + chat_history[-MAX_HISTORY_LENGTH:] + [{"role": "user", "content": user_msg}]
        res = requests.post(
            CHAT_URL,
            json={
                "messages": messages,
                "max_tokens": 120,
                "temperature": 0.7
            },
            timeout=45
        )
        if res.status_code == 200:
            msg = res.json()["choices"][0]["message"]
            content = msg.get("content", "").strip()
            if not content and "reasoning_content" in msg:
                # If content is empty because tokens were consumed in thinking, grab last thought sentence
                lines = [l.strip() for l in msg["reasoning_content"].splitlines() if l.strip()]
                content = lines[-1] if lines else "Hey... I am here."
            return clean_reply(content)
    except Exception as e:
        print(f"Chat endpoint error: {e}")

    return "Hey... I'm listening."

# ----------------------------
# MAIN LOOP
# ----------------------------
if device == "cuda":
    torch.cuda.empty_cache()

print("\n--- Waifu AI Voice Assistant (Coqui TTS + Bonsai-27B) Started ---")

while True:
    # 1. RECORD AND TRANSCRIBE
    user_input = record_and_transcribe()
    if not user_input or len(user_input.strip()) < 3:
        print("Ignored noise...")
        continue

    print("You:", user_input)

    # 2. GET LLM RESPONSE
    reply = generate_llm_reply(user_input)
    print("Rem:", reply)

    # 3. UPDATE HISTORY
    chat_history.append({"role": "user", "content": user_input})
    chat_history.append({"role": "assistant", "content": reply})

    # 4. GENERATE COQUI XTTS AUDIO
    clean_text = str(reply).strip().replace("\n", " ")

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
        print(f"Coqui TTS Generation Error: {e}")
        continue

    # Clear VRAM for next iteration
    if device == "cuda":
        torch.cuda.empty_cache()

    # 5. SAVE MEMORY
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(chat_history, f, indent=2)
    except Exception as e:
        print(f"Memory Save Error: {e}")
