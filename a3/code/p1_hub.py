b# Imports
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0


class HubController(app_manager.RyuApp):

    # Open Flow Protocol version coming from RYU
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    # RYU Application Constructor
    def __init__(self, *args, **kwargs):
        """
        Initializes a new instance of the HubController class.

        Parameters:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
        """
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
    That is when the application is on normal status
    """

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        """
        Handle the packet_in event.

        Parameters:
        - event: An object that represents the packet_in event.

        Returns:
        None
        """
        # Event Parsing
        msg = event.msg  # an object that represents a packet_in data structure.
        datapath = (
            msg.datapath
        )  # msg.datapath is an object that represents a datapath (switch)
        ofp = (
            datapath.ofproto
        )  # ofproto and ofproto_parser are objects that represent the OpenFlow protocol that Ryu and the switch negotiated. ofproto is an object in Ryu that holds OpenFlow protocol constants

        # Data Parsing
        # Check if the buffer ID is set to OFP_NO_BUFFER
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
            # If the buffer ID is not set, it means the packet data is not buffered in the switch
            # Therefore, we need to retrieve the packet data from the message object
            data = msg.data
        else:
            data = None

        self.send_packet(datapath, datapath.ofproto.OFPP_FLOOD, data)

    def send_packet(self, datapath, out_port, data):
        """
        Sends a packet to a specified port on a datapath.

        Parameters:
        - datapath (Datapath): The datapath to send the packet from.
        - port_no (int): The port number to send the packet to.
        - data (bytes): The packet data to be sent.

        Returns:
        None
        """
        ofproto = datapath.ofproto
        # parser provides the tools needed to construct and parse OpenFlow messages
        # •	When the controller wants to send a specific OpenFlow message (e.g., to install a flow or to query statistics), ofproto_parser helps to construct that message in a format that the switch understands.
        # •	Similarly, when the controller receives an OpenFlow message from a switch (e.g., Packet-In or Features Reply), ofproto_parser helps to decode and interpret the message.
        parser = datapath.ofproto_parser
        # OFPActionOutput class is used with a packet_out message to specify a switch port that you want to send the packet out of.
        # This application uses the OFPP_FLOOD flag to indicate that the packet should be sent out on all ports

        actions = [parser.OFPActionOutput(out_port)]
        # OFPPacketOut class is used to build a packet_out message.
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=ofproto.OFPP_CONTROLLER,
            actions=actions,
            data=data,
        )
        # If you call Datapath class's send_msg method with a OpenFlow message class object,
        # Ryu builds and sends the data to the switch and tells it what to perform the actions
        datapath.send_msg(out)
