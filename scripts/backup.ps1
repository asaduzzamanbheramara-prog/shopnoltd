# Shopnoltd Database Backup Script
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "C:\Users\asadu\shopnoltd-backups\$timestamp"
New-Item -ItemType Directory -Force -Path $backupDir

# Backup PostgreSQL
kubectl exec deployment/postgres-prod -- pg_dump -U shopnoltd shopnoltd > "$backupDir\database.sql"

# Backup Docker volumes
docker run --rm -v shopnoltd_postgres-data:/data -v $backupDir:/backup alpine tar czf /backup/postgres-data.tar.gz -C /data .

# Backup configs
Copy-Item C:\Users\asadu\.cloudflared "$backupDir\cloudflared-config" -Recurse

# Upload to cloud (optional)
# aws s3 cp $backupDir s3://shopnoltd-backups/$timestamp/ --recursive

# Cleanup old backups (keep last 7 days)
Get-ChildItem "C:\Users\asadu\shopnoltd-backups" -Directory | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item -Recurse -Force

Write-Host "Backup completed: $backupDir"
