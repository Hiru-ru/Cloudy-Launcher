@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === 云朵启动器 v1.2.12.16 打包 ===
pyinstaller --noconfirm --clean build.spec
if errorlevel 1 (
    echo 打包失败，请检查上方错误信息。
    pause
    exit /b 1
)
echo 打包完成，输出位于 dist\云朵启动器.exe
pause
