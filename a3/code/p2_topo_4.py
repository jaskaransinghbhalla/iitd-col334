##!/usr/bin/python

# Dual Cycle with 6 switches

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.clean import cleanup

class ComplexTopo(Topo):
    """Custom topology with 7 switches forming a complex structure and 1 host per switch."""

    def build(self):
        # Create switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')
        s5 = self.addSwitch('s5')
        s6 = self.addSwitch('s6')

        # Create 6 hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')
        h5 = self.addHost('h5')
        h6 = self.addHost('h6')
        h7 = self.addHost('h7')
        h8 = self.addHost('h8')
        h9 = self.addHost('h9')
        h10 = self.addHost('h10')
        h11 = self.addHost('h11')
        h12 = self.addHost('h12')
        h13 = self.addHost('h13')
        h14 = self.addHost('h14')
        h15 = self.addHost('h15')
        h16 = self.addHost('h16')
        h17 = self.addHost('h17')
        h18 = self.addHost('h18')

        # Connect each host to its respective switch
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s1)
        self.addLink(h4, s2)
        self.addLink(h5, s2)
        self.addLink(h6, s2)
        self.addLink(h7, s3)
        self.addLink(h8, s3)
        self.addLink(h9, s3)
        self.addLink(h10, s4)
        self.addLink(h11, s4)
        self.addLink(h12, s4)
        self.addLink(h13, s5)
        self.addLink(h14, s5)
        self.addLink(h15, s5)
        self.addLink(h16, s6)
        self.addLink(h17, s6)
        self.addLink(h18, s6)
        


        # Connect switches to form a complex topology
        self.addLink(s1, s2)
        self.addLink(s2, s3)
        self.addLink(s3, s4)
        self.addLink(s4, s5)
        self.addLink(s5, s6)
        self.addLink(s6, s1)
        self.addLink(s3, s5)
        self.addLink(s1, s4)
        self.addLink(s2, s6)
        self.addLink(s3, s6)
        self.addLink(s2, s5)
        self.addLink(s3, s1)
        self.addLink(s5, s1)
        self.addLink(s2, s4)
        self.addLink(s6, s4)

        # Additional connections to create more complexity and potential loops
        # self.addLink(s1, s3)
        # self.addLink(s2, s4)
        # self.addLink(s3, s5)
        # self.addLink(s4, s6)

def run():
    """Create the network, start it, and enter the CLI."""
    topo = ComplexTopo()
    net = Mininet(topo=topo, switch=OVSSwitch, build=False)
    net.addController('c0', controller=RemoteController, ip="127.0.0.1", protocol='tcp', port=6633)
    net.build()
    net.start()
    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    cleanup()
    # Set log level to display Mininet output
    setLogLevel('info')
    run()