@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python chưa được cài hoặc chưa có trong PATH.
  echo Cài Python 3.11+ từ https://www.python.org/downloads/windows/
  echo Nhớ tích chọn "Add python.exe to PATH".
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Đang tạo môi trường Python...
  py -3 -m venv .venv
  if errorlevel 1 (
    echo Không tạo được môi trường ảo. Hãy kiểm tra cài đặt Python.
    pause
    exit /b 1
  )
)
echo Đang cài thư viện...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Cài thư viện thất bại. Kiểm tra Internet rồi chạy lại.
  pause
  exit /b 1
)
echo.
echo Web sẽ chạy tại http://127.0.0.1:5000
echo Để dừng máy chủ, nhấn Ctrl+C.
start "" http://127.0.0.1:5000
".venv\Scripts\python.exe" app.py
pause
