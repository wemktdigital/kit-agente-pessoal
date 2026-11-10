# Instala o kit WE (HyperFrames + pipeline reels-we) no Windows.
# Uso (PowerShell, na pasta do kit):
#   powershell -ExecutionPolicy Bypass -File .\instalar.ps1
#   opcoes: -SemApplio (sem dublagem EN/ES)  -SemWhisperLarge (pula o modelo de 3 GB)
param([switch]$SemApplio, [switch]$SemWhisperLarge)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$KIT = $PSScriptRoot
$TOOLS = Join-Path $HOME "tools"
$DOCS = [Environment]::GetFolderPath("MyDocuments")
$APPLIO = Join-Path $TOOLS "Applio"
$APPLIO_COMMIT = "c817f1f"
$WHISPER_DIR = Join-Path $HOME "models\whisper"
$REPO_KIT = "wemktdigital/kit-agente-pessoal"

function Passo($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Ok($t) { Write-Host "ok   $t" -ForegroundColor Green }
function Aviso($t) { Write-Host "AVISO $t" -ForegroundColor Yellow }
function Recarrega-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
function Tem($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Garante($cmd, $id) {
  if (Tem $cmd) { Ok "$cmd"; return }
  Write-Host "     instalando $id ..."
  winget install --id $id -e --accept-source-agreements --accept-package-agreements --silent | Out-Host
  Recarrega-Path
  if (-not (Tem $cmd)) { throw "$cmd nao ficou disponivel. Feche e abra o PowerShell e rode de novo." }
  Ok "$cmd"
}
function Garante-Gh {
  $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  gh auth status *> $null; $logado = ($LASTEXITCODE -eq 0)
  $ErrorActionPreference = $old
  if (-not $logado) { gh auth login }
}
function Liga($link, $alvo) {
  if (Test-Path $link) {
    $item = Get-Item $link -Force
    if ($item.LinkType -and ($item.Target -contains $alvo)) { Ok "$link (ja ligado)"; return }
    $bk = "$link-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss")
    Move-Item $link $bk
    Write-Host "     backup -> $bk"
  }
  New-Item -ItemType Directory -Force -Path (Split-Path $link) | Out-Null
  New-Item -ItemType Junction -Path $link -Target $alvo | Out-Null
  Ok "$link -> $alvo"
}
function Baixa($url, $dest) {
  if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 1MB)) { Ok "$dest (ja existe)"; return }
  New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
  curl.exe -L --fail -C - -o $dest $url
  if ($LASTEXITCODE -ne 0) { throw "download falhou: $url" }
  Ok $dest
}

Passo "Programas (winget)"
if (-not (Tem "winget")) { throw "winget nao encontrado. Instale o 'App Installer' pela Microsoft Store." }
Garante "git" "Git.Git"
Garante "node" "OpenJS.NodeJS.LTS"
Garante "ffmpeg" "Gyan.FFmpeg"
Garante "gh" "GitHub.cli"
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { Garante "python" "Python.Python.3.11" }
$PY = if (Tem "py") { "py" } else { "python" }
$PYARGS = if ($PY -eq "py") { @("-3.11") } else { @() }

Passo "Variaveis de ambiente"
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User"); $env:PYTHONUTF8 = "1"
Ok "PYTHONUTF8=1"
if ($DOCS -ne (Join-Path $HOME "Documents")) {
  [Environment]::SetEnvironmentVariable("WE_DOCS", $DOCS, "User"); $env:WE_DOCS = $DOCS
  Ok "WE_DOCS=$DOCS (Documentos fora do padrao, ex.: OneDrive)"
}

Passo "Skills e pastas do kit"
foreach ($s in @("we-posts", "we-reels")) { Liga (Join-Path $HOME ".cursor\skills\$s") (Join-Path $KIT "skills\$s") }
Liga (Join-Path $TOOLS "reels-we") (Join-Path $KIT "tools\reels-we")
New-Item -ItemType Directory -Force -Path (Join-Path $DOCS "hyperframes\we-reels-finais") | Out-Null
Liga (Join-Path $DOCS "hyperframes\we-modelos") (Join-Path $KIT "we-modelos")

Passo "whisper.cpp"
if (Tem "whisper-cli") { Ok "whisper-cli" } else {
  $rel = Invoke-RestMethod "https://api.github.com/repos/ggml-org/whisper.cpp/releases/latest"
  $asset = $rel.assets | Where-Object { $_.name -eq "whisper-bin-x64.zip" } | Select-Object -First 1
  if (-not $asset) { throw "nao achei whisper-bin-x64.zip no release $($rel.tag_name)" }
  $zip = Join-Path $env:TEMP "whisper-bin-x64.zip"
  $dir = Join-Path $TOOLS "whisper"
  curl.exe -L --fail -o $zip $asset.browser_download_url
  Expand-Archive $zip -DestinationPath $dir -Force
  $exe = Get-ChildItem $dir -Recurse -Filter "whisper-cli.exe" | Select-Object -First 1
  if (-not $exe) { throw "whisper-cli.exe nao veio no zip" }
  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  if ($userPath -notlike "*$($exe.DirectoryName)*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$($exe.DirectoryName)", "User")
  }
  Recarrega-Path
  Ok "whisper-cli ($($rel.tag_name))"
}
$HFW = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
Baixa "$HFW/ggml-small.bin" (Join-Path $WHISPER_DIR "ggml-small.bin")
if (-not $SemWhisperLarge) { Baixa "$HFW/ggml-large-v3.bin" (Join-Path $WHISPER_DIR "ggml-large-v3.bin") }

Passo "Kokoro (voz base da dublagem)"
$KVENV = Join-Path $TOOLS "kokoro\.venv"
$KPY = Join-Path $KVENV "Scripts\python.exe"
if (-not (Test-Path $KPY)) { & $PY @PYARGS -m venv $KVENV }
& $KPY -m pip install --quiet --upgrade pip
& $KPY -m pip install --quiet "kokoro-onnx==0.6.1" soundfile
Ok $KPY

if ($SemApplio) { Aviso "Applio pulado (-SemApplio): recorte.py/prep.py precisam de torch; dublagem EN/ES fica indisponivel." } else {
  Passo "Applio (torch + RVC) - demora e baixa alguns GB"
  if (-not (Test-Path (Join-Path $APPLIO ".git"))) { git clone https://github.com/IAHispano/Applio.git $APPLIO }
  git -C $APPLIO checkout -q $APPLIO_COMMIT
  $APY = Join-Path $APPLIO "env\python.exe"
  if (-not (Test-Path $APY)) {
    Push-Location $APPLIO
    cmd /c "run-install.bat < nul"
    Pop-Location
  }
  if (-not (Test-Path $APY)) { throw "Applio nao instalou ($APY nao existe). Veja a saida acima." }
  & $APY -m pip install --quiet pillow soundfile
  & $APY -c "import torch, torchaudio; torchaudio.pipelines.MMS_FA.get_model(); print('torch', torch.__version__, 'torchaudio', torchaudio.__version__)"
  Ok $APY

  Passo "Vozes treinadas (release privado)"
  Garante-Gh
  $tmpv = Join-Path $env:TEMP "vozes-we"
  New-Item -ItemType Directory -Force -Path $tmpv | Out-Null
  gh release download vozes-v1 -R $REPO_KIT -D $tmpv --skip-existing
  foreach ($par in @(@("c06-esq", @("c06-esq_20e_1740s.pth", "c06-esq.index")), @("c06-dir", @("c06-dir_20e_1580s.pth", "c06-dir.index")))) {
    $d = Join-Path $APPLIO "logs\$($par[0])"
    New-Item -ItemType Directory -Force -Path $d | Out-Null
    foreach ($f in $par[1]) { Copy-Item (Join-Path $tmpv $f) (Join-Path $d $f) -Force }
    Ok $d
  }
}

Passo "decupagem-videos"
$DEC = Join-Path $DOCS "decupagem-videos"
if (-not (Test-Path (Join-Path $DEC ".git"))) {
  Garante-Gh
  gh repo clone wemktdigital/decupagem-videos $DEC
}
Push-Location $DEC; npm install --silent; Pop-Location
Ok $DEC

Passo "MCPs do Cursor (Envato e Canva)"
$mcp = Join-Path $HOME ".cursor\mcp.json"
& $KPY -c @"
import json, pathlib
p = pathlib.Path(r'$mcp')
cfg = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
s = cfg.setdefault('mcpServers', {})
s.setdefault('envato', {'url': 'https://mcp.envato.com/mcp'})
s.setdefault('canva', {'url': 'https://mcp.canva.com/mcp'})
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('ok  ', p)
"@

Passo "Skills oficiais do HyperFrames"
npx --yes hyperframes skills update
npx --yes hyperframes doctor

Write-Host ""
Write-Host "Pronto." -ForegroundColor Green
Write-Host "1. Feche e abra o Cursor (PATH e variaveis novas)."
Write-Host "2. Em Cursor Settings > MCP, faca login no Envato e no Canva."
Write-Host "3. Abra um chat novo e peca: 'editar o corte NN' (skill we-reels)."
