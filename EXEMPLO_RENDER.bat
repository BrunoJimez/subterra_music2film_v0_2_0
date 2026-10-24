@echo off
setlocal
cd /d "%~dp0"
echo Edite este arquivo e substitua CAMINHO_DA_MUSICA.wav.
".venv\Scripts\python.exe" subterra.py render "CAMINHO_DA_MUSICA.wav" "output\filme.mp4" --width 1920 --height 1080 --render-scale 0.75 --style reference_collage --filter auto --encoder auto
pause
