param(
    [Parameter(Mandatory=$true)][string]$Vps,
    [string]$TargetDir = "/opt/safety-plus"
)

$ErrorActionPreference = "Stop"
$projectDir = $PSScriptRoot
$tempZip = Join-Path $env:TEMP "Safety_Plus_V36_18_33.zip"
$remoteZip = "/tmp/Safety_Plus_V36_18_33.zip"
$remoteDir = "/tmp/safetyplus_v36_18_32"

Write-Host "Safety Plus V36.18.36 - envio para VPS" -ForegroundColor Cyan
Write-Host "VPS: $Vps"

if (Test-Path $tempZip) { Remove-Item $tempZip -Force }

Write-Host "[1/3] Criando pacote sem .env, storage e backups..." -ForegroundColor Yellow
& tar.exe -a -c -f $tempZip --exclude=.env --exclude=storage --exclude=backups -C $projectDir .
if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o ZIP." }

Write-Host "[2/3] Enviando para a VPS..." -ForegroundColor Yellow
& scp $tempZip "${Vps}:$remoteZip"
if ($LASTEXITCODE -ne 0) { throw "Falha no SCP." }

Write-Host "[3/3] Atualizando o Safety Plus..." -ForegroundColor Yellow
$remote = @"
set -e
rm -rf $remoteDir
mkdir -p $remoteDir
unzip -q -o $remoteZip -d $remoteDir
cd $remoteDir
chmod +x ATUALIZAR_VPS.sh
sudo ./ATUALIZAR_VPS.sh $TargetDir
rm -f $remoteZip
"@
& ssh $Vps $remote
if ($LASTEXITCODE -ne 0) { throw "Falha durante a atualização remota." }

Write-Host "Concluído." -ForegroundColor Green
