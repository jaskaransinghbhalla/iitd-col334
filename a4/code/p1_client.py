import socket
import argparse

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
    while True:
        try : 
            client_socket.sendto("GET".encode(), (server_ip, server_port))
            packet, _ = client_socket.recvfrom(BUFFER_SIZE)
        except client_socket.timeout :
            continue


    # Processing packets from server
    # server_address = (server_ip, server_port)


args = parser.parse_args()
print(args.pref_outfile)

# Run the client
receive_file(args.server_ip, args.server_port, args.pref_outfile)
