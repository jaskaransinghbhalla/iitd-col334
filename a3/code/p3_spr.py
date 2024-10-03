import struct
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import ethernet, lldp
from ryu.lib.packet import ether_types
from ryu.lib.packet import packet
from ryu.ofproto import ofproto_v1_0
from ryu.topology import event
from ryu.topology.api import get_switch, get_all_link
import time
import threading
from ryu.lib.packet import packet
from ryu.lib.packet import lldp


class ShortestPathRouting(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    # Initiazler

    def __init__(self, *args, **kwargs):
        super(ShortestPathRouting, self).__init__(*args, **kwargs)
        self.graph = {}
        self.w_graph = {}
        self.topology_api_app = self
        self.lldp_active = True  # Flag to control LLDP handling
        self.lldp_duration = 10  # Duration to handle LLDP packets in seconds
        self.src_lldp_timestamps = {}
        threading.Thread(target=self.lldp_timer).start()

    # LLDP Packet and Graph construction

    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, event):

        # Send LLDP Packets

        self.switches = get_switch(self.topology_api_app, None)
        for switch in self.switches:
            if self.lldp_active:
                self.send_lldp_packets_on_all_ports(switch.dp)

        print("--------------------------------")
        print("Graph")

        self.switches = get_switch(self.topology_api_app, None)
        self.links = [link.to_dict() for link in get_all_link(self.topology_api_app)]
        self.graph = {}
        graph = self.graph
        for link in self.links:
            src = link["src"]["dpid"]
            dst = link["dst"]["dpid"]
            if int(dst) not in graph.get(int(src), []):
                self.graph.setdefault(int(src), []).append(int(dst))
            if int(src) not in graph.get(int(dst), []):
                graph.setdefault(int(dst), []).append(int(src))
        print(graph)
        print("--------------------------------")

    def send_lldp_packets_on_all_ports(self, datapath):
        """
        Sends LLDP packets on all ports of the switch (datapath).
        :param datapath: The OpenFlow datapath object (represents a switch)
        """
        # Iterate through all the ports on the switch
        for port_no, port in datapath.ports.items():

            if port_no != datapath.ofproto.OFPP_LOCAL:  # Avoid the local port

                # Build LLDP packet for each port
                lldp_pkt = self.build_lldp_packet(datapath, port_no)
                self.send_packet(
                    datapath, port_no, lldp_pkt
                )  # Create an OpenFlow PacketOut message to send the LLDP packet
                
                # Save the time.time() in src_lldp_timestamps
                self.src_lldp_timestamps[(datapath.id, port_no)] = time.time()
                print(f"LLDP Packet Sent {datapath.id} {port_no}", time.time())

    def build_lldp_packet(self, datapath, port_no):

        # Create Ethernet frame
        eth = ethernet.ethernet(
            dst=lldp.LLDP_MAC_NEAREST_BRIDGE,
            src=datapath.ports[port_no].hw_addr,
            ethertype=ether_types.ETH_TYPE_LLDP,
        )

        # Use the DPID as the chassis ID
        chassis_id = lldp.ChassisID(
            subtype=lldp.ChassisID.SUB_LOCALLY_ASSIGNED,
            chassis_id=datapath.id.to_bytes(
                16, byteorder="big"
            ),  # Convert DPID to bytes
        )

        # port_id = lldp.PortID(
        #     subtype=lldp.PortID.SUB_PORT_COMPONENT,
        #     port_id=str(port_no).encode(),  # Convert port number to bytes
        # )
        port_id = lldp.PortID(
            subtype=lldp.PortID.SUB_PORT_COMPONENT,
            port_id=struct.pack(
                ">I", port_no
            ),  # Convert port number to a 4-byte integer
        )

        ttl = lldp.TTL(ttl=120)  # Time-to-live for the LLDP packet

        # Build the LLDP packet
        lldp_pkt = packet.Packet()
        lldp_pkt.add_protocol(eth)
        lldp_pkt.add_protocol(lldp.lldp(tlvs=[chassis_id, port_id, ttl, lldp.End()]))
        lldp_pkt.serialize()

        # Return the serialized packet (raw bytes)
        return lldp_pkt.data  # Return raw packet b`ytes without decoding

    def send_packet(self, datapath, port_no, data):
        """
        Sends a packet out on a specific port of a switch (datapath).
        :param datapath: The OpenFlow datapath object (represents a switch)
        :param port_no: The port number to send the packet on
        :param data: Serialized packet data (e.g., LLDP packet)
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Construct an OpenFlow PacketOut message
        actions = [
            parser.OFPActionOutput(port_no)
        ]  # Output action to send on specific port
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,  # No buffer, we're sending raw data
            in_port=ofproto.OFPP_CONTROLLER,  # Packet originates from the controller
            actions=actions,
            data=data,  # The serialized LLDP packet
        )

        # Send the PacketOut message to the switch
        datapath.send_msg(out)

    def lldp_timer(self):
        time.sleep(self.lldp_duration)  # Wait for the duration
        print("LLDP Timer expired.")
        print("--------------------------------")
        print("Modified Graph")
        print(self.w_graph)
        self.lldp_active = False  # Stop handling LLDP packets

    # Packet In Handling

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        msg = event.msg
        datapath = msg.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        pkt = packet.Packet(msg.data)  # Parsing the packet to get the Ethernet frame
        eth = pkt.get_protocol(
            ethernet.ethernet
        )  # Get ethernet/link layer frame from the packet
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:  # Link Layer Discovery Protocol
            if self.lldp_active:
                self.handle_lldp_packet_in(datapath, msg, pkt)
            return

    def handle_lldp_packet_in(self, datapath, msg, pkt):
        # Parse the LLDP packet
        lldp_pkt = pkt.get_protocol(lldp.lldp)
        if lldp_pkt:
            tlvs = lldp_pkt.tlvs  # Extract TLVs (Type-Length-Value fields)
            src_chassis = None
            src_port_id = None

            # Extract chassis ID (usually the source switch's ID)
            for tlv in tlvs:
                if isinstance(tlv, lldp.ChassisID):
                    src_chassis = (
                        tlv.chassis_id
                    )  # Get the raw chassis ID (could be MAC, etc.)
                    src_chassis = int.from_bytes(src_chassis, byteorder="big")
                    if src_chassis > 100000:
                        return
            # Extract port ID (usually the source port number)
                if isinstance(tlv, lldp.PortID):
                    src_port_id = struct.unpack(">I", tlv.port_id)[0]
                    

            # match datapath.id and msg.in_port with src_lldp_timestamps and check if the time difference is less than 10 seconds and get start_time
            if (datapath.id, msg.in_port) in self.src_lldp_timestamps:
                start_time = self.src_lldp_timestamps[(datapath.id, msg.in_port)]
                if time.time() - start_time > self.lldp_duration:
                    return
            end_time = time.time()
            link_delay = round((end_time - start_time) * 1000, 2)  # Convert to milliseconds and round to 2 decimal places

            #    Store the graph in w_graph
            self.w_graph.setdefault(src_chassis, {})[datapath.id] = link_delay
            self.w_graph.setdefault(datapath.id, {})[src_chassis] = link_delay
            
            print(
                "LLDP Packet Received",
                datapath.id,
                # msg.in_port,
                src_chassis,
                # src_port_id,
                link_delay,
            )
            
            

            # Extract neighbor switch information from the LLDP packet
            neighbor_dpid = src_chassis
            neighbor_port = src_port_id

            #   Continue processing, such as updating network topology or logging neighbor connection
            # self.update_topology(src_dpid, src_port, neighbor_dpid, src_port, neighbor_port)
