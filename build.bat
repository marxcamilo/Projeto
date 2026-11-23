@echo off
REM =====================================================================
REM build.bat — Gera Schulz_Calibracao.exe
REM Projeto Aplicado I — AV04 | Schulz S.A.
REM =====================================================================
setlocal

echo ============================================
echo  BUILD — Schulz Calibracao
echo ============================================
echo.

REM --- 1. Verifica Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH.
    echo Instale o Python 3.10+ e marque "Add to PATH".
    pause
    exit /b 1
)

REM --- 2. Ambiente virtual ---
if not exist ".venv" (
    echo [1/5] Criando ambiente virtual...
    python -m venv .venv
) else (
    echo [1/5] Ambiente virtual ja existe.
)
call .venv\Scripts\activate.bat

REM --- 3. Dependencias ---
echo [2/5] Instalando dependencias...
python -m pip install --upgrade pip --quiet
python -m pip install openpyxl pyinstaller --quiet
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)

REM --- 4. Limpa builds anteriores ---
echo [3/5] Limpando builds anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "Schulz_Calibracao.spec" del /q "Schulz_Calibracao.spec"

REM --- 5. PyInstaller ---
echo [4/5] Compilando executavel...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name Schulz_Calibracao ^
    --add-data "03_banco.sql;." ^
    --add-data "04_classes.py;." ^
    --hidden-import openpyxl ^
    --hidden-import openpyxl.cell._writer ^
    --collect-submodules openpyxl ^
    --clean ^
    --noconfirm ^
    07_gerador_certificado.py

if errorlevel 1 (
    echo [ERRO] Falha na compilacao.
    pause
    exit /b 1
)

REM --- 6. Empacota a pasta de distribuicao ---
echo [5/5] Montando pasta de distribuicao...
if not exist "dist\Schulz_Calibracao" mkdir "dist\Schulz_Calibracao"
copy /y "dist\Schulz_Calibracao.exe" "dist\Schulz_Calibracao\" >nul
copy /y "03_banco.sql" "dist\Schulz_Calibracao\" >nul
copy /y "LEIA-ME.txt" "dist\Schulz_Calibracao\" >nul 2>&1

echo.
echo ============================================
echo  BUILD CONCLUIDO
echo ============================================
echo  Executavel : dist\Schulz_Calibracao.exe
echo  Pacote     : dist\Schulz_Calibracao\
echo.
echo  Teste: dist\Schulz_Calibracao\Schulz_Calibracao.exe
echo ============================================
pause
