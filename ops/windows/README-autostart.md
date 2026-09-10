# Shopnoltd Windows/WSL 24/7 hosting

This directory documents the Windows-side startup contract for the Shopnoltd self-hosted server.

## Verified startup chain

The verified production sequence is:

`Windows boot -> Windows Autologon -> Shopnoltd-WSL-Autostart -> WSL Ubuntu -> systemd -> k3s -> ArgoCD -> Shopnoltd services`

The scheduled task must run as the interactive Windows user and execute:

`C:\Windows\System32\wsl.exe -d Ubuntu --exec sleep infinity`

The long-running `sleep infinity` process is intentional. WSL can terminate when no foreground process remains. Do **not** replace it with `/bin/true` because that exits immediately.

## Installer

Run `install-shopnoltd-autostart.ps1` once from PowerShell in the Windows user context. It creates/updates the canonical scheduled task:

`Shopnoltd-WSL-Autostart`

The installer does not contain passwords, tokens, Kubernetes credentials, or database credentials.

## Windows power policy

For 24/7 hosting:

- **Sleep:** Never (AC and battery)
- **Hibernate:** Never (AC and battery)
- **Display off:** Any preferred timeout, such as 10 minutes on AC
- **Manual Power -> Sleep:** Do not use while hosting
- **Win + L:** Safe; it locks Windows while the server continues running
- **Charger:** Keep connected for continuous hosting

Turning the display off is not the same as Windows Sleep. A display-off timeout does not stop WSL, k3s, or Shopnoltd services.

## Autologon

The current verified host uses Windows Autologon so the interactive user session is established automatically after reboot. Do not place the Windows password in this repository. Configure Autologon directly on the Windows host using the approved local Windows/Sysinternals procedure.

## Important runtime rule

GitHub `main` is the source of truth for application and deployment code. The Windows installer here documents/configures the host startup mechanism; it does not copy the repository into production. The normal application deployment path remains:

`GitHub main -> GitHub Actions -> GHCR -> ArgoCD/Kubernetes -> WSL/k3s`

## Verification after reboot

From PowerShell:

```powershell
whoami
wsl --list --verbose
Get-ScheduledTask -TaskName 'Shopnoltd-WSL-Autostart' | Select-Object TaskName,State
wsl -d Ubuntu -- systemctl is-system-running
wsl -d Ubuntu -- systemctl is-active k3s
wsl -d Ubuntu -- systemctl is-enabled k3s
```

Then verify Kubernetes and the public site using the normal Shopnoltd health checks.
