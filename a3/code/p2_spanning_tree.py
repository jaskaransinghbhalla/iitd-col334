# Imports
import pprint
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet
from ryu.lib.packet import packet
from ryu.ofproto import ofproto_v1_0
from ryu.topology import event
from ryu.topology.api import get_switch, get_all_link
import time
from pprintpp import pprint as pp


class SpanningTreeLearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    # Initialzer

    def __init__(self, *args, **kwargs):
        """
        Initializes the SpanningTreeLearningSwitch object.

        Parameters:
        - args: Variable length argument list.
        - kwargs: Arbitrary keyword arguments.

        Attributes:
        - mac_to_port: A dictionary mapping MAC addresses to port numbers of the switch.
        - links: A list of links in the network.
        - switches: A list of switches in the network.
        - topology_api_app: The topology API application.
        - graph: A dictionary representing the network graph.
        - spanning_tree: A list representing the spanning tree of the network.
        - blocked_ports: A set of blocked ports in the network.
        """
        super(SpanningTreeLearningSwitch, self).__init__(*args, **kwargs)

        # Common
        self.mac_to_port = {}
        self.links = []
        self.switches = []
        self.topology_api_app = self

        # Graph
        self.graph = {}

        # Spanning Tree
        self.spanning_tree = []
        self.blocked_ports = set()

    # Topology

    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, ev):
        """
        Retrieves the topology data, constructs a graph, creates a spanning tree, and determines the ports to block.
        Parameters:
        - ev: The event triggering the function.
        Returns:
        None
        Raises:
        None
        """

        # Get Switches and Links
        self.switches = get_switch(self.topology_api_app, None)
        self.links = [link.to_dict() for link in get_all_link(self.topology_api_app)]

        # Graph Construction
        graph = {}
        for link in self.links:
            src = link["src"]["dpid"]
            dst = link["dst"]["dpid"]
            if int(dst) not in graph.get(int(src), []):
                graph.setdefault(int(src), []).append(int(dst))
            if int(src) not in graph.get(int(dst), []):
                graph.setdefault(int(dst), []).append(int(src))
        if(graph == {}):
            return
        self.graph = graph
        
        print("--------------------")
        print("Graph")
        pp(self.graph)

        # Spanning Tree Creation and Port Blocking
        self.create_spanning_tree()
        print("--------------------")
        print("Spanning Tree")
        pp(self.spanning_tree)

        # Get the ports to be blocked
        self.get_ports_to_block()
        print("--------------------")
        for src, port in self.blocked_ports:
            print("Blocked Port: switch=s{}, port={}".format(src, port))
        print("--------------------")

    # Spanning Tree

    def create_spanning_tree(self):
        """
        Creates a spanning tree using Prim's algorithm.

        This method clears the existing spanning tree and then applies Prim's algorithm to generate a new spanning tree.

        Returns:
            None
        """
        self.spanning_tree.clear()
        self.prims()

    def prims(self):
        """
        Implements Prim's algorithm to find the minimum spanning tree of a graph.

        Returns:
            None

        Algorithm:
            1. Initialize an empty set 'visited' to keep track of visited vertices.
            2. Set 'start' as the ID of the first switch in the 'switches' list.
            3. Add 'start' to the 'visited' set.
            4. Initialize an empty list 'edges' to store the edges of the minimum spanning tree.
            5. For each neighbor of 'start' in the 'graph' dictionary:
                a. If the neighbor is not in the 'visited' set, add the edge (start, neighbor) to 'edges'.
            6. While 'edges' is not empty:
                a. Sort 'edges' based on the second element of each edge.
                b. Pop the first edge from 'edges' and assign it to 'next_edge'.
                c. Extract the source and destination vertices from 'next_edge'.
                d. If the destination vertex is not in the 'visited' set:
                    i. Add the 'next_edge' to the 'spanning_tree' list.
                    ii. Add the destination vertex to the 'visited' set.
                    iii. For each neighbor of the destination vertex in the 'graph' dictionary:
                        - If the neighbor is not in the 'visited' set, add the edge (destination, neighbor) to 'edges'.
            7. Return None.
        """

        edges = []
        start = self.switches[0].dp.id
        visited = set()

        visited.add(start)
        for neighbor in self.graph[start]:
            if neighbor not in visited:
                edges.append((start, neighbor))

        while edges:
            edges.sort(key=lambda x: x[1])
            next_edge = edges.pop(0)
            src, dst = next_edge

            if dst not in visited:
                visited.add(dst)
                self.spanning_tree.append(next_edge)

                for neighbor in self.graph[dst]:
                    if neighbor not in visited:
                        edges.append((dst, neighbor))

    def get_ports_to_block(self):
        """
        Retrieves the ports that need to be blocked based on the current spanning tree.

        Returns:
            set: A set of tuples representing the blocked ports. Each tuple contains the source
            switch ID and the port number that needs to be blocked.
        """
        spanning_tree = self.spanning_tree
        self.blocked_ports.clear()  # Reset blocked ports
        for link in self.links:
            src = link["src"]["dpid"]
            dst = link["dst"]["dpid"]
            if (int(src), int(dst)) not in spanning_tree and (
                int(dst),
                int(src),
            ) not in spanning_tree:
                self.blocked_ports.add((int(src), int(link["src"]["port_no"])))
                self.blocked_ports.add((int(dst), int(link["dst"]["port_no"])))

    # Packet Handling

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        """
        Handle incoming packet events.
        Args:
            event (Event): The event object containing the packet message.
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
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

        # Initializing and updating Host Mac Address - Switch Port table
        self.mac_to_port.setdefault(datapath.id, {})
        self.mac_to_port[datapath.id][src_mac] = msg.in_port

        # Port Management
        mac_to_switch_port_mapping = self.mac_to_port[datapath.id]

        out_ports = []
        flood = False

        # Check if the destination MAC address is in the MAC to switch port mapping
        if dst_mac in mac_to_switch_port_mapping:
            # If the destination MAC address is found, get the corresponding output port
            out_port = mac_to_switch_port_mapping[dst_mac]
            out_ports.append(out_port)
        else:
            # If the destination MAC address is not found, flood the packet to all ports except the input port and blocked ports
            flood = True
            # Get all the ports of the switch
            ports_all = set(datapath.ports.keys())
            # Exclude the input port and the special OFPP_CONTROLLER port (65534)
            ports_to_exclude = {msg.in_port, 65534}
            # Exclude the blocked ports specific to this switch
            for datapath_id_for_blocked_port, port_no in self.blocked_ports:
                if datapath_id_for_blocked_port == datapath.id:
                    ports_to_exclude.add(port_no)
            # Calculate the output ports by subtracting the excluded ports from all ports
            out_ports = list(ports_all - ports_to_exclude)

        # Check if the buffer ID is set to OFP_NO_BUFFER
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
            # If the buffer ID is not set, it means the packet data is not buffered in the switch
            # Therefore, we need to retrieve the packet data from the message object
            data = msg.data
        else:
            data = None

        for out_port in out_ports:
            if not flood:
                self.add_flow(
                    datapath, src_mac, msg.in_port, dst_mac, out_port
                )  # Install a flow to avoid packet_in next time
            self.send_packet(datapath, out_port, data)

    def send_packet(self, datapath, port_no, data):
        """
        Sends a packet to a specified port on a datapath.

        Parameters:
        - datapath (Datapath): The datapath to send the packet from.
        - port_no (int): The port number to send the packet to.
        - data (bytes): The packet data to be sent.

        Returns:
        None
        """
        # Rest of the code...
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(port=port_no)]
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=ofproto.OFPP_CONTROLLER,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

    def add_flow(self, datapath, src, in_port, dst, out_port):
        """
        Add a flow entry to the switch's flow table.

        Parameters:
            datapath (OFPDatapath): The datapath of the switch.
            in_port (int): The input port of the flow.
            dst (str): The destination MAC address of the flow.
            src (str): The source MAC address of the flow.
            port (int): The output port of the flow.

        Returns:
            None
        """
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        actions = [ofp_parser.OFPActionOutput(out_port)]

        match = ofp_parser.OFPMatch(
            in_port=in_port, dl_dst=haddr_to_bin(dst), dl_src=haddr_to_bin(src)
        )

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
