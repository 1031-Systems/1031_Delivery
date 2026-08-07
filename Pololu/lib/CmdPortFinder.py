"""
Cross-platform detection of a Pololu Maestro's Command Port.

Strategy (checked in order, first hit wins):
  1. USB interface number, read from `hwid` (Windows "MI_00"/"MI_01") or
     from `location` (Linux "1-3:1.0", and Windows on pyserial >= ~3.5
     "1-4:x.0"). Interface 0 is always the Command Port, interface 1 the
     TTL Port, on every platform where the OS exposes it.
  2. Windows text fallback: `description`/`product` containing "Command"
     or "TTL", which Pololu's own Windows driver sets as the friendly name.
  3. Final fallback (used for macOS, where neither of the above is
     available): the numerically-lowest /dev/cu.usbmodem* device, since
     Pololu's docs state the Command Port always gets the lower number.
"""

import re
import sys

import serial.tools.list_ports as list_ports

POLOLU_VID = 0x1FFB


def _interface_number(port):
    """Return the USB interface number (0 or 1) if we can determine it, else None."""
    m = re.search(r"MI_(\d+)", port.hwid or "", re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"\.(\d+)$", port.location or "")
    if m:
        return int(m.group(1))
    return None


def _natural_sort_key(device):
    """Sort device paths/names by their trailing number so 'COM9' < 'COM10', etc."""
    m = re.search(r"(\d+)$", device)
    return (int(m.group(1)) if m else -1, device)


def find_maestro_command_port(vid=POLOLU_VID, pid=None, serial_number=None):
    """
    Find the Command Port of a connected Pololu Maestro.

    Args:
        vid: USB vendor ID to match (default: Pololu's 0x1FFB).
        pid: USB product ID to match, or None to match any Maestro model.
        serial_number: Board serial number to match, needed if multiple
            Maestros are connected, to avoid mixing up their ports.

    Returns:
        The device string (e.g. '/dev/ttyACM0', 'COM4',
        '/dev/cu.usbmodem14201') for the Command Port, or None if no
        matching Maestro was found.
    """
    candidates = [
        p for p in list_ports.comports()
        if p.vid == vid
        and (pid is None or p.pid == pid)
        and (serial_number is None or p.serial_number == serial_number)
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0].device

    # 1. Interface-number based detection (Linux, and Windows when exposed).
    numbered = [(_interface_number(p), p) for p in candidates]
    numbered = [(n, p) for n, p in numbered if n is not None]
    if numbered:
        numbered.sort(key=lambda t: t[0])
        return numbered[0][1].device

    # 2. Windows friendly-name fallback.
    if sys.platform.startswith("win"):
        for p in candidates:
            text = f"{p.description or ''} {p.product or ''}".lower()
            if "command" in text:
                return p.device

    # 3. macOS (and any other platform lacking the above info): lowest device name.
    return sorted(candidates, key=lambda p: _natural_sort_key(p.device))[0].device


if __name__ == "__main__":
    port = find_maestro_command_port()
    if port:
        print(f"Maestro Command Port: {port}")
    else:
        print("No Pololu Maestro found.")

