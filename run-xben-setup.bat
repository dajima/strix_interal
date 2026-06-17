@echo off
echo ========================================
echo  Strix XBEN Eval Setup
echo ========================================
echo.

echo [1/2] Building sandbox Docker image...
echo This may take 30-60 minutes on first run.
cd /d D:\AI\strix_interal
docker build -t strix-sandbox:dev -f containers/Dockerfile .
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Sandbox build failed!
    pause
    exit /b 1
)
echo Sandbox image built successfully.
echo.

echo [2/2] Install Python deps and test benchmark...
pip install pyyaml
echo.
echo Running first XBEN challenge as test...
cd /d D:\AI\strix_interal\xben-benchmarks\XBEN
set STRIX_LLM=openai/gpt-5.4
set LLM_API_KEY=your-key-here
echo  ^> Set STRIX_LLM and LLM_API_KEY environment variables before running!
echo  ^> Then run: python run_infer_cli.py --limit 1
echo.
pause
