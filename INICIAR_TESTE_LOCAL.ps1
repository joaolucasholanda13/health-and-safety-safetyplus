$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "Safety Plus - iniciando teste local..." -ForegroundColor Cyan
& "$PSScriptRoot\INICIAR_TESTE_LOCAL.bat"
