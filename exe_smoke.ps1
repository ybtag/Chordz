Set-Location 'C:\Users\ymber\Chordz'
& 'C:\Users\ymber\Chordz\dist\chordz.exe' examples\progression_test.wav *>&1 | Out-File 'C:\Users\ymber\Chordz\exe_smoke.log' -Encoding utf8
'DONE' | Set-Content 'C:\Users\ymber\Chordz\exe_smoke.done'
