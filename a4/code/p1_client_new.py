import argparse
import socket
import struct

DOWNLOAD_FILE_NAME = "downloaded_file.txt"


class Client:
    def __init__(self, server_ip, server_port, pref_outfile, download_file_name):

        # Constants
        # Maximum Segment Size
        self.MSS = 1
        # Buffer Size
        self.BUFFER_SIZE = self.MSS + 1000

        self.server_ip = server_ip
        self.server_port = server_port
        self.pref_outfile = pref_outfile

        # Initialize UDP socket
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set timeout for server response
        self.client_socket.settimeout(2)

        # Output File
        self.output_filename = f"{pref_outfile}_{download_file_name}"
        self.eof_recieved = False
        self.receive_file()

    def receive_file(self):
        """
        Receive the file from the server with reliability, handling packet loss
        and reordering.
        """
        # Process Variables
        self.buffer = {}
        self.expected_ack_num = 0

        with open(self.output_filename, "wb") as download_file:

            # Ping Server to Send File
            while True:
                try:
                    print(f"{self.server_ip}:{self.server_port} /GET")
                    self.client_socket.sendto(
                        "GET".encode(), (self.server_ip, self.server_port)
                    )
                    print("Downloading file from server")
                    packet, _ = self.client_socket.recvfrom(self.BUFFER_SIZE)
                    self.process_packet(
                        packet,
                        download_file,
                    )
                    break
                except socket.timeout:
                    continue

            # Recieve File
            while True:
                try:
                    packet, _ = self.client_socket.recvfrom(self.BUFFER_SIZE)
                    # deserialise the binary string into a json
                    # packet = json.loads(packet)
                    self.process_packet(
                        packet,
                        download_file,
                    )
                    if self.eof_recieved:
                        break
                except socket.timeout:
                    self.send_ack_to_server()

    def process_packet(self, packet, download_file):

        seq_to_be_acked = 0
        seq_num, data = self.parse_packet(packet)

        # EOF
        if data == b"EOF":
            seq_to_be_acked = seq_num
            self.handle_eof_recv()
        # Expected/Desired Packet
        elif seq_num == self.expected_ack_num:
            download_file.write(data)
            self.expected_ack_num += 1
            # Write Existing in Buffer
            while self.expected_ack_num in self.buffer:
                download_file.write(self.buffer.pop(self.expected_ack_num))
                self.expected_ack_num += 1
            seq_to_be_acked = self.expected_ack_num - 1
        # Out of Order Packet
        elif seq_num > self.expected_ack_num:
            print(
                f"Out of Order - Expected : {self.expected_ack_num}, Received:  {seq_num}"
            )
            if seq_num not in self.buffer:
                self.buffer[seq_num] = data
        else:
            print(f"Duplicate Packet - Seq: {seq_num}")
        return

        # Send Ack to Server
        self.send_ack_to_server(client_socket, seq_to_be_acked, server_ip, server_port)
        print(
            f"Recieves seq {seq_num}\t, ACK for seq {seq_to_be_acked}, Expecting seq {expected_ack_num}"
        )
        return expected_ack_num, buffer

    def send_ack_to_server(self):
        self.client_socket.sendto(
            self.expected_ack_num.to_bytes(4, "big"), (self.server_ip, self.server_port)
        )

    def parse_packet(self, packet):
        seq_length = struct.unpack("I", packet[:4])[0]
        seq_bytes = packet[4 : 4 + seq_length]
        seq = int.from_bytes(seq_bytes, "big")
        data = packet[4 + seq_length :]
        return seq, data

    def handle_eof_recv(self):
        self.eof_recieved = True
        self.client_socket.close()
        print("File downloaded successfully")

    def close_client(self):
        self.client_socket.close()
        print("Client Socket Closed")


def read_args():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Reliable file receiver over UDP.")
    parser.add_argument("server_ip", help="IP address of the server")
    parser.add_argument("server_port", type=int, help="Port number of the server")
    parser.add_argument("--pref_outfile", default="", help="Prefix for the output file")
    args = parser.parse_args()
    return (args.server_ip, args.server_port, args.pref_outfile)


if __name__ == "__main__":
    # Run the client
    client = Client(*read_args(), DOWNLOAD_FILE_NAME)
