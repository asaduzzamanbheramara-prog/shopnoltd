# Shopnoltd read-only diagnostics starter

This is a small, offline Python diagnostic utility for the Software & OS Center implementation phase. It reports OS family/release, CPU architecture, Python version, and free/total bytes on the home volume. It does not print the home path.

## Run

```sh
python3 tools/software-os-diagnostics/diagnose.py
```

The output is JSON. Review it before sharing it with anyone. This starter does not upload results, require administrator/root privileges, install packages, inspect private files, change settings, or repair disks/bootloaders.

## Explicit non-goals

- Not an installer or system repair tool.
- Not a substitute for signed installers or a bootable recovery image.
- Does not claim full OS/hardware compatibility.
- Do not extend this utility to run arbitrary commands from website/API/catalogue content.

Before distribution as a desktop app, add platform-specific packaging, signed releases, a privacy review, and additional platform tests.
