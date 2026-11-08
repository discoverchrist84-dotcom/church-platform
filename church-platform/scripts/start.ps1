# One-command start for development.   Run from the project folder:   .\scripts\start.ps1
# It applies any database changes, then starts the server and prints the phone address.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)   # project folder, wherever you launched from

python manage.py makemigrations
if ($LASTEXITCODE -ne 0) { Write-Host "makemigrations failed: copy the error above and send it to me." -ForegroundColor Red; exit 1 }
python manage.py migrate
if ($LASTEXITCODE -ne 0) { Write-Host "migrate failed: copy the error above and send it to me." -ForegroundColor Red; exit 1 }
python manage.py runlan
