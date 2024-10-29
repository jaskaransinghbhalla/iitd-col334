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
    WINDOW_SIZE = 3
    # Initial timeout value, # Initialize timeout to some value but update it as ACK packets arrive
    INITIAL_TIMEOUT = 1.0
    # Buffer size for receiving packets
    BUFFER_SIZE = 1000  # 64

    def __init__(self, server_ip, server_port, fast_recovery):
        self.server_ip = server_ip
        self.server_port = server_port
        self.fast_recovery = fast_recovery
        # Server Socket Creation
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.server_ip, self.server_port))
        print(f"Server listening on \t{self.server_ip}:{self.server_port}")
        # Client
        self.client_address = None
        # RTT Variables
        self.estimated_rtt = self.INITIAL_TIMEOUT
        self.dev_rtt = 0.0
        self.timeout_interval = self.estimated_rtt + 4 * self.dev_rtt
        # Start listening for clients
        while True:
            self.packet_timestamps = {}
            self.listen_for_client()

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
        self.file_sent = False
        # Assume the sequence number starts from 1
        with open(SERVER_FILE_PATH, "rb") as f:
            while True:
                print(f"LAF: {self.LAF}, LFS: {self.LFS}")

                # 1 - Determine the packets to be sent
                packets_to_send = self.read_data_from_file(f)
                print(f"Packets to send: {packets_to_send}")
                # 2 - Send the Packets
                self.send_packets_to_client(packets_to_send)
                # 3 - Wait for the Acknowledgement
                # 4 - Update the window
                self.LFS = packets_to_send[-1][0]
                self.LAF = packets_to_send[-1][0]
                # 5 - Check if the file is sent
                if self.file_sent and self.LAF == self.LFS:
                    print("File sent successfully.")
                    break

    def send_packets_to_client(self, packets):
        for seq, packet_data in packets:
            # Retransmission due to timeout
            # Normal Sending
            packet = self.make_packet(seq, packet_data)
            self.server_socket.sendto(packet, self.client_address)
            print(f"Sent seq {seq} ")

    def read_data_from_file(self, file):
        # create a packets object of size WINDOW_SIZE
        packets = []
        # Read the file from the current LFS * MSS position
        file_read_offset = self.get_file_read_offset()
        file.seek(file_read_offset)
        for i in range(self.WINDOW_SIZE):
            seq_no = self.LFS + i + 1
            data = file.read(self.MSS)
            if not data:
                self.file_sent = True
                packets.append((seq_no, b"EOF"))
                break
            else:
                packets.append((seq_no, data))
                self.packet_timestamps[seq_no] = time.time()
        return packets

    def get_file_read_offset(self):
        if self.LFS == -1:
            return 0
        return self.LFS * self.MSS + 1

    def update_time_interval(self, ack_num):
        sample_rtt = time.time() - self.packet_timestamps[ack_num]
        # Update EstimatedRTT and DevRTT
        estimated_rtt = (1 - self.ALPHA) * estimated_rtt + self.ALPHA * sample_rtt
        dev_rtt = (1 - self.BETA) * dev_rtt + self.BETA * abs(
            sample_rtt - estimated_rtt
        )
        timeout_interval = estimated_rtt + 4 * dev_rtt
        return timeout_interval

    def make_packet(self, seq, data):
        seq_bytes = seq.to_bytes((seq.bit_length() + 7) // 8, byteorder="big")
        seq_length = len(seq_bytes)
        serialised_data = struct.pack("I", seq_length) + seq_bytes + data
        return serialised_data


def send_file(server_ip, server_port, enable_fast_recovery):
    """
    Send a predefined file to the client, ensuring reliability over UDP.
    """

    while True:
        # Open file and initialize sliding window pointers
        with open(FILE_PATH, "rb") as f:
            # Last Acknowledged Frame
            LAF = -1
            # Last Frame Sent
            LFS = -1
            # Session Variables
            duplicate_acks = {}
            file_sent = False
            packet_timestamps = {}
            packets = []

            while True:

                k = 0
                while k < WINDOW_SIZE and not file_sent:
                    LFS += 1
                    data = f.read(MSS)
                    if not data:
                        file_sent = True
                        packets.append((LFS, b"EOF"))
                        break
                    packets.append((LFS, data))
                    packet_timestamps[LFS] = time.time()
                    k = k + 1

                # while LFS < LAF + WINDOW_SIZE and not file_sent:
                #     LFS += 1
                #     data = f.read(MSS)
                #     packets.append((LFS, data))
                #     packet_timestamps[LFS] = time.time()
                # if not data:

                for seq, packet_data in packets:

                    if time.time() - packet_timestamps[seq] >= timeout_interval:
                        packet = seq.to_bytes(4, "big") + packet_data
                        packet = make_packet(seq, packet_data)
                        server_socket.sendto(packet, client_address)
                        packet_timestamps[seq] = time.time()
                        print(f"Packet {seq} retransmitted due to timeout.")
                    else:
                        packet = make_packet(seq, packet_data)
                        server_socket.sendto(packet, client_address)
                        print(f"Sent seq {seq} ")
                # 3 - Wait for the Acknowledgement
                try:
                    # Wait for acknowledgment
                    ack, _ = server_socket.recvfrom(BUFFER_SIZE)
                    ack_num = int.from_bytes(ack, "big")
                    print(f"Cumulative ACK received: {ack_num}")

                    # Calculate SampleRTT
                    if ack_num in packet_timestamps:
                        timeout_interval = update_time_interval()

                        # print(f"Timeout interval updated to {timeout_interval}")

                    # Fast retransmit mode: Check for duplicate ACKs
                    if enable_fast_recovery:
                        if ack_num in duplicate_acks:
                            duplicate_acks[ack_num] += 1
                        else:
                            duplicate_acks[ack_num] = 1

                        # Retransmit if 3 duplicate ACKs are received
                        if duplicate_acks[ack_num] == 3 and ack_num < LFS:
                            print(f"Fast recovery: Retransmitting packet {ack_num}")
                            # Find the packet and retransmit
                            for seq, packet_data in packets:
                                if seq == ack_num:
                                    # packet = seq.to_bytes(4, 'big') + packet_data
                                    packet_json = {"seq": seq, "data": packet_data}

                                    # serialise packet_json into a binary string
                                    # packet = json.dumps(packet_json).encode()
                                    packet = make_packet(seq, packet_data)
                                    server_socket.sendto(packet, client_address)

                                    packet_timestamps[seq] = time.time()
                                    break

                    # Slide the window up to the latest cumulative ACK
                    if ack_num > LAF:
                        LAF = ack_num
                        # Remove acknowledged packets from the window and timestamps
                        packets = [(seq, data) for seq, data in packets if seq > LAF]
                        packet_timestamps = {
                            seq: ts
                            for seq, ts in packet_timestamps.items()
                            if seq > LAF
                        }

                        duplicate_acks = {
                            seq: count
                            for seq, count in duplicate_acks.items()
                            if seq > LAF
                        }

                except socket.timeout:
                    print("Timeout occurred while waiting for ACK.")
                    continue

                if file_sent and LAF == LFS:
                    print("File sent successfully.")
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
