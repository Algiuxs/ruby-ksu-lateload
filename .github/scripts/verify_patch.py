#!/usr/bin/env python3
"""Verify that the .ko has been correctly patched (vermagic + CRC).

Usage:
    python3 verify_patch.py <input.ko> <expected_vermagic> <expected_crc_hex> <symbol_name>

Exit status: 0 on success, non-zero on failure.
"""

import struct
import sys


def find_section(data, name):
    """Find a section by name in ELF64, return (offset, size) or None."""
    if len(data) < 64 or data[:4] != b"\x7fELF":
        return None
    if data[4] != 2:
        return None
    (e_shoff,) = struct.unpack_from("<Q", data, 0x28)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x3A)

    shstr_o = e_shoff + e_shstrndx * e_shentsize
    (shstr_off,) = struct.unpack_from("<Q", data, shstr_o + 0x18)

    for i in range(e_shnum):
        o = e_shoff + i * e_shentsize
        sh_name, _sh_type, _flags, _addr, sh_offset, sh_size = \
            struct.unpack_from("<IIQQQQ", data, o)
        end = data.find(b"\x00", shstr_off + sh_name)
        if end < 0:
            continue
        sec_name = data[shstr_off + sh_name:end].decode("ascii", errors="ignore")
        if sec_name == name:
            return (sh_offset, sh_size)
    return None


def main():
    if len(sys.argv) != 5:
        print("Usage: verify_patch.py <input.ko> <expected_vermagic> <expected_crc_hex> <symbol_name>")
        sys.exit(1)

    input_ko = sys.argv[1]
    expected_vermagic = sys.argv[2]
    expected_crc_hex = sys.argv[3]
    symbol_name = sys.argv[4]
    expected_crc = int(expected_crc_hex, 16)

    with open(input_ko, "rb") as f:
        data = bytearray(f.read())

    # 1. Verify vermagic string is present
    expected_vermagic_bytes = expected_vermagic.encode("ascii").replace(b"+", b"")
    if expected_vermagic_bytes in data:
        print("VERMAGIC OK: target version string present in .ko")
    else:
        print("VERMAGIC FAIL: target version string NOT found in .ko")
        sys.exit(1)

    # 2. Verify CRC for the symbol in __versions section
    sec = None
    for cand in ("__versions", ".modversions"):
        sec = find_section(data, cand)
        if sec:
            break

    if not sec:
        print("CRC FAIL: no __versions section found")
        sys.exit(1)

    sec_offset, sec_size = sec
    found = False
    pos = sec_offset
    end = sec_offset + sec_size

    while pos < end - 9:
        crc = struct.unpack_from("<Q", data, pos)[0]
        name_start = pos + 8
        name_end = data.find(b"\x00", name_start)
        if name_end == -1 or name_end >= end:
            break
        name = data[name_start:name_end].decode("ascii", errors="ignore")

        if name == symbol_name:
            if crc == expected_crc:
                print("CRC OK: %s CRC = 0x%08x" % (symbol_name, crc))
                found = True
            else:
                print("CRC FAIL: %s CRC = 0x%08x (expected 0x%s)"
                      % (symbol_name, crc, expected_crc_hex))
                sys.exit(1)
            break

        pos = name_end + 1

    if not found:
        print("CRC FAIL: %s entry not found in __versions section" % symbol_name)
        sys.exit(1)


if __name__ == "__main__":
    main()