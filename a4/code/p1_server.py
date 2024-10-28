import socket
import time
import argparse

# Constants
MSS = 1400  # Maximum Segment Size for each packet
# Check Window Size later on
WINDOW_SIZE = 5  # Number of packets in flight
DUP_ACK_THRESHOLD = 3  # Threshold for duplicate ACKs to trigger fast recovery
FILE_PATH = ""
TIMEOUT = 1.0  # Initialize timeout to some value but update it as ACK packets arrive

BUFFER_SIZE = 1000  # 64


def send_file(server_ip, server_port, enable_fast_recovery):
    """
    Send a predefined file to the client, ensuring reliability over UDP.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((server_ip, server_port))

    print(f"Server listening on {server_ip}:{server_port}")

    # Wait for client to initiate connection
    client_address = None
    file_path = FILE_PATH  # Predefined file name

    while True:
        # Receive file request from client
        request, client_address = server_socket.recvfrom(BUFFER_SIZE)
        print("Client Connected :", client_address)
        print("Request : ", request.decode())


# Parse command-line arguments
parser = argparse.ArgumentParser(description="Reliable file transfer server over UDP.")
parser.add_argument("server_ip", help="IP address of the server")
parser.add_argument("server_port", type=int, help="Port number of the server")
parser.add_argument("fast_recovery", type=int, help="Enable fast recovery")

args = parser.parse_args()

# Run the server
send_file(args.server_ip, args.server_port, args.fast_recovery)
