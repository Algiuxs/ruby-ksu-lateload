#!/usr/bin/env python3
"""Patch the CRC32 checksum in a KernelSU .ko binary's module_layout section.

Usage:
    python3 patch_crc.py <input.ko> <crc_hex> <section_name>

The .ko binary format includes a __versions section that contains version
info with CRCs. Each entry is: 8-byte CRC (little-endian, arm64 unsigned
long) + null-terminated symbol name.

If the target symbol already has the expected CRC, nothing is written
(idempotent).
"""

import sys
import struct


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
    if len(sys.argv) != 4:
        print("Usage: patch_crc.py <input.ko> <crc_hex> <section_name>")
        print("  crc_hex: CRC32 value in hex (e.g., 0xf0c01ec5)")
        print('  section_name: e.g., "module_layout"')
        sys.exit(1)

    input_ko = sys.argv[1]
    crc_hex = sys.argv[2]
    section_name = sys.argv[3]
    output_ko = input_ko.replace(".ko", "_patched.ko")

    target_crc = int(crc_hex, 16)

    with open(input_ko, "rb") as f:
        data = bytearray(f.read())

    # Find __versions or .modversions section
    sec = None
    for cand in ("__versions", ".modversions"):
        sec = find_section(data, cand)
        if sec:
            break

    if not sec:
        print("ERROR: no __versions section found")
        sys.exit(1)

    sec_offset, sec_size = sec
    patched = False
    pos = sec_offset
    end = sec_offset + sec_size

    # On arm64, unsigned long is 8 bytes: 8-byte CRC + null-terminated name
    while pos < end - 9:
        crc = struct.unpack_from("<Q", data, pos)[0]
        name_start = pos + 8
        name_end = data.find(b"\x00", name_start)
        if name_end == -1 or name_end >= end:
            break
        name = data[name_start:name_end].decode("ascii", errors="ignore")

        if name == section_name:
            if crc == target_crc:
                print("Already patched: %s CRC = 0x%08x" % (section_name, crc))
            else:
                data[pos:pos + 8] = struct.pack("<Q", target_crc)
                print('Patched CRC for "%s" at offset %d: 0x%08x -> %s'
                      % (section_name, pos, crc, crc_hex))
            patched = True
            break

        pos = name_end + 1

    if not patched:
        print('WARNING: "%s" not found in __versions section' % section_name)
        sys.exit(1)

    with open(output_ko, "wb") as f:
        f.write(data)

    print("Patched CRC saved to %s" % output_ko)


if __name__ == "__main__":
    main()