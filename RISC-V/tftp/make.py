import struct
import binascii
import time

with open("boot.txt", "rb") as f:
    payload = f.read()

dcrc = binascii.crc32(payload) & 0xffffffff

magic = 0x27051956
time_stamp = int(time.time())
data_size = len(payload)
load_addr = 0x00000000
exec_addr = 0x00000000

hcrc = 0
os_type = 5
arch = 22
img_type = 6
comp = 0
name = b"Network Boot Script".ljust(32, b'\x00')[:32]

header = struct.pack(">IIIIIIBBBB32s", magic, hcrc, time_stamp, data_size, load_addr, exec_addr, os_type, arch, img_type, comp, name)

header = struct.pack(">IIIIIIBBBB32s", magic, hcrc, time_stamp, data_size, load_addr, exec_addr, os_type, arch, img_type, comp, name)

correct_format = ">IIIIIIIBBBB32s"

header = struct.pack(correct_format, magic, hcrc, time_stamp, data_size, load_addr, exec_addr, dcrc, os_type, arch, img_type, comp, name)

hcrc = binascii.crc32(header) & 0xffffffff

header = struct.pack(correct_format, magic, hcrc, time_stamp, data_size, load_addr, exec_addr, dcrc, os_type, arch, img_type, comp, name)

with open("boot.scr", "wb") as f:
    f.write(header + payload)

print("boot.scr successfully created for RISC-V U-Boot!")
