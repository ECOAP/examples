from random import *

import _thread
import sys
import gevent

def default_callback(group, node, cmd, data, interface = ""):
    print("{} DEFAULT CALLBACK : Group: {}, NodeName: {}, Cmd: {}, Returns: {}, interface: {}".format(datetime.datetime.now(), group, node.name, cmd, data, interface))


class RPLGlobalCC():


    def __init__(self, global_controller):
        self.global_controller = global_controller

        self.max_rank = 127

        _thread.start_new_thread(self.periodic_send, () )

    def periodic_send(self):
        while True:
            self.send_max_rank()
            gevent.sleep(60)

    def send_max_rank(self):

        try:
            msg = {'interface': 'lowpan0', 'command': 'SET_MAX_RANK', 'max_rank': str(self.max_rank)}
            self.global_node_manager.send_downstream(msg, default_callback)
        except:
            print("Unexpected error:")
            print(sys.exc_info()[0])

        pass

    def report(self, mac_address, measurement_report):
        for st in measurement_report:
            print("%s @ %s " % (str(mac_address), str(st)))
            if st == "rpl_rank":
                rank = int(measurement_report[st][0])
                if rank > self.max_rank:
                    self.max_rank = rank


