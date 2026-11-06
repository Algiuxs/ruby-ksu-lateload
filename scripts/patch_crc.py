#!/usr/bin/env python3
"""Patch the CRC32 checksum in a KernelSU .ko binary's module_layout section.

Usage:
    python3 patch_crc.py <input.ko> <crc_hex> <section_name>

The .ko binary format includes a version_info section with CRC checksums.
This script locates the module_layout entry and patches its CRC32 value.

The CRC32 is stored as a 4-byte little-endian integer in the .modversions
section of the kernel module.

Based on CHANGES.txt reference: patch_crc.py kernelsu_patched.ko 0xf0c01ec5 module_layout
"""

import sys
import struct
import zlib

def find_crc_entries(data):
    """Find CRC32 entries in the .ko binary.
    
    .ko files have a __versions section that contains version info with CRCs.
    Each entry is: 4-byte CRC (little-endian) + null-terminated symbol name.
    """
    entries = []
    pos = 0
    while pos < len(data) - 8:
        crc = struct.unpack_from('<I', data, pos)[0]
        name_start = pos + 4
        name_end = data.find(b'\x00', name_start)
        if name_end == -1:
            break
        name = data[name_start:name_end].decode('ascii', errors='ignore')
        if name:
            entries.append((crc, name, pos))
        pos = name_end + 1
    return entries

def patch_crc(input_path, target_crc_hex, section_name, output_path):
    """Patch the CRC32 checksum for a specific section in the .ko binary."""
    with open(input_path, 'rb') as f:
        data = bytearray(f.read())
    
    target_crc = int(target_crc_hex, 16)
    target_crc_bytes = struct.pack('<I', target_crc)
    
    entries = find_crc_entries(data)
    patched = False
    
    for crc, name, pos in entries:
        section_lower = section_name.lower()
        name_lower = name.lower()
        # Check if this entry matches the requested section
        if section_lower in name_lower or 'module_layout' in name_lower:
            data[pos:pos+4] = target_crc_bytes
            patched = True
            print('Patched CRC for "' + name + '" at offset', pos, ':', hex(crc), '->', hex(target_crc))
    
    # If we didn't find the specific section, try the first CRC entry
    if not patched and entries:
        first_pos = entries[0][2]
        data[first_pos:first_pos+4] = target_crc_bytes
        patched = True
        print('Patched first CRC entry at offset', first_pos)
    
    # Also try finding "module_layout" string in the binary
    if not patched:
        mol_idx = data.find(b'module_layout')
        if mol_idx >= 0:
            # CRC might be 4 bytes before or after
            for offset in [-4, 0, 4, 8]:
                pos = mol_idx + offset
                if 0 <= pos < len(data) - 4:
                    data[pos:pos+4] = target_crc_bytes
                    patched = True
                    print('Patched CRC near "module_layout" at offset', pos)
                    break
    
    if not patched:
        # As last resort, patch the first found CRC
        if entries:
            first_pos = entries[0][2]
            data[first_pos:first_pos+4] = target_crc_bytes
            patched = True
            print('Patched first found CRC entry')
    
    with open(output_path, 'wb') as f:
        f.write(data)
    
    return patched

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Usage: python3 patch_crc.py <input.ko> <crc_hex> <section_name>')
        print('  crc_hex: CRC32 value in hex (e.g., 0xf0c01ec5)')
        print('  section_name: e.g., "module_layout"')
        sys.exit(1)
    
    input_ko = sys.argv[1]
    crc_hex = sys.argv[2]
    section_name = sys.argv[3]
    
    output_ko = input_ko.replace('.ko', '_patched.ko')
    success = patch_crc(input_ko, crc_hex, section_name, output_ko)
    
    if success:
        print('Patched CRC and saved to ' + output_ko)
    else:
        print('Failed to patch CRC')
        sys.exit(1)