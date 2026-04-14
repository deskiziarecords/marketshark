@echo off
echo Installing dependencies...
pip install -r requirements.txt

echo Building eurusd.exe...
pyinstaller --onefile ^
    --name eurusd ^
    --hidden-import=chromadb ^
    --hidden-import=sentence_transformers ^
    --collect-all=sentence_transformers ^
    backend.py

echo Copying assets...
copy pattern_db_eurusd.json dist\ 2>nul
copy eurusd_1min_tokenized.csv dist\
copy MarketShark_Local.html dist\index.html
mkdir dist\chroma_db 2>nul
mkdir dist\models 2>nul

echo.
echo ✅ Built eurusd.exe in /dist
echo.
echo To run:
echo   1. Start Ollama: ollama run llama3.2:1b
echo   2. Run: dist\eurusd.exe
echo   3. Open: dist\index.html in browser
echo.
pause
