from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0

class HubController(app_manager.RyuApp):

    # Open Flow Protocol version coming from RYU
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    # Constructor
    def __init__(self, *args, **kwargs):
        super(HubController, self).__init__(*args, **kwargs)

    """
    This is a decorator, it is used to register a handler for a specific event.
    This decorator tells Ryu when the decorated function should be called
    It handles the event when ever a packet is received by the switch
    
    The first argument of the decorator indicates which type of event this function should be called for. 
    As you might expect, every time Ryu gets a packet_in message, this function is called.
    
    The second argument indicates the state of the switch. 
    You probably want to ignore packet_in messages before the negotiation between Ryu and the switch is finished. 
    Using 'MAIN_DISPATCHER' as the second argument means this function is called only after the negotiation completes.
    """
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER) 
    def packet_in_handler(self, event):
        
        #  an object that represents a packet_in data structure.
        msg = event.msg 
        
        # msg.dp is an object that represents a datapath (switch)
        dp = msg.datapath
        
        # dp.ofproto and dp.ofproto_parser are objects that represent the OpenFlow protocol that Ryu and the switch negotiated
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser

        # OFPActionOutput class is used with a packet_out message to specify a switch port that you want to send the packet out of. 
        # This application uses the OFPP_FLOOD flag to indicate that the packet should be sent out on all ports
        actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)]

        data = None
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
             data = msg.data

        # OFPPacketOut class is used to build a packet_out message.
        out = ofp_parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions, data = data)
        
        # If you call Datapath class's send_msg method with a OpenFlow message class object, 
        # Ryu builds and sends the on-wire data format to the switch.
        dp.send_msg(out)
 
        