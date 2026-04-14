@echo off
echo [1/3] Installing dependencies...
pip install -r requirements.txt

echo [2/3] Packaging eurusd.exe...
pyinstaller --onefile ^
    --name eurusd ^
    --hidden-import=chromadb ^
    --hidden-import=sentence_transformers ^
    --collect-all=sentence_transformers ^
    --collect-all=chromadb ^
    src/backend.py

echo [3/3] Bundling assets...
xcopy /Y /I MarketShark.html dist\
xcopy /Y /I requirements.txt dist\
xcopy /Y /I data\* dist\data\ 2>nul
mkdir dist\src 2>nul
xcopy /Y /I src\*.py dist\src\

echo.
echo ✅ DONE: dist\eurusd.exe
echo 👉 Double-click to launch. Ollama must be running for LLM fallback.
pause
