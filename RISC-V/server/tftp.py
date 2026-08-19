import socket
import struct
import threading
import os

# --- CONFIGURE THESE PATHS ---
TAP0_IP = "192.168.1.100"      # The IP address of your Windows tap0 adapter
TFTP_ROOT = r"..\tftp"  # Folder where incoming files will be written

def handle_tftp_session(client_addr, opcode, filename):
    """
    Handles TFTP Read (RRQ=1) and Write (WRQ=2) operations.
    """
    clean_filename = filename.strip().replace('/', os.sep).replace('\\', os.sep)
    
    # 1. TRAP: If U-Boot sends a directory validation sweep, acknowledge it!
    if clean_filename.endswith(os.sep) or clean_filename == "dtb":
        print(f"[TFTP DIR-CHECK] Client {client_addr} validated path structure: '{filename}'")
        # Open an ephemeral socket to tell U-Boot the path is open and legal
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((TAP0_IP, 0))
        # Send an immediate ACK for block 0 to tell U-Boot the path is writeable
        ack_packet = struct.pack("!HH", 4, 0)
        sock.sendto(ack_packet, client_addr)
        sock.close()
        return

        # Resolve full target path mapping
    file_path = os.path.join(TFTP_ROOT, clean_filename)
    
    # !!! ADD THIS WINDOWS FILENAME SANITIZATION LAYER !!!
    # Extract the directory and the actual filename to isolate the text string
    directory_part = os.path.dirname(file_path)
    filename_part = os.path.basename(file_path)
    
    # Replace colons from the MAC address string with safe dashes so Windows accepts it
    safe_filename_part = filename_part.replace(':', '-')
    
    # Reassemble the final system path string
    file_path = os.path.join(directory_part, safe_filename_part)
    # -----------------------------------------------------

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Allocate session socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((TAP0_IP, 0))
    sock.settimeout(3.0)

    # --------------------------------------------------------------------------
    # CASE A: HANDLING AN OUTBOUND UPLOAD FROM VM (WRQ = 2)
    # --------------------------------------------------------------------------
    if opcode == 2:
        print(f"[TFTP WRITE] Receiving upload from client {client_addr} -> '{file_path}'")
        try:
            with open(file_path, "wb") as f:
                block_num = 0
                # Acknowledge the Write Request (ACK block 0) to kick off the stream
                sock.sendto(struct.pack("!HH", 4, block_num), client_addr)
                
                while True:
                    data, addr = sock.recvfrom(1024)
                    pack_op, pack_block = struct.unpack("!HH", data[:4])
                    
                    if pack_op == 3: # Data Packet
                        # Write raw block chunk bytes straight to disk
                        chunk = data[4:]
                        f.write(chunk)
                        
                        # Send matching lock-step block confirmation ACK
                        sock.sendto(struct.pack("!HH", 4, pack_block), client_addr)
                        block_num = pack_block
                        
                        # TFTP terminates when a packet is smaller than 512 bytes
                        if len(chunk) < 512:
                            print(f" -> [TFTP WRITE SUCCESS] Saved file: {file_path}")
                            break
        except socket.timeout:
            print(f" -> [TFTP WRITE TIMEOUT] Upload aborted for {filename}")
        except Exception as e:
            print(f" -> [TFTP WRITE EXCEPTION] {e}")

    # --------------------------------------------------------------------------
    # CASE B: HANDLING AN INBOUND DOWNLOAD TO VM (RRQ = 1)
    # --------------------------------------------------------------------------
    elif opcode == 1:
        if not os.path.exists(file_path):
            print(f" -> [TFTP READ ERROR] File not found: {file_path}")
            sock.close()
            return
            
        print(f"[TFTP READ] Streaming download to client {client_addr} -> '{filename}'")
        try:
            with open(file_path, "rb") as f:
                block_num = 1
                while True:
                    chunk = f.read(512)
                    data_packet = struct.pack("!HH", 3, block_num) + chunk
                    
                    for retry in range(5):
                        sock.sendto(data_packet, client_addr)
                        try:
                            ack_data, _ = sock.recvfrom(512)
                            ack_op, ack_block = struct.unpack("!HH", ack_data[:4])
                            if ack_op == 4 and ack_block == block_num:
                                break
                        except socket.timeout:
                            continue
                    else:
                        print(f" -> [TFTP READ TIMEOUT] Abandoned transfer of {filename}")
                        return

                    if len(chunk) < 512:
                        print(f" -> [TFTP READ SUCCESS] Sent file: {filename}")
                        break
                    block_num = (block_num + 1) & 0xFFFF
        except Exception as e:
            print(f" -> [TFTP READ EXCEPTION] {e}")

    sock.close()

def run_tftp_server():
    tftp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tftp_sock.bind((TAP0_IP, 69))
    print(f"Standalone Python TFTP Engine listening on {TAP0_IP}:69...")
    
    while True:
        try:
            data, addr = tftp_sock.recvfrom(2048) # Increased buffer size to catch full paths
            opcode = struct.unpack("!H", data[:2])[0]
            if opcode in (1, 2): # Accept Read (1) or Write (2) requests
                # Extract the entire string payload, clearing out extra nested null padding blocks
                raw_strings = data[2:].split(b'\x00')
                filename = raw_strings[0].decode('utf-8', errors='ignore').strip()

                
                
                # If U-Boot sent a path segment but the rest of the string contains the filename:
                if (filename == "dtb" or filename.endswith(os.sep)) and len(raw_strings) > 1:
                    next_part = raw_strings[1].decode('utf-8', errors='ignore').strip()
                    if next_part and next_part != "octet": # Skip the TFTP transfer mode string
                        filename = os.path.join(filename, next_part)

                threading.Thread(target=handle_tftp_session, args=(addr, opcode, filename), daemon=True).start()
        except Exception as e:
            print(f"[TFTP SERVER LOOP ERROR] {e}")


if __name__ == '__main__':
    run_tftp_server()
