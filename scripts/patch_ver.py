#!/usr/bin/env python3
"""Patch the kernel version string in a KernelSU .ko binary."""

import sys
import struct

def patch_version(input_path, target_version, output_path):
    with open(input_path, 'rb') as f:
        data = bytearray(f.read())
    
    old_pattern = b'4.19.191-g914ba8403bb3-dirty SMP preempt mod_unload modversions aarch64'
    new_pattern = target_version.encode('ascii')
    new_pattern = new_pattern.replace(b'+', b'')
    
    idx = data.find(old_pattern)
    if idx < 0:
        idx = data.find(b'4.19.191-')
        if idx < 0:
            print('ERROR: Could not find version string in', input_path)
            return False
        end = min(idx + 60, len(data))
        old_pattern = data[idx:end]
        if not old_pattern.startswith(b'4.19.191-'):
            print('Could not determine version pattern at offset', idx)
            return False
    
    data[idx:idx+len(new_pattern)] = new_pattern
    with open(output_path, 'wb') as f:
        f.write(data)
    print('Version string patched at offset', idx)
    return True

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Usage: python3 patch_ver.py <input.ko> <target_version> <output.ko>')
        print('  target_version example: "4.19.191-ge6429b82e599 SMP preempt mod_unload modversions aarch64"')
        sys.exit(1)
    
    input_ko = sys.argv[1]
    target_ver = sys.argv[2]
    output_ko = sys.argv[3]
    
    success = patch_version(input_ko, target_ver, output_ko)
    if success:
        print('Successfully patched', input_ko, '->', output_ko)
    else:
        print('Failed to patch version string')
        sys.exit(1)
