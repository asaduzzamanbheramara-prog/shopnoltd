# Offline artifact verification

The Software & OS Center can point users to official release pages, but a link
alone does not prove that a downloaded ISO or installer is intact.

## Use the local checker

Run from a terminal with Python 3.10+:

```sh
python tools/software-os-diagnostics/verify_artifact.py /path/to/download.iso \
  --algorithm sha256 --expected PASTE_THE_PUBLISHER_SHA256_HERE
```

On Windows, use the local file path, for example:

```powershell
py tools/software-os-diagnostics/verify_artifact.py C:\Downloads\image.iso --algorithm sha256 --expected PASTE_THE_PUBLISHER_SHA256_HERE
```

Obtain the expected digest from the software publisher's official release page
or signature-verified metadata. Do not trust a checksum copied from the same
untrusted mirror as the artifact. Prefer a publisher signature when one is
provided; a checksum only establishes equality with the supplied digest.

Exit codes: `0` match, `1` mismatch, `2` invalid input or file error.

## Safety boundary

- Reads the selected file in chunks; does not change it.
- Makes no network requests.
- Does not execute, install, extract, or launch the artifact.
- Does not format or write to USB drives or disks.
- A passing checksum does not prove the software is safe, compatible, or
  authentic unless the expected digest itself is trusted.

Bootable media creation remains a separate, explicitly confirmed workflow.
Never select a target disk or format media based only on a website response.
