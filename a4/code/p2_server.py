import socket
import argparse
from utils import parse_packet, make_packet
import time

SERVER_FILE_PATH = "./test/test.txt"

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
                print(f"Client request a file to download")
                self.send_file()
                print(f"Server closed...")
            else:
                print(f"Invalid request from client")
                return
        except Exception as e:
            print(f"Error: {e}")
            raise e

    def get_file_read_offset(self):
        if self.LFS == -1 or self.LAF == -1:
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

    def get_retransmission_packets(self):
        start = self.LAF + 1
        end = self.LFS + 1
        retran_packets = []
        for seq in range(start, end):
            if time.time() - self.packet_timestamps[seq] >= self.timeout_interval:
                _, data = parse_packet(self.packet_in_flight[seq])
                retran_packets.append((seq, data))
        return retran_packets

    def send_packets_to_client(self, packets, retrans_packet=False):
        for seq, packet_data in packets:
            packet = make_packet(seq, packet_data)
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
        # print(f"Timeout interval : {self.timeout_interval}")

    def handle_ack_recv(self, ack_num):
        if ack_num > self.LFS + self.WINDOW_SIZE:
            return
        if ack_num <= self.LAF:
            return
        # Update ack condition
        self.LAF = ack_num - 1
        print(f"Cumulative ACK received: {ack_num}")

        # Calculate Sample RTT
        if self.LAF in self.packet_timestamps:
            self.update_time_interval(self.LAF)

        if ack_num in self.duplicate_acks:
            self.duplicate_acks[ack_num] += 1
        else:
            self.duplicate_acks[ack_num] = 1

        duplicate_ack_count = self.duplicate_acks[ack_num]

        if self.fast_recovery:
            if duplicate_ack_count >= self.DUP_ACK_THRESHOLD and ack_num != self.LAF:
                print(f"Fast recovery: Retransmitting seq {ack_num}")
                # Find the packet and retransmit
                seq = ack_num
                _, data = parse_packet(self.packet_in_flight[seq])
                packet = make_packet(seq, data)
                self.server_socket.sendto(packet, self.client_address)
                self.packet_timestamps[seq] = time.time()
                # self.duplicate_acks[ack_num] = 0
                return
        # print("Duplicate Acks", self.duplicate_acks)
        # Delete all the keys equal to and below ack_num
        for key in list(self.packet_timestamps.keys()):
            if key <= self.LAF:
                del self.packet_timestamps[key]
                del self.packet_in_flight[key]

    def send_eof(self):
        eof_packet = make_packet(self.LFS + 1, b"EOF")
        self.server_socket.sendto(eof_packet, self.client_address)

    def send_file(self):
        """
        Handles sending file to the client who has just connected on self.client_address
        """
        print("Sending file to client")
        with open(SERVER_FILE_PATH, "rb") as file:
            while True:
                print(f"LAF: {self.LAF}, LFS: {self.LFS}")

                packets_to_send = self.read_data_from_file(f)
                self.send_packets_to_client(packets_to_send)

                # Wait for ACK
                try:
                    ack, _ = self.server_socket.recvfrom(self.BUFFER_SIZE)
                    ack_num = int(ack.decode())
                    self.handle_ack_recv(ack_num)

                except socket.timeout:
                    print("Timeout occurred while waiting for ACK.")
                    continue

                packets_to_retransmit = self.get_retransmission_packets()
                self.send_packets_to_client(packets_to_retransmit, retrans_packet=True)

                if self.all_packets_read and self.LAF == self.LFS:
                    eof_counter = 0
                    while eof_counter < self.RETRY_BEFORE_QUIT:
                        self.send_eof()
                        eof_counter = eof_counter + 1
                        print(f"Trying for {eof_counter} time. EOF sent")
                        try:
                            ack, _ = self.server_socket.recvfrom(self.BUFFER_SIZE)
                            ack_num = int.from_bytes(ack, "big")
                            if ack_num == self.LAF + 2:
                                print("Final ack", ack_num)
                                break
                        
                        except socket.timeout:
                            print("Timeout occurred while waiting for EOF ACK.")
                            continue
                    
                    self.client_count += 1
                    print(f"File sent ")


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