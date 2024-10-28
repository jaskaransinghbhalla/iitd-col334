import socket
import argparse
import time
import json

# Constants
MSS = 1400  # Maximum Segment Size
BUFFER_SIZE = MSS + 1000
# Parse command-line arguments
parser = argparse.ArgumentParser(description="Reliable file receiver over UDP.")
parser.add_argument("server_ip", help="IP address of the server")
parser.add_argument("server_port", type=int, help="Port number of the server")
parser.add_argument("--pref_outfile", default="", help="Prefix for the output file")


def receive_file(server_ip, server_port, pref_outfile):
    """
    Receive the file from the server with reliability, handling packet loss
    and reordering.
    """
    # Initialize UDP socket

    ## Add logic for handling packet loss while establishing connection
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(2)  # Set timeout for server response


    output_filename = f"{pref_outfile}_received.bin"
    
    expected_ack_num = 0
    buffer = {}

    has_request_sent = False

    with open(output_filename, "wb") as f:
        while True:
            try:
                if not has_request_sent:
                    print("Sending GET request to server...")
                    client_socket.sendto("GET".encode(), (server_ip, server_port))
                    packet, _ = client_socket.recvfrom(BUFFER_SIZE)
            except socket.timeout:
                continue

            has_request_sent = True

            try:
                if has_request_sent:
                    packet, _ = client_socket.recvfrom(BUFFER_SIZE)

                # deserialise the binary string into a json
                packet = json.loads(packet)
                print("DEBUG, packet: ", packet)

                seq_num = packet["seq"]
                data = packet["data"]

                if data == b'EOF':
                    print("File tranmission completed")
                    break
                
                if seq_num == expected_ack_num:
                    f.write(data)
                    expected_ack_num += 1

                    while expected_ack_num in buffer:
                        f.write(buffer.pop(expected_ack_num))
                        expected_ack_num += 1

                    ack_num = expected_ack_num
                    client_socket.sendto(ack_num.to_bytes(4, 'big'), (server_ip, server_port))
                    print(f"ACK sent for sequence {ack_num}")
                
                elif seq_num > expected_ack_num:
                    if seq_num not in buffer:
                        buffer[seq_num] = data
                    client_socket.sendto(expected_ack_num.to_bytes(4, 'big'), (server_ip, server_port))
                    print(f"Out-of-order packet {seq_num} received, expecting {expected_ack_num}.")
                
            except socket.timeout:
                print("Waiting for packets...")
                client_socket.sendto(expected_ack_num.to_bytes(4, 'big'), (server_ip, server_port))

args = parser.parse_args()
print(args.pref_outfile)

# Run the client
receive_file(args.server_ip, args.server_port, args.pref_outfile)
