#!/usr/bin/env python3
import struct, sys

def inject(ko_path, crc, symname="module_layout"):
    with open(ko_path, 'rb') as f:
        data = bytearray(f.read())

    assert data[:4] == b'\x7fELF', "not ELF"
    assert data[4] == 2, "not 64-bit"
    assert data[5] == 1, "not little-endian"

    e_shoff     = struct.unpack_from('<Q', data, 0x28)[0]
    e_shentsize = struct.unpack_from('<H', data, 0x3a)[0]
    e_shnum     = struct.unpack_from('<H', data, 0x3c)[0]
    e_shstrndx  = struct.unpack_from('<H', data, 0x3e)[0]
    print(f"e_shoff=0x{e_shoff:x} entsize={e_shentsize} shnum={e_shnum} shstrndx={e_shstrndx}")

    shstr_hdr = e_shoff + e_shstrndx * e_shentsize
    shstr_off  = struct.unpack_from('<Q', data, shstr_hdr + 24)[0]
    shstr_size = struct.unpack_from('<Q', data, shstr_hdr + 32)[0]
    print(f"shstrtab @ 0x{shstr_off:x}, size {shstr_size}")

    versions_hdr = None
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        name_idx = struct.unpack_from('<I', data, off)[0]
        if name_idx >= shstr_size:
            continue
        end = data.index(0, shstr_off + name_idx)
        name = data[shstr_off + name_idx:end].decode('ascii', 'replace')
        if name == '__versions':
            versions_hdr = off
            old_off  = struct.unpack_from('<Q', data, off + 24)[0]
            old_size = struct.unpack_from('<Q', data, off + 32)[0]
            print(f"__versions: section[{i}] hdr=0x{off:x} sh_offset=0x{old_off:x} sh_size={old_size}")
            break

    if versions_hdr is None:
        print("ERROR: __versions section not found", file=sys.stderr)
        sys.exit(1)

    # Build one 64-byte modversion_info:
    #   u64 crc;            (8 bytes)
    #   char name[56];      (56 bytes, MODULE_NAME_LEN = 64 - 8)
    name_b = symname.encode()
    assert len(name_b) < 56
    entry = struct.pack('<Q', crc) + name_b + b'\x00' * (56 - len(name_b))
    assert len(entry) == 64

    # Append entry (8-byte aligned) at end of file
    while len(data) % 8:
        data.append(0)
    new_off = len(data)
    data.extend(entry)

    # Repoint section header: sh_offset (byte 24), sh_size (byte 32)
    struct.pack_into('<Q', data, versions_hdr + 24, new_off)
    struct.pack_into('<Q', data, versions_hdr + 32, 64)

    with open(ko_path, 'wb') as f:
        f.write(data)

    print(f"OK: injected '{symname}' crc=0x{crc:08x} -> sh_offset=0x{new_off:x} sh_size=64")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <ko> <crc_hex> [symname]")
        sys.exit(1)
    inject(sys.argv[1], int(sys.argv[2], 16), sys.argv[3] if len(sys.argv) > 3 else "module_layout")
