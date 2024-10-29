import socket
import time
import argparse
import struct

# Constants
MSS = 1400  # Maximum Segment Size for each packet
# Check Window Size later on
WINDOW_SIZE = 5  # Number of packets in flight
DUP_ACK_THRESHOLD = 3  # Threshold for duplicate ACKs to trigger fast recovery
# FILE_PATH = "100MB.bin"
FILE_PATH = "10KB.bin"
# Initialize timeout to some value but update it as ACK packets arrive
INITIAL_TIMEOUT = 1.0

ALPHA = 0.125
BETA = 0.25

BUFFER_SIZE = 1000  # 64


def make_packet(seq, data):
    seq_bytes = seq.to_bytes((seq.bit_length() + 7) // 8, byteorder="big")
    seq_length = len(seq_bytes)
    serialised_data = struct.pack("I", seq_length) + seq_bytes + data
    return serialised_data


def send_file(server_ip, server_port, enable_fast_recovery):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((server_ip, server_port))

    print(f"Server listening on {server_ip}:{server_port}")

    estimated_rtt = INITIAL_TIMEOUT
    dev_rtt = 0.0
    timeout_interval = estimated_rtt + 4 * dev_rtt

    client_address = None

    while True:
        request, client_address = server_socket.recvfrom(BUFFER_SIZE)
        print("Client Connected:", client_address)
        
        if request.decode() == "GET":
            print("Client requested a file...")
            with open(FILE_PATH, "rb") as f:
                LAF = 0
                LFS = 0
                file_sent = False
                packets = []
                packet_timestamps = {}
                duplicate_acks = {}

                while True:
                    if LFS < LAF + WINDOW_SIZE and not file_sent:
                        data = f.read(MSS)
                        if not data:
                            file_sent = True
                            # packets.append((LFS, b"EOF"))
                        else:
                            packets.append((LFS, data))
                        packet_timestamps[LFS] = time.time()
                        LFS += 1

                    for seq, packet_data in packets:
                        if time.time() - packet_timestamps[seq] >= timeout_interval:
                            packet = make_packet(seq, packet_data)
                            server_socket.sendto(packet, client_address)
                            packet_timestamps[seq] = time.time()
                            print(f"Packet {seq} retransmitted due to timeout.")
                        else:
                          packet = make_packet(seq, packet_data)
                          server_socket.sendto(packet, client_address)
                    
                    try:
                        # Wait for acknowledgement from client  
                        ack, _ = server_socket.recvfrom(BUFFER_SIZE)
                        ack_num = int.from_bytes(ack, "big")
                        print(f"Cumulative ACK received: {ack_num}")

                        # Timeout and RTT calculations here ...
                        if ack_num in packet_timestamps:
                            sample_rtt = time.time() - packet_timestamps[ack_num]

                            # Update EstimatedRTT and DevRTT
                            estimated_rtt = (
                                1 - ALPHA
                            ) * estimated_rtt + ALPHA * sample_rtt
                            dev_rtt = (1 - BETA) * dev_rtt + BETA * abs(
                                sample_rtt - estimated_rtt
                            )
                            timeout_interval = estimated_rtt + 4 * dev_rtt
                        
                        if enable_fast_recovery:
                            if ack_num in duplicate_acks:
                                duplicate_acks[ack_num] += 1
                            else:
                                duplicate_acks[ack_num] = 1

                            if duplicate_acks[ack_num] == DUP_ACK_THRESHOLD and ack < LFS:
                                print(f"Fast recovery triggered: Retransmitting packet {ack_num}")
                                
                                # Find the packet and retransmit
                                for seq, packet_data in packets:
                                    if seq == ack_num:
                                        packet = make_packet(seq, packet_data)
                                        server_socket.sendto(packet, client_address)
                                        packet_timestamps[seq] = time.time()
                                        print(f"Packet {seq} retransmitted due to fast recovery.")
                                        break
                        
                        # TODO:
                        # UNDERSTAND THESE TWO LINES
                        if file_sent and ack_num >= LFS - 1:
                            break

                        # Slide the window up to the latest cumulative ACKs
                        if ack_num > LAF:
                            LAF = ack_num
                            packets = [(seq, packet_data) for seq, packet_data in packets if seq > LAF]
                            packet_timestamps = {seq: timestamp for seq, timestamp in packet_timestamps.items() if seq > LAF}
                            duplicate_acks = {seq: count for seq, count in duplicate_acks.items() if seq > LAF}

                    except socket.timeout:
                        print("Timeout occurred while waiting for ACK.")
                        continue

                # EOF Transmission Policy
                eof_sent = False
                eof_retransmissions = 0
                while not eof_sent and eof_retransmissions < 10:
                    eof_packet = make_packet(LFS, b"EOF")
                    server_socket.sendto(eof_packet, client_address)
                    packet_timestamps[LFS] = time.time()
                    print(f"EOF packet transmitted, attempt {eof_retransmissions + 1}")
                    
                    try:
                        ack, _ = server_socket.recvfrom(BUFFER_SIZE)
                        ack_num = int.from_bytes(ack, "big")

                        if ack_num == LFS:
                            print("EOF ACK received.")
                            eof_sent = True
                        else:
                            raise socket.timeout
                        
                    except socket.timeout:
                        eof_retransmissions += 1
                        print("Timeout on EOF ACK, retransmitting EOF.")

                if not eof_sent:
                    print("EOF ACK not received after 10 attempts. Closing connection.")
                    break

            print("File transfer complete. Closing connection.")
            break

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Reliable file transfer server over UDP.")
parser.add_argument("server_ip", help="IP address of the server")
parser.add_argument("server_port", type=int, help="Port number of the server")
parser.add_argument("fast_recovery", type=bool, help="Enable fast recovery")

args = parser.parse_args()

# Run the server
send_file(args.server_ip, args.server_port, args.fast_recovery)
