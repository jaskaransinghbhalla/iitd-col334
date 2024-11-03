import socket
import time
import argparse
from utils import make_packet, parse_packet

SERVER_FILE_PATH = "./test/test_10KB.bin"
# SERVER_FILE_PATH = "./test/test_1MB.bin"
# SERVER_FILE_PATH = "./test/test_10MB.bin"
# SERVER_FILE_PATH = "./test/test_100MB.bin"


class Server:
    # Maximum Segment Size for each packet (in bytes)
    MSS = 1400

    ALPHA = 0.125
    BETA = 0.25
    # Threshold for duplicate ACKs to trigger fast recovery
    DUP_ACK_THRESHOLD = 3
    # Number of packets in flight
    WINDOW_SIZE = 1
    # Initial timeout value, # Initialize timeout to some value but update it as ACK packets arrive
    INITIAL_TIMEOUT = 1.0
    # Buffer size for receiving packets
    BUFFER_SIZE = 1000  # 64
    # Packets in flight
    RETRY_BEFORE_QUIT = 10

    MAX_RATE = 10000 # 

    # define an enum with values SS, CA, and FR
    # STATES = ["SS", "CA", "FR"]
    # 0 = SS
    # 1 = CA
    # 2 = FR

    def __init__(self, server_ip, server_port, fast_retransmit):
        self.server_ip = server_ip
        self.server_port = server_port
        self.fast_retransmit = fast_retransmit
        # Server Socket Creation
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.server_ip, self.server_port))
        print(f"Server listening on \t{self.server_ip}:{self.server_port}")

        # Start listening for clients
        self.client_count = 0

        # state is a string value
        self.state = "SS"
        self.cwnd = self.MSS
        self.ssthresh = 64000 # 64kb (default value)

        # while True:
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
        self.all_packets_read = False
        self.duplicate_acks = {}
        self.packet_in_flight = {}
        self.packet_timestamps = {}
        self.dup_ack_count = 0

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
                start_time = time.time()
                self.send_file()
                end_time = time.time()
                print(f"Time taken to send file: {end_time - start_time}s")
                print(f"Server closed...")
            else:
                print("Invalid request from client")
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
        packet_range_max = self.cwnd

        if self.LAF != -1:
            packet_range_min = self.LFS + 1
            packet_range_max = self.LAF + self.cwnd + 1

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
        if ack_num > self.LFS + min(self.WINDOW_SIZE, self.cwnd):
            return
        if ack_num <= self.LAF:
            return
        # Update ack condition
        self.LAF = ack_num - 1
        print(f"Cumulative ACK received: {ack_num}")

        # Calculate Sample RTT
        # if self.LAF in self.packet_timestamps:
        #     self.update_time_interval(self.LAF)

        if ack_num in self.duplicate_acks:
            self.duplicate_acks[ack_num] += 1
        else:
            self.duplicate_acks[ack_num] = 1

        duplicate_ack_count = self.duplicate_acks[ack_num]
        
        is_new_ack = ack_num not in self.duplicate_acks
        
        if is_new_ack:
            # Reset duplicate ACK count
            self.dup_ack_count = 0
            self.update_cwnd_on_ack(ack_num, is_new_ack)
        else:
            self.dup_ack_count += 1
            print(f"Duplicate ACK count: {self.dup_ack_count}")
            if self.dup_ack_count == 3 and self.state != "FR":
                # Enter FR on 23 duplicate ACKs
                self.ssthreh = max(self.cwnd // 2, self.MSS)
                self.cwnd = self.ssthresh + 3 * self.MSS
                self.state = "FR"
            elif self.state == "FR":
                self.update_cwnd_on_ack(ack_num, is_new_ack)
            
        if self.fast_retransmit:
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

    def update_cwnd_on_ack(self, ack_num, is_new_ack):
        """
        Update the congestion window size based on the state of the sender.
        """
        if self.state == "SS":
            # Slow Start: cwnd doubles each RTT
            self.cwnd += self.MSS
            print(f"In Slow Start: Increased cwnd to {self.cwnd}")

            # Transition to Congestion Avoidance if cwnd exceeds ssthresh
            if self.cwnd >= self.ssthresh:
                self.state = "CA"
                print("Transition to Congestion Avoidance (CA)")
        elif self.state == "CA":
            # Congestion Avoidance: cwnd increases linearly
            self.cwnd += self.MSS * (self.MSS // self.cwnd)
            print(f"In Congestion Avoidance: Increased cwnd to {self.cwnd}")
        elif self.state == "FR":
            if is_new_ack:
                # Exit fast recovery on new ACK
                self.cwnd = self.ssthresh
                self.state = "CA"
                self.dup_ack_count = 0
                print("Exiting Fast Recovery: cwnd set to ssthresh")
            else:
                self.cwnd += self.MSS
                print(f"In fast recovery: Increased cwnd to {self.cwnd}")
            
    def send_eof(self):
        eof_packet = make_packet(self.LFS + 1, b"EOF")
        self.server_socket.sendto(eof_packet, self.client_address)

    def send_file(self):
        """
        Send a predefined file to the client, ensuring reliability over UDP.
        """
        print("Sending file to client")
        # Assume the sequence number starts from 1
        with open(SERVER_FILE_PATH, "rb") as f:
            while True:
                print(f"LAF: {self.LAF}, LFS: {self.LFS}")

                # 1 - Determine the packets to be sent
                packets_to_send = self.read_data_from_file(f)
                # 2 - Send the Packets
                self.send_packets_to_client(packets_to_send)

                # 3 - Wait for the Acknowledgement
                try:
                    ack, _ = self.server_socket.recvfrom(self.BUFFER_SIZE)
                    ack_num = int.from_bytes(ack, "big")
                    self.handle_ack_recv(ack_num)
                except socket.timeout:
                    print(f"Timeout occurred while waiting for ACK in {self.state} state")
                    self.ssthresh = self.cwnd // 2
                    self.cwnd = 1 * self.MSS
                    self.dup_ack_count = 0
                    continue

                packets_to_retransmit = self.get_retransmission_packets()
                self.send_packets_to_client(packets_to_retransmit, retrans_packet=True)

                # 4 - Check if the file is sent
                if self.all_packets_read and self.LAF == self.LFS:
                    eof_counter = 0
                    while eof_counter < self.RETRY_BEFORE_QUIT:
                        self.send_eof()
                        eof_counter = eof_counter + 1
                        print(f"Trying for {eof_counter} time. EOF Sent")
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
                    print(f"File sent successfully {self.client_count} times.")
                    return


# Parse command-line arguments
def read_args():
    parser = argparse.ArgumentParser(
        description="Reliable file transfer server over UDP."
    )
    parser.add_argument("server_ip", help="IP address of the server")
    parser.add_argument("server_port", type=int, help="Port number of the server")
    # parser.add_argument("fast_retransmit", help="Enable fast recovery")
    args = parser.parse_args()
    # fast_retransmit = args.fast_retransmit
    # if (
    #     fast_retransmit == "0"
    #     or fast_retransmit == "False"
    #     or fast_retransmit == False
    #     or fast_retransmit == 0
    # ):
    #     return (args.server_ip, args.server_port, False)

    # else:
    
    # In part 2, fast retransmit is ALWAYS enabled
    return (args.server_ip, args.server_port, True)


if __name__ == "__main__":
    # Run the server
    server = Server(*read_args())