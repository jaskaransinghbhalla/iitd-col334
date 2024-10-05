# Imports
from pprintpp import pprint as pp  # type: ignore
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, lldp
from ryu.lib.packet import lldp
from ryu.lib.packet import packet
from ryu.lib.packet import packet
from ryu.ofproto import ofproto_v1_0
from ryu.topology import event
from ryu.topology.api import get_switch, get_all_link, get_all_host
import heapq
import struct
import time


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
        self.hosts = {}
        self.topology_api_app = self

        # Shortest Path

        self.w_graph = {}
        self.shortest_path = {}

        # Spanning Tree

        self.blocked_ports = set()
        self.spanning_tree = []
        
        # LLDP Constants

        self.lldp_timer_thread = hub.spawn(self.lldp_timer)

        self.switch_threads = {}
        self.switch_stop_flags = {}

    # LLDP Packet and Graph construction
    @set_ev_cls(event.EventSwitchEnter)
    def on_switch_enter(self, event):
        datapath = event.switch.dp
        dpid = datapath.id  # Get switch ID

        # Stop all previous threads
        self.stop_all_threads()
        hub.sleep(0.1)

        # Create a new stop flag and spawn a new thread for the entering switch
        self.switch_stop_flags[dpid] = False
        self.logger.info(f"Switch {dpid} entered, starting a new thread.")
        thread = hub.spawn(self.switch_thread, dpid)
        self.switch_threads[dpid] = thread  # Save the new thread

    def switch_thread(self, dpid):
        while not self.switch_stop_flags[dpid]:
            hub.sleep(0.5)
            print("LLDP Listening Started")
            # Switches
            self.switches = get_switch(self.topology_api_app, None)

            # Send LLDP Packets
            for switch in self.switches:
                if self.lldp_active:
                    self.send_lldp_packets_on_all_ports(switch.dp)
            self.stop_all_threads()

    def stop_all_threads(self):
        """Stop all running threads."""
        if self.switch_threads:
            self.logger.info("Stopping all threads.")

            # Set the stop flag for all running threads
            for dpid in self.switch_stop_flags:
                self.switch_stop_flags[dpid] = True

            # Wait for all threads to stop
            hub.joinall(self.switch_threads.values())

            # Clear threads and stop flags after they are stopped
            self.switch_threads.clear()
            self.switch_stop_flags.clear()

            self.logger.info("All threads stopped.")

    def send_lldp_packets_on_all_ports(self, datapath):

        # Iterate through all the ports on the switch
        for port_no, port in datapath.ports.items():

            if port_no != datapath.ofproto.OFPP_LOCAL:  # Avoid the local port

                # Build LLDP packet for each port
                lldp_pkt = self.build_lldp_packet(datapath, port_no)
                self.src_lldp_timestamps[(datapath.id, port_no)] = time.time()
                self.send_lldp_packet(datapath, port_no, lldp_pkt)

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

    def lldp_timer(self):
        hub.sleep(self.lldp_duration)  # Wait for the duration
        self.on_lldp_complete()
        hub.joinall([self.lldp_timer_thread])

    def on_lldp_complete(self):
        self.lldp_active = False  # Stop handling LLDP packets
        print("LLDP Listening Stopped.")
        print("--------------------------------")
        #  Links
        self.links = [link.to_dict() for link in get_all_link(self.topology_api_app)]
        # Hosts
        # hosts = get_all_host(self.topology_api_app)
        # self.hosts = {
        #     host.mac: {"datapath": host.port.dpid, "port": host.port.port_no}
        #     for host in hosts
        # }
        print("Hosts")
        # pp(hosts)
        print(self.hosts.keys())
        pp(self.hosts)
        print("--------------------------------")

        # Graph Construction
        self.create_graph()

        print("Graph")
        pp(self.graph)
        print("--------------------------------")

        # Link Delay Weighted Graph

        print("Link-delay Weighted Graph")
        pp(self.w_graph)
        print("--------------------------------")
        self.create_spanning_tree()
        print("Spanning-Tree")
        pp(self.spanning_tree)
        print("--------------------------------")
        print("Blocked Ports")
        for dpid, port_no in self.blocked_ports:
            pp(f"DPID: {dpid}, Port: {port_no}")

        # print("--------------------------------")
        self.cal_shortest_path(self.w_graph)
        print("Shortest Path")
        pp(self.shortest_path)
        print("--------------------------------")

    def create_graph(self):
        graph = {}
        for link in self.links:
            src = link["src"]["dpid"]
            dst = link["dst"]["dpid"]
            if int(dst) not in graph.get(int(src), []):
                graph.setdefault(int(src), []).append(int(dst))
            if int(src) not in graph.get(int(dst), []):
                graph.setdefault(int(dst), []).append(int(src))
        self.graph = graph

    # Spanning Tree

    def create_spanning_tree(self):

        # Spanning Tree
        self.prims()
        self.block_ports(self.spanning_tree)

    def prims(self):
        edges = []
        start = self.switches[0].dp.id
        visited = set()

        visited.add(start)
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

    # Shortest Path

    def cal_shortest_path(self, graph):
        for node in graph:
            self.shortest_path[node] = self.dijkstra(graph, node)

    def dijkstra(self, graph, start):
        # Initialize the distance dictionary with infinity
        distances = {node: [float("inf"), None] for node in graph}
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
                weight = info["delay"]
                if current_node == start:
                    port = info["src_port"]
                else:
                    port = distances[current_node][1]
                distance = current_distance + weight

                # If a shorter path to the neighbor is found
                if distance < distances[neighbor][0]:
                    distances[neighbor] = [distance, port]
                    heapq.heappush(pq, (distance, neighbor))

        return distances

    # Packet In Handling

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        # Event Handling
        msg = event.msg
        datapath = msg.datapath
        ofp = datapath.ofproto

        # Print the type of packet

        # Link Layer
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        src_mac = eth.src
        dst_mac = eth.dst

        # LLDP Packet Handling
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:  # Link Layer Discovery Protocol
            if self.lldp_active:
                self.handle_lldp_packet_in(datapath, msg, pkt)
                return

        self.mac_to_port.setdefault(datapath.id, {})
        self.mac_to_port[datapath.id][src_mac] = msg.in_port

        # Port Management
        mac_to_switch_port_mapping = self.mac_to_port[datapath.id]
        out_ports = []

        """
        Section to be Editted
        """

        # print packet info
        # print(f"Packet in {datapath.id} {src_mac} {dst_mac}")
        flood = False
        # Check if the destination MAC address is in the MAC to switch port mapping
        if dst_mac in mac_to_switch_port_mapping:
            # If the destination MAC address is found, get the corresponding output port
            out_port = mac_to_switch_port_mapping[dst_mac]
            out_ports.append(out_port)
        elif dst_mac in list(self.hosts.keys()):
            print("Shortest path handled")
            # Get the switch corresponding to dst_mac
            dst_datapath = self.hosts[dst_mac]['datapath']
            # Get the output port for the data to be sent to
            out_port = self.shortest_path[datapath.id][dst_datapath][1]
            print(type(out_port))
            # Update the out_ports
            out_ports.append(out_port)
            # Save the dst_mac to port configuration
            self.mac_to_port[datapath.id][dst_mac] = out_port
        else:
            # Spanning Tree
            flood = True
            # Broadcast MAC address
            ports_all = set(datapath.ports.keys())
            # Exclude the input port and the special OFPP_CONTROLLER port (65534)
            ports_to_exclude = {msg.in_port, 65534}
            # Exclude the blocked ports specific to this switch
            for datapath_id_for_blocked_port, port_no in self.blocked_ports:
                if datapath_id_for_blocked_port == datapath.id:
                    ports_to_exclude.add(port_no)
            # Calculate the output ports by subtracting the excluded ports from all ports
            out_ports = list(ports_all - ports_to_exclude)

        """
        Section to be Editted
        """
        # Data Parsing
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
            data = msg.data
        else:
            data = None

        # Flow Management and Packet Sending
        for out_port in out_ports:
            # Flow Management
            if not flood :
                self.add_flow(datapath, msg.in_port, out_port, src_mac, dst_mac)
            # Packet Sending
            self.send_packet(datapath, msg.in_port, out_port, data, msg.buffer_id)

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
            link_delay = round(
                (end_time - start_time) * 1000, 0
            )  # Convert to milliseconds and round to 2 decimal places

            self.w_graph.setdefault(src_chassis, {})[datapath.id] = {
                "delay": link_delay,
                "src_port": src_port_id,
            }

            self.w_graph.setdefault(datapath.id, {})[src_chassis] = {
                "delay": link_delay,
                "src_port": msg.in_port,
            }

            (print)(
                "LLDP Packet Received",
                datapath.id,
                src_chassis,
                link_delay,
            )

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

    def send_lldp_packet(self, datapath, port_no, data):

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(port_no)]
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=ofproto.OFPP_CONTROLLER,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

    @set_ev_cls(event.EventHostAdd, MAIN_DISPATCHER)
    def host_add_handler(self, ev):
        self.hosts[ev.host.mac] = {
            "datapath": ev.host.port.dpid,
            "port": ev.host.port.port_no,
        }
