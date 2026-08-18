#!/usr/bin/env python3
"""
Minimal FDT (flattened device tree) parser.
Outputs JSON.
Usage: python3 deviceTreeToJson.py [in.dtb] [out.json]
       (omit out.json to print to stdout)
"""
import struct
import sys
import json

FDT_BEGIN_NODE = 0x1
FDT_END_NODE   = 0x2
FDT_PROP       = 0x3
FDT_NOP        = 0x4
FDT_END        = 0x9

def align4(x):
    return (x + 3) & ~3

def looks_like_strings(b):
    if not b or b[-1] != 0:
        return False
    parts = b.split(b'\x00')
    if parts and parts[-1] == b'':
        parts = parts[:-1]
    if not parts:
        return False
    for p in parts:
        if not p or not all(32 <= c < 127 for c in p):
            return False
    return True

def parse(path):
    data = open(path, 'rb').read()

    magic, totalsize, off_dt_struct, off_dt_strings, off_mem_rsvmap, \
        version, last_comp_version, boot_cpuid_phys, size_dt_strings, \
        size_dt_struct = struct.unpack_from('>10I', data, 0)

    if magic != 0xd00dfeed:
        raise ValueError(f"bad magic: got 0x{magic:08x}, expected 0xd00dfeed")

    header = {
        "magic": f"0x{magic:08x}",
        "totalsize": totalsize,
        "version": version,
        "last_comp_version": last_comp_version,
        "boot_cpuid_phys": boot_cpuid_phys,
    }

    reservations = []
    off = off_mem_rsvmap
    while True:
        addr, size = struct.unpack_from('>QQ', data, off)
        off += 16
        if addr == 0 and size == 0:
            break
        reservations.append({"addr": f"0x{addr:x}", "size": f"0x{size:x}"})

    def get_string(nameoff):
        end = data.index(b'\x00', off_dt_strings + nameoff)
        return data[off_dt_strings + nameoff:end].decode('ascii', 'replace')

    off = off_dt_struct
    addr_cells_stack = [2]
    size_cells_stack = [1]

    def decode_prop(propname, propdata, ac, sc):
        plen = len(propdata)
        if propname == '#address-cells':
            addr_cells_stack[-1] = struct.unpack('>I', propdata)[0]
        if propname == '#size-cells':
            size_cells_stack[-1] = struct.unpack('>I', propdata)[0]

        if propname == 'reg' and plen > 0:
            stride = (ac + sc) * 4
            pairs = []
            p = 0
            while p + stride <= plen:
                addr = 0
                for i in range(ac):
                    addr = (addr << 32) | struct.unpack_from('>I', propdata, p + i*4)[0]
                size = 0
                for i in range(sc):
                    size = (size << 32) | struct.unpack_from('>I', propdata, p + ac*4 + i*4)[0]
                pairs.append({"addr": f"0x{addr:x}", "size": f"0x{size:x}"})
                p += stride
            return pairs
        elif looks_like_strings(propdata):
            strs = propdata.rstrip(b'\x00').split(b'\x00')
            return [s.decode('ascii') for s in strs]
        elif plen == 4:
            val = struct.unpack('>I', propdata)[0]
            return f"0x{val:x}"
        elif plen == 0:
            return True
        else:
            return {"hex": propdata.hex(), "bytes": plen}

    def parse_node():
        nonlocal off
        node = {"name": "", "properties": {}, "children": []}
        end = data.index(b'\x00', off)
        node["name"] = data[off:end].decode('ascii', 'replace')
        off = align4(end + 1)

        addr_cells_stack.append(addr_cells_stack[-1])
        size_cells_stack.append(size_cells_stack[-1])

        while True:
            tok, = struct.unpack_from('>I', data, off)
            if tok == FDT_BEGIN_NODE:
                off += 4
                child = parse_node()
                node["children"].append(child)
            elif tok == FDT_END_NODE:
                off += 4
                break
            elif tok == FDT_PROP:
                off += 4
                plen, nameoff = struct.unpack_from('>II', data, off)
                off += 8
                propname = get_string(nameoff)
                propdata = data[off:off + plen]
                off = align4(off + plen)
                ac = addr_cells_stack[-2] if len(addr_cells_stack) > 1 else 2
                sc = size_cells_stack[-2] if len(size_cells_stack) > 1 else 1
                node["properties"][propname] = decode_prop(propname, propdata, ac, sc)
            elif tok == FDT_NOP:
                off += 4
                continue
            elif tok == FDT_END:
                break
            else:
                raise ValueError(f"unknown token 0x{tok:x} at offset {off}")

        addr_cells_stack.pop()
        size_cells_stack.pop()
        return node

    tok, = struct.unpack_from('>I', data, off)
    if tok != FDT_BEGIN_NODE:
        raise ValueError(f"expected FDT_BEGIN_NODE at struct start, got 0x{tok:x}")
    off += 4
    root = parse_node()

    return {
        "header": header,
        "memory_reservations": reservations,
        "root": root,
    }

if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        print(f"usage: {sys.argv[0]} <file.dtb> [out.json]")
        sys.exit(1)
    result = parse(sys.argv[1])
    text = json.dumps(result, indent=2)
    if len(sys.argv) == 3:
        with open(sys.argv[2], 'w') as f:
            f.write(text)
        print(f"wrote {sys.argv[2]}")
    else:
        print(text)