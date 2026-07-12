Write-Host "Starting port-forwards and tunnel..." -ForegroundColor Cyan

Get-Process kubectl -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3

# CORRECTED: this used to forward ingress-nginx-controller (namespace no
# longer exists) to port 8090. But cloudflared's config.yml sends every
# hostname to 127.0.0.1:8080 -- these two never matched, which is why the
# whole public site was down regardless of pod health. tenant-router is
# the real current router (Redis-backed dynamic routing); forward IT to
# the port Cloudflare actually expects.
Start-Process kubectl -ArgumentList "port-forward -n default svc/tenant-router 8080:80" -WindowStyle Hidden

# kept as-is: separate direct path to kf, unrelated to the tenant-router fix above
Start-Process kubectl -ArgumentList "port-forward svc/kf 8091:80 -n toolbox" -WindowStyle Hidden

Write-Host "Waiting 15s for port-forwards to stabilize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Start-Process cloudflared -ArgumentList "tunnel run" -WindowStyle Hidden

Write-Host "All services started!" -ForegroundColor Green
Start-Sleep -Seconds 10

Write-Host "Status check:" -ForegroundColor Cyan
curl http://shopnoltd.dpdns.org/ -I
curl http://kf.shopnoltd.dpdns.org/ -I
