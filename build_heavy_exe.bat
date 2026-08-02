@echo off
REM Build the offline Demucs edition. The htdemucs model must be staged first.
REM Produces dist\chordz-heavy.exe; this is substantially larger than chordz.exe.
if not exist build\demucs_models\955717e8-8726e21a.th (
  echo Missing build\demucs_models\955717e8-8726e21a.th
  exit /b 1
)
if not exist build\demucs_models\htdemucs.yaml (
  echo Missing build\demucs_models\htdemucs.yaml
  exit /b 1
)
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name chordz-heavy ^
  --icon data\chordz.ico ^
  --add-data "data\chordz.ico;data" ^
  --add-data "build\demucs_models;demucs_models" ^
  --runtime-hook chordz\demucs_runtime_hook.py ^
  --splash data\chordz_splash.png ^
  --collect-all chordz ^
  --collect-all librosa ^
  --collect-all soundfile ^
  --collect-all just_playback ^
  --collect-all numpy ^
  --collect-all scipy ^
  --collect-all demucs ^
  --collect-all sphn ^
  --collect-all julius ^
  --collect-all safetensors ^
  --collect-all huggingface_hub ^
  chordz\__main__.py
