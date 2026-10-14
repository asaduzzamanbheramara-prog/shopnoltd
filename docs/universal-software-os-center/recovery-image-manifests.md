# Recovery image manifest contract

This manifest is the metadata contract for future recovery-image catalogue entries. It is **not** an image downloader, USB writer, or proof of compatibility.

## Validation

Run from the repository root:

```sh
python scripts/validate-recovery-image-manifest.py catalogue/recovery-images/linux-recovery-image-template.json
python -m unittest discover -s tests/software-os-diagnostics -p 'test_*.py' -v
```

The template is intentionally marked `draft`, with image verification and boot testing set to `not-verified` and `not-tested`. It must not be presented as a tested image or recommended download.

## Promotion rules

A manifest marked `approved-for-listing` must record a publisher-sourced SHA-256/SHA-512 digest or signature verification, the URL where the expected digest/signature was published, and a successful boot test with environment and date. A `digest-verified` or `signature-verified` status must include a valid SHA-256/SHA-512 value and an HTTPS digest-source URL. A `signature-verified` claim must additionally record an HTTPS signature URL, signature format, and signer identity. VM boot success is not a claim of physical-hardware compatibility. Reviewers must also confirm that the official source is specific to the named distribution or vendor and that the architecture, firmware, Secure Boot, and capacity claims match its current documentation.

Do not store downloaded proprietary images or binaries in the repository. Use official publisher pages, and keep the publisher's source URL distinct from any direct image URL. A manifest passing schema validation only means its fields satisfy the contract; it does not independently validate the claims, verify a cryptographic signature, fetch the image, or prove the publisher identity. Do not mark an image signature-verified until a separate trusted-key verification step has actually passed.
