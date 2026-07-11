# KoBoCollect APKs

This folder contains tooling to download the official KoBoCollect APK from the project's GitHub releases.

Files
- `fetch_kobocollect_apk.ps1` — PowerShell script that downloads the latest (or specified) KoBoCollect APK.

Usage

Open PowerShell and run:

```powershell
# download latest release to the script directory
.\fetch_kobocollect_apk.ps1

# download to a custom directory
.\fetch_kobocollect_apk.ps1 -OutDir .\apks

# download a specific release tag
.\fetch_kobocollect_apk.ps1 -Tag v4.21.3
```

Notes
- The script uses the GitHub Releases API. If you hit rate limits, consider authenticating requests with a GitHub token.
- Alternatively, install KoBoCollect from Google Play Store on devices.
