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

## Verify a detached OpenPGP signature offline

When a publisher provides a detached OpenPGP signature, verify it against a
trusted local keyring and a fingerprint checked independently from the publisher:

```sh
python tools/software-os-diagnostics/verify_detached_signature.py /path/to/image.iso /path/to/image.iso.sig \
  --keyring /path/to/publisher-trusted.gpg --expected-fingerprint PASTE_TRUSTED_FINGERPRINT_HERE
```

The verifier calls local `gpgv`, makes no network requests, and requires the
signature's signing or primary-key fingerprint to match the expected fingerprint.
A keyring supplied by an untrusted mirror is not trustworthy merely because
signature verification succeeds. The unit tests mock `gpgv`; they verify policy
and fail-closed handling, not a real publisher signature.

## Safety boundary

- Reads the selected file in chunks; does not change it.
- Makes no network requests.
- Does not execute, install, extract, or launch the artifact.
- Does not format or write to USB drives or disks.
- A passing checksum does not prove the software is safe, compatible, or
  authentic unless the expected digest itself is trusted.

Bootable media creation remains a separate, explicitly confirmed workflow.
Never select a target disk or format media based only on a website response.
