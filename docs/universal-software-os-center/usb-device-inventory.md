# Read-only recovery USB device inventory

`tools/software-os-diagnostics/usb_device_inventory.py` is an initial Linux-only helper. It reads `lsblk` JSON and reports removable whole-disk candidates; it does not download, verify, partition, format, mount, or write a device.

Run:

```sh
python3 tools/software-os-diagnostics/usb_device_inventory.py
python3 tools/software-os-diagnostics/usb_device_inventory.py --json
```

**Safety limits:** a removable flag is only a hint. Some USB enclosures report flags inconsistently, and some removable devices are not intended as recovery targets. Verify model, capacity, path and the physical device independently. The output always sets `write_authorized: false`. This helper is not a USB writer and must never be used as sufficient authorization for a destructive operation. Windows and macOS inventory support and a separately designed writer remain future work.
