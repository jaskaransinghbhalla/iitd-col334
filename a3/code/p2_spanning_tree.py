# Imports
import time
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


class SpanningTreeLearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SpanningTreeLearningSwitch, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        self.switches = []
        self.links = []
        self.mac_to_port = {}
        self.blocked_ports = set()

    # Spanning Tree Construction
    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, ev):
        self.switches = get_switch(self.topology_api_app, None)
        self.links = [link.to_dict() for link in get_all_link(self.topology_api_app)]
        self.create_spanning_tree()

    def create_spanning_tree(self):
        graph = {}
        for link in self.links:
            src = link["src"]["dpid"]
            dst = link["dst"]["dpid"]
            if int(dst) not in graph.get(int(src), []):
                graph.setdefault(int(src), []).append(int(dst))
            if int(src) not in graph.get(int(dst), []):
                graph.setdefault(int(dst), []).append(int(src))
        visited = set()
        spanning_tree = []
        print("-------")
        print("Graph")
        print(graph)
        print("-------")
        start_switch = self.switches[0].dp.id
        print("start_switch", start_switch)
        self.prims(graph, start_switch, visited, spanning_tree)
        print("-------")
        print("Spanning-Tree")
        print(spanning_tree)
        print("-------")
        self.block_ports(spanning_tree)
        print("-------")
        # print("Blocked Ports")
        # for dpid, port_no in self.blocked_ports:
        #     print(f"DPID: {dpid}, Port: {port_no}")
        # print("-------")
    def prims(self, graph, start, visited, spanning_tree):

        visited.add(start)
        edges = []
        for neighbor in graph[start]:
            if neighbor not in visited:
                edges.append((start, neighbor))

        while edges:
            edges.sort(key=lambda x: x[1])  # You can use different criteria for sorting
            next_edge = edges.pop(0)
            src, dst = next_edge

            if dst not in visited:
                visited.add(dst)
                spanning_tree.append(next_edge)

                # Add new edges from the newly visited node
                for neighbor in graph[dst]:
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

    # Packet Handling
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        msg = event.msg
        datapath = msg.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        # Parsing the packet to get the Ethernet frame
        pkt = packet.Packet(msg.data)
        # Get ethernet/link layer frame from the packet
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:  # Link Layer Discovery Protocol
            # ignore lldp packet
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
            
            # for link in self.links:
            #     if int(link["src"]["dpid"]) == dpid:
            #         # print(f"Current blocked ports: {self.blocked_ports}")
            #         # print(f"Current dpid: {dpid}, src_port: {link['src']['port_no']}")
            #         # print(f"Condition evaluated as: {(dpid, link['src']['port_no']) not in self.blocked_ports}")
            #         if (dpid, int(link["src"]["port_no"])) not in self.blocked_ports and int(
            #             link["src"]["port_no"]
            #         ) != int(msg.in_port):
            #             # print("Adding port to out_ports")
            #             out_ports.append(int(link["src"]["port_no"]))
        # print(out_ports)
        
        #   # Replace with your blocked ports

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
        
        # print("----------")
        # print(
        #     f"DPID: {dpid}, In Port: {msg.in_port}, Source: {src}, Destination: {dst}"
        # )
        # print("all_ports",all_ports)
        # print("Mac to Port", self.mac_to_port)
        # print("Flooding", flooding)
        # print("Out Ports", out_ports)
        # print("----------")
        # time.sleep(10)

    def add_flow(self, datapath, in_port, dst, src, actions):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

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
