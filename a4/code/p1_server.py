import socket
import time
import argparse

# Constants
MSS = 1400  # Maximum Segment Size for each packet
# Check Window Size later on
WINDOW_SIZE = 5  # Number of packets in flight
DUP_ACK_THRESHOLD = 3  # Threshold for duplicate ACKs to trigger fast recovery
FILE_PATH = "10KB.bin"
INITIAL_TIMEOUT = 1.0  # Initialize timeout to some value but update it as ACK packets arrive

ALPHA = 0.125
BETA = 0.25

BUFFER_SIZE = 1000  # 64


def send_file(server_ip, server_port, enable_fast_recovery):
    """
    Send a predefined file to the client, ensuring reliability over UDP.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((server_ip, server_port))

    print(f"Server listening on {server_ip}:{server_port}")

    estimated_rtt = INITIAL_TIMEOUT
    dev_rtt = 0.0
    timeout_interval = estimated_rtt + 4 * dev_rtt

    # Wait for client to initiate connection
    client_address = None

    while True:
        # Receive file request from client
        request, client_address = server_socket.recvfrom(BUFFER_SIZE)
        print("Client Connected :", client_address)
        decoded_request = request.decode()
        # print("Request : ", request.decode())
        print("Request", decoded_request)
        if decoded_request == "GET":
            print(f"Client requested a file...")

            # Open file and initialize sliding window pointers
            with open(FILE_PATH, "rb") as f:
                LAF = 0 # last acknowledged frame
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
                            packets.append((LFS, b'EOF'))
                        else:
                            packets.append((LFS, data))
                        packet_timestamps[LFS] = time.time()
                        LFS += 1
                    
                    for seq, packet_data in packets:
                        if time.time() - packet_timestamps[seq] >= timeout_interval:
                            packet = seq.to_bytes(4, 'big') + packet_data
                            server_socket.sendto(packet, client_address)
                            packet_timestamps[seq] = time.time()
                            print(f"Packet {seq} retransmitted due to timeout.")
                        else:
                            packet = seq.to_bytes(4, 'big') + packet_data
                            server_socket.sendto(packet, client_address)
                    
                    try:
                        # Wait for acknowledgment
                        ack, _ = server_socket.recvfrom(BUFFER_SIZE)
                        ack_num = int.from_bytes(ack, 'big')
                        print(f"Cumulative ACK received: {ack_num}")                      

                        # Calculate SampleRTT
                        if ack_num in packet_timestamps:
                            sample_rtt = time.time() - packet_timestamps[ack_num]

                            # Update EstimatedRTT and DevRTT
                            estimated_rtt = (1 - ALPHA) * estimated_rtt + ALPHA * sample_rtt
                            dev_rtt = (1 - BETA) * dev_rtt + BETA * abs(sample_rtt - estimated_rtt)
                            timeout_interval = estimated_rtt + 4 * dev_rtt
                            print(f"Timeout interval updated to {timeout_interval}") 

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
                                        packet = seq.to_bytes(4, 'big') + packet_data
                                        server_socket.sendto(packet, client_address)
                                        packet_timestamps[seq] = time.time()
                                        break
                                
                        # Slide the window up to the latest cumulative ACK
                        if ack_num > LAF:
                            LAF = ack_num
                            # Remove acknowledged packets from the window and timestamps
                            packets = [(seq, data) for seq, data in packets if seq > LAF]
                            packet_timestamps = {seq: ts for seq, ts in packet_timestamps.items() if seq > LAF}

                            duplicate_acks = {seq: count for seq, count in duplicate_acks.items() if seq > LAF}
                    except socket.timeout:
                        print("Timeout occurred while waiting for ACK.")
                        continue

                    if file_sent and LAF == LFS:
                        print("File sent successfully.")
                        break
                    
# Parse command-line arguments
parser = argparse.ArgumentParser(description="Reliable file transfer server over UDP.")
parser.add_argument("server_ip", help="IP address of the server")
parser.add_argument("server_port", type=int, help="Port number of the server")
parser.add_argument("fast_recovery", type=bool, help="Enable fast recovery")

args = parser.parse_args()

# Run the server
send_file(args.server_ip, args.server_port, args.fast_recovery)
