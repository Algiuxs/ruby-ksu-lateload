#!/usr/bin/env python3
import sys

def patch_vermagic(ko_path, new_vermagic, output_path=None):
    if output_path is None:
        output_path = ko_path + ".patched"

    with open(ko_path, 'rb') as f:
        data = bytearray(f.read())

    marker = b'vermagic='
    idx = data.find(marker)
    if idx == -1:
        print("ERROR: 'vermagic=' not found"); sys.exit(1)

    start = idx + len(marker)
    end = data.find(b'\x00', start)
    if end == -1:
        print("ERROR: null terminator not found"); sys.exit(1)

    old = bytes(data[start:end])
    print(f"Old vermagic ({len(old)} bytes): {old.decode(errors='replace')}")

    new = new_vermagic.encode()
    print(f"New vermagic ({len(new)} bytes): {new_vermagic}")

    if len(new) > (end - start):
        print(f"ERROR: new string is {len(new) - (end - start)} bytes too long"); sys.exit(1)

    data[start:end] = new + b'\x00' * (end - start - len(new))

    with open(output_path, 'wb') as f:
        f.write(data)

    print(f"Written: {output_path}  (null-padded {end - start - len(new)} bytes)")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.ko> \"<new_vermagic>\" [output.ko]"); sys.exit(1)
    patch_vermagic(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
