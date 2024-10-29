import socket
import time
import argparse
import struct

# SERVER_FILE_PATH = "./test/test_10KB.bin"
SERVER_FILE_PATH = "./test/test.txt"


class Server:
    # Maximum Segment Size for each packet
    MSS = 1
    # MSS = 1400
    ALPHA = 0.125
    BETA = 0.25
    # Threshold for duplicate ACKs to trigger fast recovery
    DUP_ACK_THRESHOLD = 3
    # Number of packets in flight
    WINDOW_SIZE = 4
    # Initial timeout value, # Initialize timeout to some value but update it as ACK packets arrive
    INITIAL_TIMEOUT = 1.0
    # Buffer size for receiving packets
    BUFFER_SIZE = 1000  # 64
    # Packets in flight

    def __init__(self, server_ip, server_port, fast_recovery):
        self.server_ip = server_ip
        self.server_port = server_port
        self.fast_recovery = fast_recovery
        # Server Socket Creation
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.server_ip, self.server_port))
        print(f"Server listening on \t{self.server_ip}:{self.server_port}")

        # Start listening for clients
        self.client_count = 0

        while True:
            self.reset_session()
            self.listen_for_client()

    def reset_session(self):
        # RTT Variables
        self.estimated_rtt = self.INITIAL_TIMEOUT
        self.dev_rtt = 0.0
        self.timeout_interval = self.estimated_rtt + 4 * self.dev_rtt
        # Client
        self.client_address = None
        self.LAF = -1
        self.LFS = -1
        self.duplicate_acks = {}
        self.all_packets_read = False
        self.packet_timestamps = {}
        self.packet_in_flight = {}

    def listen_for_client(self):
        # Client Connection
        try:
            # Receive file request from client
            request, client_address = self.server_socket.recvfrom(self.BUFFER_SIZE)
            print(f"Client connected on \t{client_address[0]}:{client_address[1]}")
            decoded_request = request.decode()
            if decoded_request == "GET":
                self.client_address = client_address
                print(f"Client Requested a file download")
                self.send_file()
        except Exception as e:
            print(f"Error: {e}")
            return

    def update_time_interval(self, ack_num):
        sample_rtt = time.time() - self.packet_timestamps[ack_num]
        # Update EstimatedRTT and DevRTT
        self.estimated_rtt = (
            1 - self.ALPHA
        ) * self.estimated_rtt + self.ALPHA * sample_rtt
        self.dev_rtt = (1 - self.BETA) * self.dev_rtt + self.BETA * abs(
            sample_rtt - self.estimated_rtt
        )
        self.timeout_interval = self.estimated_rtt + 4 * self.dev_rtt
        print(f"Timeout interval : {self.timeout_interval}")

    def make_packet(self, seq, data):
        seq_bytes = seq.to_bytes((seq.bit_length() + 7) // 8, byteorder="big")
        seq_length = len(seq_bytes)
        serialised_data = struct.pack("I", seq_length) + seq_bytes + data
        return serialised_data

    def get_file_read_offset(self):
        if self.LFS == -1:
            return 0
        return self.LFS * self.MSS + 1

    def read_data_from_file(self, file):
        # create a packets object of size WINDOW_SIZE
        self.all_packets_read = False
        packets = []
        # Read the file from the current LFS * MSS position
        file_read_offset = self.get_file_read_offset()
        file.seek(file_read_offset)

        packet_range_min = 0
        packet_range_max = self.WINDOW_SIZE

        if self.LAF != -1:
            packet_range_min = self.LFS + 1
            packet_range_max = self.LAF + self.WINDOW_SIZE + 1

        # Sender
        i = packet_range_min
        while i < packet_range_max:
            seq_no = i
            data = file.read(self.MSS)
            if not data:
                self.all_packets_read = True
                break
            else:
                packets.append((seq_no, data))
                self.packet_timestamps[seq_no] = time.time()
            i += 1
        return packets

    def send_packets_to_client(self, packets, retrans_packet=False):
        for seq, packet_data in packets:
            packet = self.make_packet(seq, packet_data)
            self.server_socket.sendto(packet, self.client_address)
            self.packet_timestamps[seq] = time.time()
            self.packet_in_flight[seq] = packet
            # Retransmission due to timeout
            if retrans_packet:
                print(f"Packet {seq} retransmitted due to timeout.")
            else:
                # Normal Sending
                self.LFS = seq
                print(f"Sent seq {seq} ")

    def send_eof(self):
        eof_packet = self.make_packet(self.LFS + 1, b"EOF")
        self.server_socket.sendto(eof_packet, self.client_address)
        print("EOF sent to client")

    def get_retransmission_packets(self):
        start = self.LAF + 1
        end = self.LFS + 1
        retran_packets = []
        for seq in range(start, end):
            if time.time() - self.packet_timestamps[seq] >= self.timeout_interval:
                retran_packets.append(self.packet_in_flight[seq])
        return retran_packets

    def get_fast_retransmission_packets(self):
        pass

    def handle_ack_recv(self, ack_num):

        # Update ack condition
        self.LAF = ack_num
        print(f"Cumulative ACK received: {ack_num}")

        # Calculate Sample RTT
        if ack_num in self.packet_timestamps:
            self.update_time_interval(ack_num)

        if self.fast_recovery:
            duplicate_ack_count = self.duplicate_acks.get(ack_num, 0)
            if duplicate_ack_count >= self.DUP_ACK_THRESHOLD:
                print(f"Fast recovery: Retransmitting packet {ack_num+1}")
                # Find the packet and retransmit
                for seq, packet_data in self.packet_in_flight.items():
                    if seq == ack_num + 1:
                        packet = self.make_packet(seq, packet_data)
                        self.server_socket.sendto(packet, self.client_address)
                        self.packet_timestamps[seq] = time.time()
                        return

        # Delete all the keys equal to and below ack_num
        for key in list(self.packet_timestamps.keys()):
            if key <= self.LAF:
                if key in self.packet_timestamps:
                    del self.packet_timestamps[key]
                if key in self.packet_in_flight:
                    del self.packet_in_flight[key]
                if self.fast_recovery:
                    if key in self.duplicate_acks:
                        del self.duplicate_acks[key]

    def send_file(self):
        """
        Send a predefined file to the client, ensuring reliability over UDP.
        """
        print("Sending file to client")
        # Initialize Client Variables
        self.LAF = -1
        self.LFS = -1
        # Session Variables
        self.duplicate_acks = {}
        self.all_packets_read = False
        # Assume the sequence number starts from 1
        with open(SERVER_FILE_PATH, "rb") as f:
            while True:
                print(f"LAF: {self.LAF}, LFS: {self.LFS}")

                # 1 - Determine the packets to be sent
                packets_to_retransmit = self.get_retransmission_packets()
                packets_to_send = self.read_data_from_file(f)
                # 2 - Send the Packets
                self.send_packets_to_client(packets_to_retransmit, retrans_packet=True)
                self.send_packets_to_client(packets_to_send)
                # 3 - Wait for the Acknowledgement
                try:
                    ack, _ = self.server_socket.recvfrom(self.BUFFER_SIZE)
                    ack_num = int.from_bytes(ack, "big")
                    self.handle_ack_recv(ack_num)
                except socket.timeout:
                    print("Timeout occurred while waiting for ACK.")
                    continue

                # 4 - Check if the file is sent
                if self.all_packets_read and self.LAF == self.LFS:
                    self.send_eof()
                    self.client_count += 1

                    print(f"File sent successfully {self.client_count} times.")
                    break


# Parse command-line arguments
def read_args():
    parser = argparse.ArgumentParser(
        description="Reliable file transfer server over UDP."
    )
    parser.add_argument("server_ip", help="IP address of the server")
    parser.add_argument("server_port", type=int, help="Port number of the server")
    parser.add_argument("fast_recovery", type=bool, help="Enable fast recovery")
    args = parser.parse_args()
    return (args.server_ip, args.server_port, args.fast_recovery)


if __name__ == "__main__":
    # Run the server
    server = Server(*read_args())
