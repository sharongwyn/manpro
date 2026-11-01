@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" -m skripsi_search.web --root "%~dp0." --port 8765
) else (
  "C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe" -m skripsi_search.web --root "%~dp0." --port 8765
)
if errorlevel 1 (
  echo.
  echo Aplikasi belum berhasil dijalankan. Lihat README untuk pemasangan dependensi.
  pause
)