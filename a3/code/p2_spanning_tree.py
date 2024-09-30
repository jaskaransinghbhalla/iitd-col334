from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet

class SpanningTreeLearningSwitech():
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]
    
    def __init__(self, *args, **kwargs):
        super(SpanningTreeLearningSwitech, self).__init__(*args, **kwargs)
        self.datapaths = {}
        # self.mac_to_port = {}
        # self.topology_api_app = self
        # self.net = nx.DiGraph()
        # self.nodes = {}
        # self.links = {}
        # self.switches = []
        # self.hosts = []
    
    # @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    
    set_ev_cls(event.EventOFSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.datapaths[datapath.id] = datapath
    
    def create_spanning_tree():
        print("spanning tree")
    def block_ports(self):
        print("blocked ports")