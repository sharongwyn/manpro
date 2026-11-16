@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" -m skripsi_search.web --root "%~dp0." --port 8765
) else if exist "%~dp0..\.venv\Scripts\python.exe" (
  "%~dp0..\.venv\Scripts\python.exe" -m skripsi_search.web --root "%~dp0." --port 8765
) else (
  python -m skripsi_search.web --root "%~dp0." --port 8765
)
if errorlevel 1 (
  echo.
  echo Aplikasi belum berhasil dijalankan. Lihat README untuk pemasangan dependensi.
  pause
)
