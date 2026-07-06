# Check if services are up
$services = @(
    @{name="API"; url="http://localhost:8000/health"},
    @{name="Admin UI"; url="http://localhost:8080/"},
    @{name="PostgreSQL"; url="http://localhost:5432"},
    @{name="Cloudflare Tunnel"; check="service"}
)

foreach ($svc in $services) {
    if ($svc.check -eq "service") {
        $status = (Get-Service Cloudflared).Status
    } else {
        try {
            $response = Invoke-WebRequest -Uri $svc.url -UseBasicParsing -TimeoutSec 5
            $status = "UP"
        } catch {
            $status = "DOWN"
        }
    }
    Write-Host "$($svc.name): $status" -ForegroundColor $(if($status -eq "UP" -or $status -eq "Running"){"Green"}else{"Red"})
}
