#!/usr/bin/env python3
"""Patch the CRC32 checksum in a KernelSU .ko binary's module_layout section."""

import struct
import sys


def find_section(data, name):
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
        sh_name, _sh_type, _flags, _addr, sh_offset, sh_size = struct.unpack_from("<IIQQQQ", data, o)
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
        sys.exit(1)

    input_ko = sys.argv[1]
    crc_hex = sys.argv[2]
    section_name = sys.argv[3]
    output_ko = input_ko.replace(".ko", "_patched.ko")

    target_crc = int(crc_hex, 16)

    with open(input_ko, "rb") as f:
        data = bytearray(f.read())

    sec = None
    for cand in ("__versions", ".modversions"):
        sec = find_section(data, cand)
        if sec:
            break

    if not sec:
        print("ERROR: no __versions section found")
        sys.exit(1)

    sec_offset, sec_size = sec
    entry_size = 64
    crc_size = 8

    patched = False
    for pos in range(sec_offset, sec_offset + sec_size - entry_size + 1, entry_size):
        crc = struct.unpack_from("<Q", data, pos)[0]
        name_bytes = data[pos + crc_size:pos + entry_size]
        name = name_bytes.split(b"\0", 1)[0].decode("ascii", errors="ignore")

        if name == section_name:
            if crc == target_crc:
                print("Already patched: %s CRC = 0x%08x" % (section_name, crc))
            else:
                data[pos:pos + crc_size] = struct.pack("<Q", target_crc)
                print('Patched CRC for "%s" at offset %d: 0x%08x -> %s'
                      % (section_name, pos, crc, crc_hex))
            patched = True
            break

    if not patched:
        print('WARNING: "%s" not found in __versions section' % section_name)
        sys.exit(1)

    with open(output_ko, "wb") as f:
        f.write(data)

    print("Patched CRC saved to %s" % output_ko)


if __name__ == "__main__":
    main()