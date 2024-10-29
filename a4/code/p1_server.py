import socket
import time
import argparse
import json
import pickle

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
    WINDOW_SIZE = 1
    # Initial timeout value, # Initialize timeout to some value but update it as ACK packets arrive
    INITIAL_TIMEOUT = 1.0
    # Buffer size for receiving packets
    BUFFER_SIZE = 1000  # 64
    # Packets in flight
    RETRY_BEFORE_QUIT = 10

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
                _, data = self.parse_packet(self.packet_in_flight[seq])
                retran_packets.append((seq, data))
        return retran_packets

    def parse_packet(self, packet):
        """
        Deserializes the binary packet back into 'seq' and 'data'.
        :param packet: bytes, binary serialized packet
        :return: dict, with 'seq' and 'data' keys
        """
        # Decode the binary packet back into a JSON string
        json_str = packet.decode("utf-8")
        json_obj = json.loads(json_str)

        # Extract and deserialize the data
        seq = int(json_obj.get("seq"))
        data = pickle.loads(json_obj.get("data").encode("latin1"))
        return seq, data

    def make_packet(self, seq, data):
        """
        Serializes the JSON object with 'seq' and binary 'data' into a binary string.
        :param seq: int, sequence number
        :param data: bytes, binary data
        :return: bytes, binary serialized packet
        """
        # Serialize the data using pickle and encode it in base64 for JSON compatibility
        serialized_data = pickle.dumps(data)
        json_obj = json.dumps(
            {
                "seq": seq,
                "data": serialized_data.decode(
                    "latin1"
                ),  # Decode to make it JSON-serializable
            }
        )
        return json_obj.encode("utf-8")

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
                _, data = self.parse_packet(self.packet_in_flight[seq])
                packet = self.make_packet(seq, data)
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
        eof_packet = self.make_packet(self.LFS + 1, b"EOF")
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
                    print("Timeout occurred while waiting for ACK.")
                    continue

                packets_to_retransmit = self.get_retransmission_packets()
                self.send_packets_to_client(packets_to_retransmit, retrans_packet=True)

                # 4 - Check if the file is sent
                if self.all_packets_read and self.LAF == self.LFS:
                    eof_counter = 0
                    while eof_counter < self.RETRY_BEFORE_QUIT:
                        self.send_eof()
                        eof_counter = eof_counter + 1
                        print("EOF Sent")
                        try:
                            ack, _ = self.server_socket.recvfrom(self.BUFFER_SIZE)
                            ack_num = int.from_bytes(ack, "big")
                            if ack_num == self.LAF + 2:
                                print("Final ack", ack_num)
                                break

                        except socket.timeout:
                            print("Timeout occurred while waiting for EOF ACK.")
                            continue
                    print(f"File sent successfully {self.client_count} times.")
                    self.client_count += 1
                    return


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
    # Run the server
    server = Server(*read_args())
