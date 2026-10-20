$ErrorActionPreference = 'Continue'
$dockerExe = 'C:\Users\rajes\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
$logDir = 'C:\Users\rajes\Documents\Codex\xls-gepa\logs'
$logPath = Join-Path $logDir 'local-gepa-run.log'
$exitPath = Join-Path $logDir 'local-gepa-run.exit'

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Remove-Item -LiteralPath $exitPath -Force -ErrorAction SilentlyContinue

try {
    & $dockerExe pull ollama/ollama 2>&1 | Tee-Object -FilePath $logPath
    if ($LASTEXITCODE -ne 0) { throw "Ollama image pull failed: $LASTEXITCODE" }

    $existingContainer = & $dockerExe ps -a --filter 'name=^/xls-gepa-ollama$' --format '{{.Names}}'
    if ($existingContainer -eq 'xls-gepa-ollama') {
        & $dockerExe start xls-gepa-ollama 2>&1 | Tee-Object -FilePath $logPath -Append
    } else {
        & $dockerExe run -d --name xls-gepa-ollama -p 127.0.0.1:11434:11434 -v xls-gepa-ollama:/root/.ollama ollama/ollama 2>&1 |
            Tee-Object -FilePath $logPath -Append
    }
    if ($LASTEXITCODE -ne 0) { throw "Ollama container start failed: $LASTEXITCODE" }

    & $dockerExe exec xls-gepa-ollama ollama pull qwen2.5-coder:3b 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) { throw "Model pull failed: $LASTEXITCODE" }

    & $dockerExe exec xls-gepa-work python3 /workspace/run_gepa.py --authorization /workspace/configs/model-authorization.json 2>&1 |
        Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) { throw "GEPA run failed: $LASTEXITCODE" }
    Set-Content -LiteralPath $exitPath -Value '0'
} catch {
    $_ | Out-String | Tee-Object -FilePath $logPath -Append
    Set-Content -LiteralPath $exitPath -Value '1'
    exit 1
}

