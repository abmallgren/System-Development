import socket
import struct

def build_dhcp_reply(msg_type, xid, client_mac, offered_ip, server_ip, tftp_ip):
    """
    Constructs a perfectly aligned, strict DHCP binary packet for U-Boot.
    The boot_file (Option 67) parameter has been completely removed.
    """
    op = 2          # Boot Reply
    htype = 1       # Ethernet
    hlen = 6        # MAC length
    hops = 0
    secs = 0
    flags = 0x8000  # Broadcast flag (critical for unconfigured bootloaders)

    ciaddr = socket.inet_aton("0.0.0.0")
    yiaddr = socket.inet_aton(offered_ip)
    siaddr = socket.inet_aton(tftp_ip)    # Next Server IP (TFTP IP)
    giaddr = socket.inet_aton("0.0.0.0")

    # Pad the MAC hardware address to exactly 16 bytes
    chaddr = client_mac + b'\x00' * 10
    
    sname = b'\x00' * 64
    # The legacy 128-byte BOOTP boot file field is filled with nulls to clear overrides
    file = b'\x00' * 128

    # Fixed 236-byte BOOTP/DHCP header
    packet_header = struct.pack(
        '!BBBBIHH4s4s4s4s16s64s128s',
        op, htype, hlen, hops, xid, secs, flags,
        ciaddr, yiaddr, siaddr, giaddr, chaddr, sname, file
    )

    magic_cookie = b'\x63\x82\x53\x63'

    # Option 66 must be an ASCII string length field
    tftp_str_bytes = tftp_ip.encode('utf-8')
    opt66 = b'\x42' + bytes([len(tftp_str_bytes)]) + tftp_str_bytes

    options = [
        bytes([53, 1, msg_type]),                        # Option 53: DHCP Msg Type (2=Offer, 5=Ack)
        b'\x36\x04' + socket.inet_aton(server_ip),       # Option 54: Server ID Identifier
        b'\x01\x04' + socket.inet_aton("255.255.255.0"), # Option 1: Subnet Mask
        b'\x33\x04\x00\x01\x51\x80',                     # Option 51: Lease Time (86400s)
        b'\x03\x04' + socket.inet_aton(server_ip),       # Option 3: Default Gateway Router
        opt66,                                           # Option 66: TFTP Server Text Name
        b'\xff'                                          # End Option marker
    ]

    return packet_header + magic_cookie + b''.join(options)

def run_dhcp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    # !!! Ensure this matches your EXACT static Windows tap0 adapter IP !!!
    TAP0_IP = "192.168.1.100" 
    server.bind((TAP0_IP, 67))

    print(f"Python DHCP Engine listening on {TAP0_IP}:67...")

    while True:
        data, addr = server.recvfrom(2048)
        
        # Unpack message type headers
        op, htype, hlen, hops, xid = struct.unpack('!BBBBI', data[:8])
        client_mac = data[28:34]
        mac_str = ':'.join(f'{b:02x}' for b in client_mac)

        # Parse out the internal DHCP Message Type option byte (Option 53)
        msg_type = 1
        try:
            idx = data.find(b'\x35\x01')
            if idx != -1:
                msg_type = data[idx + 2]
        except Exception:
            pass

        assigned_ip = "192.168.1.99"

        if msg_type == 1:
            print(f"\n[DHCP DISCOVER] Received from MAC: {mac_str} (XID: {hex(xid)})")
            # Removed target_file argument mapping
            reply = build_dhcp_reply(2, xid, client_mac, assigned_ip, TAP0_IP, TAP0_IP)
            server.sendto(reply, ('255.255.255.255', 68))
            print(f" -> Sent [DHCP OFFER] -> {assigned_ip}")

        elif msg_type == 3:
            print(f"\n[DHCP REQUEST] Received from MAC: {mac_str} (XID: {hex(xid)})")
            # Removed target_file argument mapping
            reply = build_dhcp_reply(5, xid, client_mac, assigned_ip, TAP0_IP, TAP0_IP)
            server.sendto(reply, ('255.255.255.255', 68))
            print(f" -> Sent [DHCP ACK] -> Handshake Complete!")

if __name__ == '__main__':
    run_dhcp_server()
