@echo off
REM Script to start the llama.cpp server for Bonsai-27B-Q1_0 model

SET BIN_DIR=.\bin\cuda
SET MODEL_PATH=.\models\gguf\27B\Bonsai-27B-Q1_0.gguf

IF NOT EXIST "%BIN_DIR%\llama-server.exe" (
    REM Fallback to standard locations if not found relative to script
    IF EXIST "C:\Users\Shubham\llama.cpp\bin\cuda\llama-server.exe" (
        cd /d "C:\Users\Shubham\llama.cpp"
    ) ELSE IF EXIST "C:\Users\Shubham Singh\llama.cpp\bin\cuda\llama-server.exe" (
        cd /d "C:\Users\Shubham Singh\llama.cpp"
    )
)

echo ============================================================
echo Starting llama-server with Bonsai-27B (Q1_0) on port 8080...
echo ============================================================

.\bin\cuda\llama-server.exe -m "%MODEL_PATH%" -ngl 999 -c 8192 --host 127.0.0.1 --port 8080
pause
