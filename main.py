from time import time

import requests
import torch
from TTS.api import TTS
import simpleaudio as sa
import sounddevice as sd
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
import os
import json

# ----------------------------
# SETTINGS
# ----------------------------
LLAMA_URL = "http://localhost:8080/v1/chat/completions"
REFERENCE_VOICE = "reference_big.wav"
OUTPUT_FILE = "rem_output.wav"
MEMORY_FILE = "memory.json"

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
    except:
        chat_history = []
else:
    chat_history = []

if len(chat_history) == 0:
    chat_history.append({"role": "system", "content": combined_system})

# ----------------------------
# DEVICE
# ----------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# ----------------------------
# LOAD MODELS
# ----------------------------
print("Loading XTTS...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)


print("Loading Whisper STT...")
stt_model = WhisperModel("small.en", device="cuda", compute_type="float16")

# ----------------------------
# RECORD + TRANSCRIBE
# ----------------------------
def record_and_transcribe():
    fs = 16000
    duration = 5

    print("🎤 Speak...")
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

import re

def clean_reply(reply):
    # convert list-like string → normal sentence
    if reply.startswith("[") and reply.endswith("]"):
        try:
            import ast
            parts = ast.literal_eval(reply)
            reply = " ".join(parts)
        except:
            pass

    # remove weird unicode junk
    reply = reply.encode("ascii", errors="ignore").decode()

    # remove extra spaces
    reply = re.sub(r"\s+", " ", reply)

    return reply.strip()


# ----------------------------
# MAIN LOOP
# ----------------------------
# Clear CUDA cache to prevent OOM (Out of Memory) errors
if device == "cuda":
    torch.cuda.empty_cache()

while True:
    # 2. RECORD AND TRANSCRIBE
    user_input = record_and_transcribe()
    if not user_input or len(user_input.strip()) < 3:
        print("Ignored noise...")
        continue


    print("You:", user_input)
    
    # 3. BUILD CLEAN HISTORY (Fixes the 500 error)
    # Combine system prompts into one string
    
    # Add new user input to history
    chat_history.append({"role": "user", "content": user_input})

    # 4. GET LLM RESPONSE
    try:
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": combined_system},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.7,
            "max_tokens": 80,
            "stream": False
        }

        response = requests.post(LLAMA_URL, json=payload)
        print("RAW RESPONSE:", response.text)


        response.raise_for_status()

        result = response.json()
        reply = result['choices'][0]['message']['content']
        reply = clean_reply(reply)


    except Exception as e:
        print(f"LLM Error: {e}")
        continue

    print("Rem:", reply)
    chat_history.append({"role": "assistant", "content": reply})

    clean_text = str(reply).strip().replace("\n", " ")

    try:
        tts.tts_to_file(
            text=clean_text,
            speaker_wav=REFERENCE_VOICE,
            language="en",
            file_path=OUTPUT_FILE,
            speed = 1.1
        )
    except Exception as e:
        print(f"TTS Error: {e}")
        continue

    #6. LOCAL PLAYBACK
    wave_obj = sa.WaveObject.from_wave_file(OUTPUT_FILE)
    play_obj = wave_obj.play()
    play_obj.wait_done()
    

    # Clear VRAM for the next turn on your LOQ
    torch.cuda.empty_cache()

    # ----------------------------
    # SAVE MEMORY
    # ----------------------------

    with open(MEMORY_FILE, "w") as f:
        json.dump(chat_history, f, indent=2)
