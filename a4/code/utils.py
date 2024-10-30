import json
import pickle

def parse_packet(packet):
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

def make_packet(seq, data):
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