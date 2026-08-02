@echo off
REM Build the light Chordz Windows exe (librosa + HMM + player, ~150-200 MB).
REM Produces dist\chordz.exe. All permissive licenses (ISC/BSD/MIT).
REM For the optional heavy build (+ Demucs/torch for --separate), see README.
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name chordz ^
  --icon data\chordz.ico ^
  --add-data "data\chordz.ico;data" ^
  --splash data\chordz_splash.png ^
  --collect-all chordz ^
  --collect-all librosa ^
  --collect-all soundfile ^
  --collect-all just_playback ^
  --collect-all numpy ^
  --collect-all scipy ^
  --exclude-module torch ^
  --exclude-module torchaudio ^
  --exclude-module torchvision ^
  --exclude-module demucs ^
  chordz\__main__.py
