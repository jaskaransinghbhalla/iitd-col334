    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info("Registering datapath: %s", datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.info("Unregistering datapath: %s", datapath.id)
                del self.datapaths[datapath.id]

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._send_lldp_packets(dp)
            hub.sleep(10)  # LLDP packet sending interval

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            lldp_pkt = pkt.get_protocol(lldp.lldp)
            if lldp_pkt:
                src_dpid, src_port_no = LLDPPacket.lldp_parse(msg.data)
                self.logger.info(
                    "Received LLDP from switch %s on port %s", src_dpid, src_port_no
                )
                self._handle_lldp_packet(
                    dpid, src_dpid, src_port_no, ev.msg.match["in_port"]
                )

    def _handle_lldp_packet(self, dst_dpid, src_dpid, src_port_no, dst_port_no):
        now = time.time()
        src_port_key = (src_dpid, src_port_no)

        if src_port_key in self.port_time:
            delay = now - self.port_time[src_port_key]
            self.logger.info(
                "Link delay between switch %s port %s and switch %s port %s is %f seconds",
                src_dpid,
                src_port_no,
                dst_dpid,
                dst_port_no,
                delay,
            )
            self.link_delays[(src_dpid, src_port_no, dst_dpid, dst_port_no)] = delay
        else:
            self.logger.info(
                "First LLDP packet between switch %s port %s and switch %s port %s",
                src_dpid,
                src_port_no,
                dst_dpid,
                dst_port_no,
            )

        self.port_time[src_port_key] = now

    def _send_lldp_packets(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        ports = api.get_switch(self.topology_api_app, datapath.id)[0].ports

        for port in ports:
            port_no = port.port_no
            if port_no != ofproto.OFPP_LOCAL:  # Ignore local port
                pkt = LLDPPacket.lldp_packet(datapath, port_no, time.time())
                data = pkt.data
                actions = [parser.OFPActionOutput(port_no)]
                out = parser.OFPPacketOut(
                    datapath=datapath,
                    buffer_id=ofproto.OFP_NO_BUFFER,
                    in_port=ofproto.OFPP_CONTROLLER,
                    actions=actions,
                    data=data,
                )
                datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        datapath = ev.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        ports = api.get_switch(self.topology_api_app, datapath.id)[0].ports
        for port in ports:
            port_no = port.port_no
            if port_no != ofproto.OFPP_LOCAL:  # Ignore local port
                self.send_lldp_packet(datapath, port_no)

