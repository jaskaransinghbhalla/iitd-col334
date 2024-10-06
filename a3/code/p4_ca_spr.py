# Imports
from pprintpp import pprint as pp  # type: ignore
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import ethernet, lldp, ether_types, packet, ipv4, ipv6, arp
from ryu.ofproto import ofproto_v1_0
from ryu.topology import event
from ryu.topology.api import get_switch, get_all_link
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
        self.arp_table = {}

        # Shortest Path

        self.w_graph = {}
        self.shortest_path = {}
        self.shortest_path_pred = {}
        self.shortest_path_trees = {}
        self.blocked_ports_on_shortest_path_tree = {}

        # Spanning Tree

        self.blocked_ports = set()
        self.spanning_tree = []
        self.spt_mac_to_port = {}

        # LLDP Constants

        
        self.lldp_timer_thread = hub.spawn(self.lldp_timer)
        self.switch_threads = {}
        self.switch_stop_flags = {}
        # self.periodic_lldp_thread = hub.spawn(self.periodic_lldp_timer)  
        

    # LLDP Packet and Graph construction

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
        ofproto = datapath.ofproto
        # Iterate through all the ports on the switch
        for port_no, port in datapath.ports.items():

            if port_no != datapath.ofproto.OFPP_LOCAL:  # Avoid the local port

                # Build LLDP packet for each port
                lldp_pkt = self.build_lldp_packet(datapath, port_no)
                self.src_lldp_timestamps[(datapath.id, port_no)] = time.time()
                self.send_packet(
                    datapath,
                    ofproto.OFPP_CONTROLLER,
                    port_no,
                    lldp_pkt,
                    ofproto.OFP_NO_BUFFER,
                )

                # print(f"LLDP Packet Sent {datapath.id} {port_no}")

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

        # print("--------------------------------")
        #  Links
        self.links = [link.to_dict() for link in get_all_link(self.topology_api_app)]
        # print("Hosts")
        # pp(hosts)jj
        # pp(self.hosts)
        # print("--------------------------------")

        # Graph Construction
        self.create_graph()

        # print("Graph")
        # pp(self.graph)
        # print("--------------------------------")

        # Link Delay Weighted Graph

        # print("Link-delay Weighted Graph")
        # pp(self.w_graph)

        self.create_spanning_tree()
        # print("--------------------------------")
        # print("Spanning-Tree")
        # pp(self.spanning_tree)

        # print("--------------------------------")
        # print("Blocked Ports")
        # for dpid, port_no in self.blocked_ports:
            # pp(f"DPID: {dpid}, Port: {port_no}")

        # print("--------------------------------")
        self.cal_shortest_path(self.w_graph)
        # print("Shortest Path")
        # pp(self.shortest_path)

        # print("--------------------------------")
        # print("Shortest Path Trees")
        # pp(self.shortest_path_trees)

        # print("--------------------------------")
        # print("Blocked Ports on SPT")
        # pp(self.blocked_ports_on_shortest_path_tree)
        self.lldp_active = False  # Stop handling LLDP packets
        print("LLDP Listening Stopped.")
        hub.spawn(self.periodic_lldp_timer) 

    def periodic_lldp_timer(self):
        while True :
            hub.sleep(20)
            for switch in self.switches:
                self.send_lldp_packets_on_all_ports(switch.dp)
            print("Graph Updated")
            self.cal_shortest_path(self.w_graph)
            pp(self.w_graph)
            pp(self.shortest_path)
            for switch in self.switches:
                self.delete_all_flows(switch.dp)
    
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
        self.get_ports_to_block()

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

    # Shortest Path

    def cal_shortest_path(self, graph):
        for node in graph:
            self.shortest_path[node], self.shortest_path_pred[node] = self.dijkstra(
                graph, node
            )
            spt = self.construct_shortest_path_tree(
                self.shortest_path_pred[node], graph
            )
            self.shortest_path_trees[node] = spt
            self.cal_blocked_ports_on_shortest_path_tree(node)

    def dijkstra(self, graph, start):
        # Initialize the distance dictionary with infinity
        distances = {node: [float("inf"), None] for node in graph}
        distances[start] = [0, None]  # Distance to the start node is 0
        pred = {node: None for node in graph}

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
                    pred[neighbor] = current_node
                    heapq.heappush(pq, (distance, neighbor))

        return distances, pred

    def construct_shortest_path_tree(self, pred, graph):
        spt = {node: {} for node in graph}

        for node in graph:
            if pred[node] is not None:
                predecessor = pred[node]
                info = graph[node][predecessor]
                spt[predecessor][node] = info
        return spt

    def cal_blocked_ports_on_shortest_path_tree(self, node):
        blocked_ports = set()
        for link in self.links:
            src = link["src"]["dpid"]
            dst = link["dst"]["dpid"]

            if src == node:
                if int(dst) not in self.shortest_path_trees[node][src]:
                    blocked_ports.add((int(src), int(link["src"]["port_no"])))
                    blocked_ports.add((int(dst), int(link["dst"]["port_no"])))
        self.blocked_ports_on_shortest_path_tree[node] = blocked_ports

    # Handling Packets

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

    def handle_arp_packet_in(self, datapath, msg):
        # print("------------------")
        # print("ARP Table")
        # pp(self.arp_table)
        # print("------------------")
        ofp = datapath.ofproto

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        arp_pkt = pkt.get_protocol(arp.arp)

        src_mac = eth.src
        dst_mac = eth.dst

        src_ip = arp_pkt.src_ip
        dst_ip = arp_pkt.dst_ip

        if arp_pkt.opcode == arp.ARP_REQUEST:
            
            # Update ARP Table
            if src_ip not in self.arp_table:
                if not src_ip.startswith("169.254"):
                    self.arp_table[src_ip] = src_mac
            
            if dst_ip in self.arp_table:
                # Create ARP Reply
                arq_reply_pkt = packet.Packet()
                arq_reply_pkt.add_protocol(
                    ethernet.ethernet(
                        ethertype=ether_types.ETH_TYPE_ARP,
                        dst=src_mac,
                        src=self.arp_table[dst_ip],
                    )
                )
                arq_reply_pkt.add_protocol(
                    arp.arp(
                        opcode=arp.ARP_REPLY,
                        src_mac=self.arp_table[dst_ip],
                        src_ip=dst_ip,
                        dst_mac=src_mac,
                        dst_ip=src_ip,
                    )
                )
                arq_reply_pkt.serialize()
                arq_reply_pkt_data = arq_reply_pkt.data
                
                # Send ARP Reply
                self.send_packet(datapath, ofp.OFPP_CONTROLLER, msg.in_port, arq_reply_pkt_data, ofp.OFP_NO_BUFFER)
            else:
                # Flood in Spanning Tree
                out_ports = []
                
                self.spt_mac_to_port.setdefault(datapath.id, {})
                self.spt_mac_to_port[datapath.id][src_mac] = msg.in_port

                mac_to_switch_port_mapping = self.spt_mac_to_port[datapath.id]
                
                if dst_mac in mac_to_switch_port_mapping:
                    out_port = mac_to_switch_port_mapping[dst_mac]
                    out_ports.append(out_port)
                else:
                    ports_all = set(datapath.ports.keys())
                    ports_to_exclude = {msg.in_port, 65534}
                    for datapath_id_for_blocked_port, port_no in self.blocked_ports:
                        if datapath_id_for_blocked_port == datapath.id:
                            ports_to_exclude.add(port_no)
                    out_ports = list(ports_all - ports_to_exclude)

                if msg.buffer_id == ofp.OFP_NO_BUFFER:
                    data = msg.data
                else:
                    data = None

                # Flow Management and Packet Sending
                for out_port in out_ports:
                    self.send_packet(
                        datapath, msg.in_port, out_port, data, msg.buffer_id
                    )
            return

        if arp_pkt.opcode == arp.ARP_REPLY:
            # Update ARP Table
            out_ports = []
            if src_ip not in self.arp_table:
                self.arp_table[src_ip] = src_mac
            
            self.spt_mac_to_port.setdefault(datapath.id, {})
            self.spt_mac_to_port[datapath.id][src_mac] = msg.in_port
            
            mac_to_switch_port_mapping = self.spt_mac_to_port[datapath.id]
            
            if dst_mac in mac_to_switch_port_mapping:
                out_port = mac_to_switch_port_mapping[dst_mac]
                out_ports.append(out_port)
                
            if msg.buffer_id == ofp.OFP_NO_BUFFER:
                    data = msg.data
            else:
                data = None

            # Flow Management and Packet Sending
            for out_port in out_ports:
                self.send_packet(
                    datapath, msg.in_port, out_port, data, msg.buffer_id
                )
            
            return

    def handle_common_packet_in(self, datapath, msg):
        ofp = datapath.ofproto

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        src_mac = eth.src
        dst_mac = eth.dst

        self.mac_to_port.setdefault(datapath.id, {})
        self.mac_to_port[datapath.id][src_mac] = msg.in_port
        # Port Management
        mac_to_switch_port_mapping = self.mac_to_port[datapath.id]
        out_ports = []
        flood = False
        # Check if the destination MAC address is in the MAC to switch port mapping

        # if dst_mac in self.hosts.keys():

        if dst_mac in mac_to_switch_port_mapping:
            # If the destination MAC address is found, get the corresponding output port
            out_port = mac_to_switch_port_mapping[dst_mac]
            out_ports.append(out_port)
        else:
            # print("Shortest path handled")
            # Get the switch corresponding to dst_mac
            dst_datapath = self.hosts[dst_mac]["datapath"]
            # Get the output port for the data to be sent to
            out_port = self.shortest_path[datapath.id][dst_datapath][1]
            if out_port == None:
                all_ports = set(port.port_no for port in datapath.ports.values())
                ports_to_exclude = {msg.in_port}
                for each in self.shortest_path[datapath.id].values():
                    if each[0] != dst_datapath:
                        ports_to_exclude.add(each[1])
                out_ports = list(all_ports - ports_to_exclude)
            else:
                # Update the out_ports
                out_ports.append(out_port)
                # print(out_ports, datapath.id, dst_datapath)
                # Save the dst_mac to port configuration
                self.mac_to_port[datapath.id][dst_mac] = out_port
        # else:
        #     # Flood Shortest path Tree
        #     flood = True
        #     all_ports = set(port.port_no for port in datapath.ports.values())
        #     ports_to_exclude = {msg.in_port, 65534}
        #     for (
        #         datapath_id_for_blocked_port,
        #         port_no,
        #     ) in self.blocked_ports_on_shortest_path_tree[datapath.id]:
        #         if datapath_id_for_blocked_port == datapath.id:
        #             ports_to_exclude.add(port_no)
        #     out_ports = list(all_ports - ports_to_exclude)
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
            # if not flood:
            # self.add_flow(datapath, msg.in_port, out_port, src_mac, dst_mac)
            # Packet Sending
            self.send_packet(datapath, msg.in_port, out_port, data, msg.buffer_id)
        if(len(out_ports) == 1):
            self.add_flow(datapath, msg.in_port, out_port, src_mac, dst_mac)
    
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
        # self.logger.info(f"Packet sent from port {in_port} to port {out_port}")

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

    # Event Handlers

    # Host In

    @set_ev_cls(event.EventHostAdd, MAIN_DISPATCHER)
    def host_in_handler(self, ev):
        self.hosts[ev.host.mac] = {
            "datapath": ev.host.port.dpid,
            "port": ev.host.port.port_no,
        }

    # Switch In

    @set_ev_cls(event.EventSwitchEnter)
    def switch_in_handler(self, event):
        datapath = event.switch.dp

        # Stop all previous threads
        self.stop_all_threads()
        hub.sleep(0.1)

        # Create a new stop flag and spawn a new thread for the entering switch
        self.switch_stop_flags[datapath.id] = False
        self.logger.info(f"Switch {datapath.id} entered, starting a new thread.")
        thread = hub.spawn(self.switch_thread, datapath.id)
        self.switch_threads[datapath.id] = thread  # Save the new thread

    # Packet In

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        # Event Handling
        msg = event.msg
        datapath = msg.datapath

        # Packet Description
        pkt = packet.Packet(msg.data)

        arp_pkt = pkt.get_protocol(arp.arp)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        ipv6_pkt = pkt.get_protocol(ipv6.ipv6)

        eth = pkt.get_protocol(ethernet.ethernet)
        src_mac = eth.src
        dst_mac = eth.dst

        # LLDP Packet
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:  # Link Layer Discovery Protocol
            self.handle_lldp_packet_in(datapath, msg, pkt)
            # if self.lldp_active:
            #     return
            # else:
            #     return
        # ARP Packet
        elif arp_pkt:
            if self.lldp_active:
                return
            else:
                src_ip = arp_pkt.src_ip
                dst_ip = arp_pkt.dst_ip
                arp_opcode = arp_pkt.opcode
                if arp_opcode == arp.ARP_REPLY:

                    print(
                        "ARP Reply",
                        f"Source MAC: {src_mac}",
                        f"Destination MAC: {dst_mac}",
                        f"Source IP: {src_ip}",
                        f"Destination IP: {dst_ip}",
                        f"Datapath : {datapath.id}",
                    )
                else:
                    print(
                        "ARP Request",
                        f"Source MAC: {src_mac}",
                        f"Destination MAC: {dst_mac}",
                        f"Source IP: {src_ip}",
                        f"Destination IP: {dst_ip}",
                        f"Datapath : {datapath.id}",
                    )
                self.handle_arp_packet_in(datapath, msg)
                return
        # IPv4 Packet
        elif ipv4_pkt:
            if self.lldp_active:
                return
            else:
                src_ip = ipv4_pkt.src
                dst_ip = ipv4_pkt.dst
                print(
                    "IPv4",
                    f"Source MAC: {src_mac}",
                    f"Destination MAC: {dst_mac}",
                    f"Source IP: {src_ip}",
                    f"Destination IP: {dst_ip}")
                # Generate an array of strings from 224 to 239
                filter = [str(i) for i in range(224, 240)]
                
                # Ignore IP addresses that start with 224 to 239
                if dst_ip.startswith(tuple(filter)):
                    return
                elif dst_ip == "255:255:255:255":
                    return
                elif dst_mac == "ff:ff:ff:ff:ff:ff":
                    return
                else :
                    self.handle_common_packet_in(datapath, msg)
                    return
        # IPv6 Packet
        elif ipv6_pkt:
            if self.lldp_active:
                return
            else:
                src_ip = ipv6_pkt.src
                dst_ip = ipv6_pkt.dst

                # Check if destination IP starts with ff (IPv6 multicast)
                if ipv6_pkt.dst.startswith("ff0"):
                    return

                print(
                    "IPv6",
                    f"Source MAC: {src_mac}",
                    f"Destination MAC: {dst_mac}",
                    f"Source IP: {src_ip}",
                    f"Destination IP: {dst_ip}",
                )
                return
                self.handle_common_packet_in(datapath, msg)
        # Other Packets
        else:
            print("Other Packet", eth.ethertype)

    def delete_all_flows(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Create a flow mod message to delete all flows (OpenFlow 1.0)
        match = parser.OFPMatch()  # Match all flows
        mod = parser.OFPFlowMod(datapath=datapath, command=ofproto.OFPFC_DELETE,
                                out_port=ofproto.OFPP_NONE, match=match)
        datapath.send_msg(mod)