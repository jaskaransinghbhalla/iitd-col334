import socket
import os

# Client configuration
SERVER_IP = '127.0.0.1'
SERVER_PORT = 5001
BUFFER_SIZE = 1024

def main(filename):
    # Create UDP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(2.0)  # General socket timeout

    # Send file request to server
    client_socket.sendto(filename.encode(), (SERVER_IP, SERVER_PORT))
    
    # Prepare to receive file with sliding window mechanism
    expected_seq_num = 0
    buffer = {}  # Buffer to store out-of-order packets

    with open(f"received_{filename}", "wb") as f:
        while True:
            try:
                # Receive data from server
                packet, _ = client_socket.recvfrom(BUFFER_SIZE)
                
                # Extract sequence number and data
                seq_num = int.from_bytes(packet[:4], 'big')
                data = packet[4:]
                
                if data == b'EOF':
                    print("End of file reached.")
                    break
                
                if seq_num == expected_seq_num:
                    # Write in-order packet data to file
                    f.write(data)
                    expected_seq_num += 1

                    # Check buffer for the next in-sequence packet
                    while expected_seq_num in buffer:
                        f.write(buffer.pop(expected_seq_num))
                        expected_seq_num += 1
                    
                    # Send cumulative ACK for the next expected packet
                    ack_num = expected_seq_num
                    client_socket.sendto(ack_num.to_bytes(4, 'big'), (SERVER_IP, SERVER_PORT))
                    print(f"ACK sent for sequence {ack_num}")
                
                elif seq_num > expected_seq_num:
                    # Out-of-order packet, store in buffer
                    if seq_num not in buffer:
                        buffer[seq_num] = data
                    # Send ACK for the last received in-sequence packet
                    client_socket.sendto(expected_seq_num.to_bytes(4, 'big'), (SERVER_IP, SERVER_PORT))
                    print(f"Out-of-order packet {seq_num} received, expecting {expected_seq_num}.")
                
            except socket.timeout:
                # Handle socket timeout, in case we need to resend ACKs or take action
                print("Waiting for packets...")
                client_socket.sendto(expected_seq_num.to_bytes(4, 'big'), (SERVER_IP, SERVER_PORT))

    print(f"File '{filename}' received successfully as 'received_{filename}'.")
    client_socket.close()

if __name__ == "__main__":
    filename = input("Enter the filename to request: ")
    main(filename)