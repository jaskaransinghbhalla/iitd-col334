import json
import pickle

def make_packet(seq, data):
    # Convert `seq` to a bytes object of minimum length needed to represent the integer
    seq_bytes = seq.to_bytes((seq.bit_length() + 7) // 8, byteorder='big', signed=False)
    
    # Store the length of seq_bytes in one byte, followed by the seq and data
    packet = len(seq_bytes).to_bytes(1, byteorder='big') + seq_bytes + data
    return packet

def parse_packet(packet):
    # Read the first byte to know the length of `seq`
    seq_len = int.from_bytes(packet[0:1], byteorder='big')
    
    # Extract `seq` using the length we just read
    seq_bytes = packet[1:1 + seq_len]
    seq = int.from_bytes(seq_bytes, byteorder='big', signed=False)
    
    # The remaining part of `packet` is `data`
    data = packet[1 + seq_len:]
    
    return seq, data