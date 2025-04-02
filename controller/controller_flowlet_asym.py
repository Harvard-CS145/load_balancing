#!/usr/bin/env python3

from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
import sys


class RoutingController(object):

    def __init__(self):
        self.topo = load_topo("topology.json")
        self.controllers = {}
        self.init()

    def init(self):
        self.connect_to_switches()
        self.reset_states()
        self.set_table_defaults()

    def connect_to_switches(self):
        for p4switch in self.topo.get_p4switches():
            thrift_port = self.topo.get_thrift_port(p4switch)
            self.controllers[p4switch] = SimpleSwitchThriftAPI(thrift_port)

    def reset_states(self):
        [controller.reset_state() for controller in self.controllers.values()]

    def set_table_defaults(self):
        for controller in self.controllers.values():
            controller.table_set_default("direct_ipv4", "drop", [])
            controller.table_set_default("group_info_to_port", "drop", [])

    def route(self):
        h1_ip_addr = self.topo.get_host_ip('h1')
        h2_ip_addr = self.topo.get_host_ip('h2')
        for sw_name, controller in self.controllers.items():
            if sw_name == 's1':
                # TODO: add routing rules for s1
                # for h1: add routing rule to the direct_ipv4 table
                

                # for h2: add routing rule to direct_ipv4 table
                

                # add rules to group_info_to_port table for each possible hash index
                

                continue
            elif sw_name == 's2':
                # TODO: add routing rules for s2
                # for h1 and h2 : add routing rules to the direct_ipv4 table
                
                continue
            elif sw_name == 's3':
                # TODO: add routing rules for s3
                # for h1 and h2 : add routing rules to the direct_ipv4 table
                
                continue
            elif sw_name == 's4':
                # TODO: add routing rules for s4
                # for h2: add routing rule to the direct_ipv4 table
                
                
                # for h1: add routing rule to direct_ipv4 table
                
                
                # add rules to group_info_to_port table for each possible hash index
                

                continue


    def main(self):
        self.route()


if __name__ == "__main__":
    controller = RoutingController().main()
