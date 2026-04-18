@echo off
REM ================================================================
REM CyberAI Platform - first-run setup (Windows)
REM Run on a fresh git clone:  scripts\setup.bat
REM ================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0\.."
set ROOT=%cd%

echo ==========================================
echo  CyberAI Platform - First-run setup
echo  Project: %ROOT%
echo ==========================================

REM ---------- 1. .env file ----------
if not exist ".env" (
    echo [1/6] .env not found - copying from .env.example
    copy /Y .env.example .env >nul
    echo       OK .env created. Edit CLOUD_API_KEYS before going to production.
) else (
    echo [1/6] .env already exists - skipping
)

REM ---------- 2. Generate JWT_SECRET if still default ----------
findstr /C:"JWT_SECRET=change-me-in-production" .env >nul
if !errorlevel! == 0 (
    echo [2/6] Generating secure JWT_SECRET
    where python >nul 2>&1
    if !errorlevel! == 0 (
        for /f "delims=" %%i in ('python -c "import secrets; print(secrets.token_hex(32))"') do set NEW_SECRET=%%i
        powershell -Command "(Get-Content .env) -replace 'JWT_SECRET=change-me-in-production', 'JWT_SECRET=!NEW_SECRET!' | Set-Content .env"
        echo       OK JWT_SECRET set
    ) else (
        echo       ! python not found - leaving default JWT_SECRET ^(DEV ONLY^)
    )
) else (
    echo [2/6] JWT_SECRET already custom - skipping
)

REM ---------- 3. Create runtime folders ----------
echo [3/6] Creating runtime data folders
for %%d in (sessions uploads exports evidence assessments standards knowledge_base iso_documents vector_store translations models\huggingface) do (
    if not exist "data\%%d" mkdir "data\%%d"
)
if not exist "models\llm" mkdir "models\llm"
for %%d in (sessions uploads exports evidence assessments standards) do (
    if not exist "data\%%d\.gitkeep" type nul > "data\%%d\.gitkeep"
)
echo       OK Folders ready

REM ---------- 4. Check docker ----------
echo [4/6] Checking Docker availability
where docker >nul 2>&1
if !errorlevel! neq 0 (
    echo       FAIL Docker not installed. Install Docker Desktop from https://docs.docker.com/get-docker/
    exit /b 1
)
docker compose version >nul 2>&1
if !errorlevel! neq 0 (
    echo       FAIL Docker Compose v2 not available. Update Docker Desktop.
    exit /b 1
)
echo       OK Docker available

REM ---------- 5. Build & start ----------
echo [5/6] Building and starting containers ^(this may take 5-10 min on first run^)
docker compose up -d --build
if !errorlevel! neq 0 (
    echo       FAIL docker compose up failed
    exit /b 1
)

REM ---------- 6. Wait for health ----------
echo [6/6] Waiting for backend to become healthy...
set /a CNT=0
:wait_loop
set /a CNT+=1
if !CNT! gtr 60 goto :health_done
curl -fsS http://localhost:8000/health >nul 2>&1
if !errorlevel! == 0 (
    echo       OK Backend healthy after !CNT!0s
    goto :health_done
)
ping -n 11 127.0.0.1 >nul
goto :wait_loop
:health_done

echo.
echo ==========================================
echo  OK Setup complete!
echo ==========================================
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API docs:  http://localhost:8000/docs
echo   Ollama:    http://localhost:11434
echo   LocalAI:   http://localhost:8080
echo.
echo  Logs:    docker compose logs -f backend
echo  Status:  docker compose ps
echo  Stop:    docker compose down
echo ==========================================
echo.
echo  Note: Local models ^(Gemma 4 / Llama 3.1^) auto-download on first start.
echo        Gemma 4 ^(~9.6 GB^) takes ~10 min on broadband.
echo        Chatbot works immediately via cloud while models pull.
endlocal
