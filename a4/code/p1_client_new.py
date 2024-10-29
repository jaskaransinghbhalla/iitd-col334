import argparse
import socket
import struct

# Constants
# Maximum Segment Size
MSS = 1400
# Buffer Size
BUFFER_SIZE = MSS + 1000
# Output File
OUTPUT_FILE = "out.bin"


def parse_packet(packet):
    seq_length = struct.unpack("I", packet[:4])[0]
    seq_bytes = packet[4 : 4 + seq_length]
    seq = int.from_bytes(seq_bytes, "big")
    data = packet[4 + seq_length :]
    return seq, data


def receive_file(server_ip, server_port, pref_outfile):
    """
    Receive the file from the server with reliability, handling packet loss
    and reordering.
    """
    # Initialize UDP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set timeout for server response
    client_socket.settimeout(2)

    # Output File
    output_filename = f"{pref_outfile}_{OUTPUT_FILE}"

    # Process Variables
    buffer = {}
    expected_ack_num = 0

    with open(output_filename, "wb") as f:

        # Ping Server to Send File
        while True:
            try:
                print(f"{server_ip}:{server_port} /GET")
                client_socket.sendto("GET".encode(), (server_ip, server_port))
                packet, _ = client_socket.recvfrom(BUFFER_SIZE)
                print("Downloading file from server")
                expected_ack_num, buffer = process_packet(
                    packet,
                    buffer,
                    client_socket,
                    server_ip,
                    server_port,
                    f,
                    expected_ack_num,
                )
                break
            except socket.timeout:
                continue

        # Recieve File
        while True:
            try:
                packet, _ = client_socket.recvfrom(BUFFER_SIZE)
                # deserialise the binary string into a json
                # packet = json.loads(packet)
                result = process_packet(
                    packet,
                    buffer,
                    client_socket,
                    server_ip,
                    server_port,
                    f,
                    expected_ack_num,
                )
                if result is not None:
                    expected_ack_num, buffer = result
                else:
                    break
            except socket.timeout:
                send_ack_to_server(
                    client_socket, expected_ack_num, server_ip, server_port
                )


def process_packet(
    packet, buffer, client_socket, server_ip, server_port, f, expected_ack_num
):
    seq_to_be_acked = 0
    seq_num, data = parse_packet(packet)
    # EOF
    if data == b"EOF":
        seq_to_be_acked = seq_num
        handle_EOF_recv()
        return None
    # Expected/Desired Packet
    elif seq_num == expected_ack_num:
        f.write(data)
        expected_ack_num += 1
        # Write Existing in Buffer
        while expected_ack_num in buffer:
            f.write(buffer.pop(expected_ack_num))
            expected_ack_num += 1
        seq_to_be_acked = expected_ack_num - 1
    # Out of Order Packet
    elif seq_num > expected_ack_num:
        print(f"Out of Order - Expected : {expected_ack_num}, Received:  {seq_num}")
        if seq_num not in buffer:
            buffer[seq_num] = data
    else :
        return expected_ack_num, buffer

    # Send Ack to Server
    send_ack_to_server(client_socket, seq_to_be_acked, server_ip, server_port)
    print(f"Recieves seq {seq_num}\t, ACK for seq {seq_to_be_acked}, Expecting seq {expected_ack_num}")
    return expected_ack_num, buffer


def send_ack_to_server(client_socket, expected_ack_num, server_ip, server_port):
    client_socket.sendto(expected_ack_num.to_bytes(4, "big"), (server_ip, server_port))


def handle_EOF_recv():
    # To be Completed
    print("File downloaded successfully")


def read_args():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Reliable file receiver over UDP.")
    parser.add_argument("server_ip", help="IP address of the server")
    parser.add_argument("server_port", type=int, help="Port number of the server")
    parser.add_argument("--pref_outfile", default="", help="Prefix for the output file")
    args = parser.parse_args()
    return (args.server_ip, args.server_port, args.pref_outfile)


# Run the client
receive_file(*read_args())
