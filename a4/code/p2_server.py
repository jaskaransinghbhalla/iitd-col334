import socket
import argparse


class Server():

    # server global variables
    MSS = 1
    ALPHA = 0.125
    BETA = 0.25

    DUP_ACK_THRESHOLD = 3

    WINDOW_SIZE = 1

    INITIAL_TIMEOUT = 1.0

    BUFFER_SIZE = 1000

    RETRY_BEFORE_QUIT = 10

    def __init__(self, server_ip, server_port, fast_recovery):
        self.server_ip = server_ip
        self.server_port = server_port
        self.fast_recovery = fast_recovery

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.server_ip, self.server_port))
        print(f"Server listening on \t{self.server_ip}:{self.server_port}")

        self.client_count = 0

        self.reset_session()
        self.listen_for_client()

    def reset_session(self):
        self.estimated_rtt = self.INITIAL_TIMEOUT
        self.dev_rtt = 0
        self.timeout = self.INITIAL_TIMEOUT

        # Client
        self.client_address = None
        self.LAF = -1
        self.LFS = -1
        self.all_packets_read = False
        self.duplicate_acks = {}
        self.packet_in_flight = {}
        self.packet_timestamps = {}

    def listen_for_client(self):
        try:
            request, client_address = self.server_socket.recvfrom(self.BUFFER_SIZE)
            print(f"Client connected on \t{client_address[0]}:{client_address[1]}")
            decoded_request = request.decode()

            if decoded_request == "GET":
                self.client_address = client_address
                print(f"Client requeste a file to download")
                self.send_file()
                print(f"Server closed...")
            else:
                print(f"Invalid request from client")
                return
        except Exception as e:
            print(f"Error: {e}")
            raise e
        
    def send_file(self):
        """
        Handles sending file to the client who has just connected on self.client_address
        """
        

# Parse command-line arguments
def read_args():
    parser = argparse.ArgumentParser(
        description="Reliable file transfer server over UDP."
    )
    parser.add_argument("server_ip", help="IP address of the server")
    parser.add_argument("server_port", type=int, help="Port number of the server")
    parser.add_argument("fast_recovery", help="Enable fast recovery")
    args = parser.parse_args()
    fast_recovery = args.fast_recovery
    if (
        fast_recovery == "0"
        or fast_recovery == "False"
        or fast_recovery == False
        or fast_recovery == 0
    ):
        return (args.server_ip, args.server_port, False)

    else:
        return (args.server_ip, args.server_port, True)


if __name__ == "__main__":
    server = Server(*read_args())