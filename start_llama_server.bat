@echo off
REM Script to start the llama.cpp server for Rem AI Waifu

SET MODEL_PATH=C:\Users\Shubham Singh\llama.cpp\models\Mistral-7B-Instruct-v0.3.Q4_K_S.gguf

IF NOT EXIST "%MODEL_PATH%" (
    echo [WARNING] Model file not found at: "%MODEL_PATH%"
    echo Please update the MODEL_PATH variable in start_llama_server.bat to point to your .gguf model file.
    pause
    exit /b 1
)

cd /d "C:\Users\Shubham Singh\llama.cpp\build\bin\release" 2>nul || cd /d "C:\Users\Shubham\llama.cpp\build\bin\release" 2>nul || (
    echo [ERROR] Could not find llama.cpp build directory.
    pause
    exit /b 1
)

echo Starting llama-server on port 8080...
.\llama-server.exe -m "%MODEL_PATH%" -ngl 999 -c 8192 --port 8080
