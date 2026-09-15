import os
import re
import json
import asyncio
import requests
import sounddevice as sd
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
import soundfile as sf
import edge_tts

# ----------------------------
# SETTINGS
# ----------------------------
COMPLETION_URL = "http://127.0.0.1:8080/completion"
CHAT_URL = "http://127.0.0.1:8080/v1/chat/completions"

# RVC API endpoint (if running RVC WebUI or local RVC server)
RVC_API_URL = os.environ.get("RVC_API_URL", "http://127.0.0.1:7865/run/infer")

# Edge-TTS voice (en-US-AnaNeural is cute & clear, perfect base for anime waifu / RVC)
EDGE_VOICE = "en-US-AnaNeural"
OUTPUT_FILE = "rem_output.wav"
RAW_TTS_FILE = "edge_temp.wav"
MEMORY_FILE = "memory.json"
MAX_HISTORY_LENGTH = 8

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
# AUDIO PLAYBACK
# ----------------------------
def play_audio(filepath):
    try:
        data, fs = sf.read(filepath)
        sd.play(data, fs)
        sd.wait()
    except Exception as e:
        print(f"Playback error: {e}")

# ----------------------------
# LOAD WHISPER STT
# ----------------------------
print("Loading Whisper STT...")
stt_model = WhisperModel("small.en", device="cuda", compute_type="int8")
print("✅ Whisper STT ready!")

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
    return text if len(text) >= 2 else ""

def clean_reply(reply):
    reply = re.sub(r"^(Rem|Assistant|AI):\s*", "", reply, flags=re.IGNORECASE)
    reply = reply.encode("ascii", errors="ignore").decode()
    reply = re.sub(r"\s+", " ", reply)
    return reply.strip()

def generate_llm_reply(user_msg):
    conversation_prompt = combined_system + "\n\n"
    for item in chat_history[-MAX_HISTORY_LENGTH:]:
        role = "User" if item["role"] == "user" else "Rem"
        conversation_prompt += f"{role}: {item['content']}\n"
    conversation_prompt += f"User: {user_msg}\nRem:"

    try:
        res = requests.post(
            COMPLETION_URL,
            json={
                "prompt": conversation_prompt,
                "n_predict": 60,
                "temperature": 0.7,
                "stop": ["\nUser:", "User:", "\n\n", "Rem:"]
            },
            timeout=25
        )
        if res.status_code == 200:
            content = res.json().get("content", "").strip()
            if content:
                return clean_reply(content)
    except Exception:
        pass

    return "Hey... I'm right here with you."

# ----------------------------
# TTS + RVC PIPELINE
# ----------------------------
async def synthesize_speech(text):
    """
    1. Generates studio-clean speech via Edge-TTS (~0.5s).
    2. Passes audio through RVC (if RVC server is running) to apply Rem's exact vocal timbre.
    3. Saves final audio to rem_output.wav for Web UI lip-sync & local playback.
    """
    communicate = edge_tts.Communicate(text, EDGE_VOICE)
    await communicate.save(RAW_TTS_FILE)

    # Optional RVC conversion step
    rvc_applied = False
    try:
        if os.path.exists(RAW_TTS_FILE):
            # Check if local RVC WebUI API is running
            with open(RAW_TTS_FILE, "rb") as f:
                res = requests.post(
                    RVC_API_URL,
                    files={"audio": f},
                    timeout=5
                )
                if res.status_code == 200:
                    with open(OUTPUT_FILE, "wb") as out:
                        out.write(res.content)
                    rvc_applied = True
    except Exception:
        rvc_applied = False

    # If RVC not running or failed, use pristine Edge-TTS output
    if not rvc_applied:
        # Convert mp3/wav container cleanly to rem_output.wav
        data, fs = sf.read(RAW_TTS_FILE)
        sf.write(OUTPUT_FILE, data, fs)

# ----------------------------
# MAIN LOOP
# ----------------------------
print("\n--- Waifu AI Voice Assistant (Edge-TTS + RVC Ready) Started ---")

while True:
    # 1. Record & Transcribe
    user_input = record_and_transcribe()
    if not user_input or len(user_input.strip()) < 3:
        print("Ignored noise...")
        continue

    print("You:", user_input)

    # 2. LLM response
    reply = generate_llm_reply(user_input)
    print("Rem:", reply)

    chat_history.append({"role": "user", "content": user_input})
    chat_history.append({"role": "assistant", "content": reply})

    # 3. Fast Speech Synthesis (Edge-TTS + RVC)
    clean_text = str(reply).strip().replace("\n", " ")
    asyncio.run(synthesize_speech(clean_text))

    # 4. Play Audio (and trigger VRM lip sync via rem_output.wav)
    play_audio(OUTPUT_FILE)

    # 5. Save memory
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(chat_history, f, indent=2)
    except Exception:
        pass
