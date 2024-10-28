import socket
import os
import time
import argparse

# Server configuration
SERVER_IP = '127.0.0.1'
SERVER_PORT = 5001
BUFFER_SIZE = 1024
WINDOW_SIZE = 5  # Window size for sliding window protocol
ALPHA = 0.125  # Weight factor for EstimatedRTT
BETA = 0.25  # Weight factor for DevRTT
INITIAL_TIMEOUT = 2.0  # Initial timeout before dynamic adjustment

def main(fast_retransmit):
    # Create a UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((SERVER_IP, SERVER_PORT))
    server_socket.settimeout(1.0)  # General socket timeout for receiving ACKs
    
    print(f"Server listening on {SERVER_IP}:{SERVER_PORT} with fast retransmit={'enabled' if fast_retransmit else 'disabled'}")
    
    # Initialize RTT variables
    estimated_rtt = INITIAL_TIMEOUT
    dev_rtt = 0.0
    timeout_interval = estimated_rtt + 4 * dev_rtt

    while True:
        # Receive file request from client
        request, client_address = server_socket.recvfrom(BUFFER_SIZE)
        filename = request.decode()
        print(f"Client requested file: {filename}")
        
        if not os.path.exists(filename):
            print("Requested file does not exist.")
            server_socket.sendto(b"ERROR: File not found", client_address)
            continue

        # Open file and initialize sliding window pointers
        with open(filename, 'rb') as f:
            LAF = 0  # Last acknowledged frame
            LFS = 0  # Last frame sent
            file_end = False
            packets = []  # Store packets in the window
            packet_timestamps = {}  # Store send times for packets
            duplicate_acks = {}  # Track duplicate ACKs

            # Prepare packets and manage the sliding window
            while True:
                # Fill window if there are packets left to send
                if LFS < LAF + WINDOW_SIZE and not file_end:
                    data = f.read(BUFFER_SIZE - 4)
                    if not data:
                        file_end = True
                        packets.append((LFS, b'EOF'))
                    else:
                        packets.append((LFS, data))
                    packet_timestamps[LFS] = time.time()
                    LFS += 1

                # Send or retransmit all packets in the window
                for seq, packet_data in packets:
                    # Check if the packet needs to be retransmitted based on timeout
                    if time.time() - packet_timestamps[seq] >= timeout_interval:
                        packet = seq.to_bytes(4, 'big') + packet_data
                        server_socket.sendto(packet, client_address)
                        packet_timestamps[seq] = time.time()  # Update timestamp
                        print(f"Packet {seq} retransmitted due to timeout.")
                    else:
                        packet = seq.to_bytes(4, 'big') + packet_data
                        server_socket.sendto(packet, client_address)
                
                try:
                    # Wait for acknowledgment
                    ack_data, _ = server_socket.recvfrom(4)
                    ack_num = int.from_bytes(ack_data, 'big')
                    print(f"Cumulative ACK received: {ack_num}")

                    # Calculate SampleRTT
                    if ack_num in packet_timestamps:
                        sample_rtt = time.time() - packet_timestamps[ack_num]
                        
                        # Update EstimatedRTT and DevRTT
                        estimated_rtt = (1 - ALPHA) * estimated_rtt + ALPHA * sample_rtt
                        dev_rtt = (1 - BETA) * dev_rtt + BETA * abs(sample_rtt - estimated_rtt)
                        timeout_interval = estimated_rtt + 4 * dev_rtt
                        print(f"Updated RTT stats: EstimatedRTT={estimated_rtt:.3f}, DevRTT={dev_rtt:.3f}, Timeout={timeout_interval:.3f}")

                    # Fast retransmit mode: Check for duplicate ACKs
                    if fast_retransmit:
                        if ack_num in duplicate_acks:
                            duplicate_acks[ack_num] += 1
                        else:
                            duplicate_acks[ack_num] = 1
                        
                        # Retransmit if 3 duplicate ACKs are received
                        if duplicate_acks[ack_num] == 3 and ack_num < LFS:
                            print(f"Fast retransmit for packet {ack_num} after 3 duplicate ACKs")
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
                        packets = [(seq, pkt) for seq, pkt in packets if seq >= LAF]
                        packet_timestamps = {seq: packet_timestamps[seq] for seq, _ in packets}
                        # Reset duplicate ACKs tracking for lower sequence numbers
                        duplicate_acks = {seq: count for seq, count in duplicate_acks.items() if seq >= LAF}
                
                except socket.timeout:
                    # No ACK received, check for timed-out packets to retransmit
                    continue

                # End transfer if all packets are acknowledged and EOF sent
                if file_end and LAF >= LFS:
                    print("File transfer completed.")
                    break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP File Transfer Server with Sliding Window Protocol")
    parser.add_argument('--fast-retransmit', action='store_true', help="Enable fast retransmit mode")
    args = parser.parse_args()
    main(args.fast_retransmit)
