# Atualiza o kit WE no Windows: baixa a versao nova e roda o instalador de novo
# (ele pula o que ja existe e instala o que for novo).
# Uso: dois cliques em atualizar.cmd, ou no PowerShell, na pasta do kit:
#   powershell -ExecutionPolicy Bypass -File .\atualizar.ps1
#   opcoes: -SoBaixar (so git pull, sem rodar o instalador) + as mesmas do instalar.ps1
param([switch]$SoBaixar, [switch]$SemApplio, [switch]$SemWhisperLarge)
$ErrorActionPreference = "Stop"
$KIT = $PSScriptRoot
Set-Location $KIT

function Git-Out { $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"; $o = & git @args 2>&1; $c = $LASTEXITCODE; $ErrorActionPreference = $old; return @($o, $c) }

Write-Host "== Atualizando o kit em $KIT ==" -ForegroundColor Cyan

$sujo = git status --porcelain --untracked-files=no
if ($sujo) {
  Write-Host "Arquivos do kit foram alterados nesta maquina:" -ForegroundColor Yellow
  $sujo | ForEach-Object { Write-Host "   $_" }
  Write-Host "Nada foi atualizado. Mande essa lista para o agente (ou rode 'git stash') e tente de novo." -ForegroundColor Yellow
  exit 1
}

if ((Get-Command gh -ErrorAction SilentlyContinue)) {
  $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  gh auth status *> $null
  if ($LASTEXITCODE -eq 0) { gh auth setup-git *> $null }
  $ErrorActionPreference = $old
}

$antes = (git rev-parse HEAD).Trim()
$r = Git-Out pull --ff-only
$r[0] | ForEach-Object { Write-Host "   $_" }
if ($r[1] -ne 0) { throw "git pull falhou (veja acima). Se pedir login, rode 'gh auth login' e tente de novo." }
$depois = (git rev-parse HEAD).Trim()

if ($antes -eq $depois) {
  Write-Host "Ja estava na versao mais nova." -ForegroundColor Green
} else {
  Write-Host ""
  Write-Host "Novidades:" -ForegroundColor Cyan
  git log --pretty=format:"   %ad  %s" --date=short "$antes..$depois"
  Write-Host ""
}

if ($SoBaixar) { Write-Host "Pronto (-SoBaixar: instalador nao rodou)."; exit 0 }

Write-Host ""
Write-Host "== Conferindo dependencias (instalar.ps1) ==" -ForegroundColor Cyan
$args2 = @("-ExecutionPolicy", "Bypass", "-File", (Join-Path $KIT "instalar.ps1"))
if ($SemApplio) { $args2 += "-SemApplio" }
if ($SemWhisperLarge) { $args2 += "-SemWhisperLarge" }
& powershell @args2
if ($LASTEXITCODE -ne 0) { throw "instalar.ps1 terminou com erro (veja acima)." }

Write-Host ""
Write-Host "Atualizado. Abra um chat NOVO no Cursor para as skills novas valerem." -ForegroundColor Green
