# Imports
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet
from ryu.lib.packet import packet
from ryu.ofproto import ofproto_v1_0


class LearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    # Initialzer

    def __init__(self, *args, **kwargs):
        """
        Initializes the LearningSwitch object.

        Parameters:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

        Attributes:
        mac_to_port (dict): Mac Address to Port table for Switch/RYU.
        """
        super(LearningSwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}  # Mac Address to Port table for Switch/RYU

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        """
        Handle incoming packet events.
        Args:
            event (Event): The event object containing the packet data.
        Returns:
            None
        Raises:
            None
        """
        # Event Parsing
        msg = event.msg
        datapath = msg.datapath
        ofp = datapath.ofproto

        # Packet Parsing
        pkt = packet.Packet(msg.data)  # parsing the packet data
        eth = pkt.get_protocol(
            ethernet.ethernet
        )  # get link layer frame from the packet
        src_mac = eth.src
        dst_mac = eth.dst

        # LLDP Control
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:  # Link Layer Discovery Protocol
            # ignore lldp packet
            return

        # Initializing and updating Host Mac Address - Switch Port table
        self.mac_to_port.setdefault(datapath.id, {})
        self.mac_to_port[datapath.id][src_mac] = msg.in_port
        
        # Port Management
        flood = False
        mac_to_switch_port_mapping = self.mac_to_port[datapath.id]
        
        if dst_mac in mac_to_switch_port_mapping:
            out_port = mac_to_switch_port_mapping[dst_mac]
        else:
            flood = True
            out_port = ofp.OFPP_FLOOD
            
        # Data Parsing
        data = None
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
            data = msg.data
        
        # Flow Management
        if not flood:
            self.add_flow(datapath, msg.in_port, out_port, src_mac, dst_mac)
            
        # Packet Sending
        self.send_packet(datapath, msg.in_port, out_port, data, msg.buffer_id)

    def add_flow(self, datapath, in_port, out_port, src, dst):
        """
        Add a flow to the switch's flow table.
        Parameters:
        - datapath: The datapath object representing the switch.
        - in_port: The input port number.
        - out_port: The output port number.
        - src: The source MAC address.
        - dst: The destination MAC address.
        Returns:
            None
        """
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        match = datapath.ofproto_parser.OFPMatch(
            in_port=in_port, dl_dst=haddr_to_bin(dst), dl_src=haddr_to_bin(src)
        )
        
        actions = [ofp_parser.OFPActionOutput(out_port)]

        # Modification
        # The following code is modified to add the flow with the OFPFF_SEND_FLOW_REM flag set.
        mod = ofp_parser.OFPFlowMod(
            datapath=datapath,
            match=match,
            cookie=0,
            command=ofp.OFPFC_ADD,
            idle_timeout=0,
            hard_timeout=0,
            priority=ofp.OFP_DEFAULT_PRIORITY,
            flags=ofp.OFPFF_SEND_FLOW_REM,
            actions=actions,
        )
        datapath.send_msg(mod)

    def send_packet(self, datapath, in_port, out_port, data, buffer_id):
        """
        Sends a packet to a specified port on a datapath.

        Parameters:
        - datapath (Datapath): The datapath to send the packet from.
        - port_no (int): The port number to send the packet to.
        - data (bytes): The packet data to be sent.

        Returns:
        None
        """
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(out_port)]
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)
