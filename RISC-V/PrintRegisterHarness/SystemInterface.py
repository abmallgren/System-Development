import socket
import subprocess
import sys
import time

port = 4444
opcodes = sys.argv[1:]

command = [
    "qemu-system-riscv64",
    "-machine",
    "virt",
    "-m",
    "128M",
    "-nographic",
    "-bios",
    "none",
    "-kernel",
    "kernel.bin",
    "-monitor",
    "none",
    "-serial",
    f"tcp::{port},server,nowait",
]

qemu_process = subprocess.Popen(command)

time.sleep(1.0)

try:
  client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  client.connect(("127.0.0.1", port))
  client.settimeout(2.0)


  def read_until_prompt():
    buffer = ""
    start_time = time.time()
    while time.time() - start_time < 2.0:
      try:
        chunk = client.recv(4096).decode("utf-8", errors="ignore")
        if chunk:
          buffer += chunk
          if buffer.strip().endswith(">"):
            break
      except socket.timeout:
        break
    return buffer

  initial = read_until_prompt()

  for op in opcodes:
    client.sendall((op + "\r\n").encode("utf-8"))
    time.sleep(0.1)
    response = read_until_prompt()
    print(response)

finally:
  try:
    client.close()
  except:
    pass
  if qemu_process.poll() is None:
    qemu_process.terminate()
    qemu_process.wait()