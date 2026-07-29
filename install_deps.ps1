$ErrorActionPreference = 'Continue'
$py = 'C:\Users\ymber\Chordz\.venv\Scripts\python.exe'
$maxAttempts = 10
$ok = $false
for ($i = 1; $i -le $maxAttempts -and -not $ok; $i++) {
    "Attempt $i of $maxAttempts..." | Out-File 'C:\Users\ymber\Chordz\install.log' -Encoding utf8
    & $py -m pip install --retries 10 --timeout 30 librosa numpy scipy pytest *>&1 | Out-File 'C:\Users\ymber\Chordz\install.log' -Append -Encoding utf8
    & $py -c "import librosa, numpy, scipy, pytest" 2>$null
    if ($LASTEXITCODE -eq 0) { $ok = $true; "SUCCESS on attempt $i" | Out-File 'C:\Users\ymber\Chordz\install.log' -Append -Encoding utf8 }
}
if ($ok) { "DONE-OK" | Set-Content 'C:\Users\ymber\Chordz\install.done' } else { "DONE-FAILED" | Set-Content 'C:\Users\ymber\Chordz\install.done' }
