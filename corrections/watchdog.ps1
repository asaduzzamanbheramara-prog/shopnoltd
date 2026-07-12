# CORRECTED: was watching/restarting port 8090 (ingress-nginx-controller,
# which no longer exists) -- meaning port 8080, the one cloudflared
# actually uses, was NEVER monitored or auto-restarted. Every manual
# `kubectl port-forward ... 8080:80` died the moment its terminal session
# ended, with nothing in place to bring it back. This is why the whole
# site kept going down. Now watches 8080 -> tenant-router.

while ($true) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8080/" -TimeoutSec 5 -ErrorAction Stop
    } catch {
        Write-Host "$(Get-Date): Restarting tenant-router port-forward (8080)..."
        Get-CimInstance Win32_Process -Filter "Name='kubectl.exe'" | Where-Object {$_.CommandLine -like "*8080*"} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 2
        Start-Process kubectl -ArgumentList "port-forward -n default svc/tenant-router 8080:80" -WindowStyle Hidden
    }

    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8091/" -TimeoutSec 5 -ErrorAction Stop
    } catch {
        Write-Host "$(Get-Date): Restarting kf port-forward (8091)..."
        Get-CimInstance Win32_Process -Filter "Name='kubectl.exe'" | Where-Object {$_.CommandLine -like "*8091*"} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 2
        Start-Process kubectl -ArgumentList "port-forward svc/kf 8091:80 -n toolbox" -WindowStyle Hidden
    }

    Start-Sleep -Seconds 30
}
