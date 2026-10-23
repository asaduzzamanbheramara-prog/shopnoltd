# Read-only recovery USB device inventory

`tools/software-os-diagnostics/usb_device_inventory.py` provides read-only inventory on Linux, Windows, and macOS. Linux reads `lsblk` JSON; Windows queries PowerShell CIM disk metadata; macOS reads `diskutil` plist metadata. It reports only removable/USB whole-disk candidates and does not download, verify, partition, format, mount, or write a device.

Run:

```sh
python3 tools/software-os-diagnostics/usb_device_inventory.py
python3 tools/software-os-diagnostics/usb_device_inventory.py --json
```

**Safety limits:** a removable flag is only a hint. Some USB enclosures report flags inconsistently, and some removable devices are not intended as recovery targets. Verify model, capacity, path and the physical device independently. The output always sets `write_authorized: false`. This helper is not a USB writer and must never be used as sufficient authorization for a destructive operation. Inventory filtering is conservative and may omit devices whose OS metadata does not clearly identify them as USB/removable. A separately designed, separately authorized writer remains future work.
