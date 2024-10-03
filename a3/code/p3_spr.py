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
from ryu.lib.mac import haddr_to_bin
from ryu.topology.api import get_switch, get_all_link
import time
import threading
from ryu.lib.packet import packet
from ryu.lib.packet import lldp
import heapq


class ShortestPathRouting(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    # Initiazler

    def __init__(self, *args, **kwargs):
        super(ShortestPathRouting, self).__init__(*args, **kwargs)
        
        # LLDP
        
        self.lldp_active = True  # Flag to control LLDP handling
        self.lldp_duration = 10  # Duration to handle LLDP packets in seconds
        self.src_lldp_timestamps = {}
        
        # Common
        
        self.mac_to_port = {}
        self.graph = {}
        self.links = []
        self.switches = []
        self.topology_api_app = self
        
        # Shortest Path
        
        self.w_graph = {}
        self.shortest_path = {}

        # Spanning Tree
        
        self.blocked_ports = set()
        self.spanning_tree = []
        
        threading.Thread(target=self.lldp_timer).start()
        

    # LLDP Packet and Graph construction

    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, event):
        
        # Switches and Links
        
        self.switches = get_switch(self.topology_api_app, None)
        self.links = [link.to_dict() for link in get_all_link(self.topology_api_app)]
        print(get_all_link(self.topology_api_app))
        
        # Graph Construction
        
        graph = {}
        for link in self.links:
            src = link["src"]["dpid"]
            dst = link["dst"]["dpid"]
            if int(dst) not in graph.get(int(src), []):
                graph.setdefault(int(src), []).append(int(dst))
            if int(src) not in graph.get(int(dst), []):
                graph.setdefault(int(dst), []).append(int(src))
        self.graph = graph
        
        # Send LLDP Packets
        
        for switch in self.switches:
            if self.lldp_active:
                self.send_lldp_packets_on_all_ports(switch.dp)
        self.create_spanning_tree()
    
    def create_spanning_tree(self):
        
        # Spanning Tree
        self.prims()
        self.block_ports(self.spanning_tree)
        
    def prims(self):
        visited = set()
        start = self.switches[0].dp.id
        
        visited.add(start)
        edges = []
        for neighbor in self.graph[start]:
            if neighbor not in visited:
                edges.append((start, neighbor))

        while edges:
            edges.sort(key=lambda x: x[1])  # You can use different criteria for sorting
            next_edge = edges.pop(0)
            src, dst = next_edge

            if dst not in visited:
                visited.add(dst)
                self.spanning_tree.append(next_edge)

                # Add new edges from the newly visited node
                for neighbor in self.graph[dst]:
                    if neighbor not in visited:
                        edges.append((dst, neighbor))

    def block_ports(self, spanning_tree):
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
                self.src_lldp_timestamps[(datapath.id, port_no)] = time.time()
                self.send_packet(
                    datapath, port_no, lldp_pkt
                )  # Create an OpenFlow PacketOut message to send the LLDP packet
                
                # Save the time.time() in src_lldp_timestamps
                
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
        self.lldp_active = False  # Stop handling LLDP packets
        self.cal_shortest_path(self.w_graph)
        print("LLDP Timer expired.")
        print("--------------------------------")
        print("Graph")
        print(self.graph)
        print("--------------------------------")
        print("Modified Graph")
        print(self.w_graph)
        print("--------------------------------")
        print("Spanning-Tree")
        print(self.spanning_tree)
        print("--------------------------------")
        print("Blocked Ports")
        for dpid, port_no in self.blocked_ports:
            print(f"DPID: {dpid}, Port: {port_no}")
        print("--------------------------------")
        print("Shortest Path")
        print(self.shortest_path)
        print("--------------------------------")

    # Packet In Handling
    
    def cal_shortest_path(self, graph):
        for node in graph:
            self.shortest_path[node] = self.dijkstra(graph, node)
    
    def dijkstra(self, graph, start):
        # Initialize the distance dictionary with infinity
        distances = {node: [float('inf'), None] for node in graph}
        distances[start] = [0, None]  # Distance to the start node is 0

        # Priority queue: (distance to the node, node)
        pq = [(0, start)]

        while pq:
            current_distance, current_node = heapq.heappop(pq)

            # If the distance is greater than the recorded shortest path, skip it
            if current_distance > distances[current_node][0]:
                continue

            # Explore neighbors
            for neighbor, info in graph[current_node].items():
                weight = info[0]
                if(current_node == start):
                    port = info[1]
                else :
                    port = distances[current_node][1]
                distance = current_distance + weight

                # If a shorter path to the neighbor is found
                if distance < distances[neighbor][0]:
                    distances[neighbor] = [distance, port]
                    heapq.heappush(pq, (distance, neighbor))

        return distances

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
       
        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        self.mac_to_port.setdefault(dpid, {})

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = msg.in_port
        out_ports = []
        actions = []
        flooding = False
        
        # Port Management
        
        
        if dst in self.mac_to_port[dpid]:
            out_ports = [self.mac_to_port[dpid][dst]]
        else:
            all_ports = set(datapath.ports.keys())
            excluded_ports = {msg.in_port, 65534}
            for id, port_no in self.blocked_ports:
                if id == dpid:
                    excluded_ports.add(port_no)
            out_ports = all_ports - excluded_ports
            flooding = True
            
    # Get all available ports
        
    # Exclude the ports
        # out_ports = all_ports - excluded_ports
        # If there are valid ports, forward the packet; otherwise, drop it
        if out_ports:
            actions = [ofp_parser.OFPActionOutput(port) for port in out_ports]
        else:
            actions = []  # Drop packet
        # install a flow to avoid packet_in next time
        if not flooding:
            self.add_flow(datapath, msg.in_port, dst, src, actions)
            # print("Updated Flow Table")

        data = None
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
            data = msg.data
        out = ofp_parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=msg.in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)
        
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
            link_delay = round((end_time - start_time) * 1000, 0)  # Convert to milliseconds and round to 2 decimal places

            #    Store the graph in w_graph
            self.w_graph.setdefault(src_chassis, {})[datapath.id] = [link_delay, src_port_id]
            self.w_graph.setdefault(datapath.id, {})[src_chassis] = [link_delay, msg.in_port]
            
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

     # Add flow to the switch
    
    def add_flow(self, datapath, in_port, dst, src, actions):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        match = datapath.ofproto_parser.OFPMatch(
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

