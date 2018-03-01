from gevent.threading import Lock
from .base_cc import BaseCC
from random import *

import _thread
import sys



class SimpleCC(BaseCC):
    def __init__(self, app_manager):
        self.app_manager = app_manager
        self.lock = False

    def send_rto(self, node_id, rto):
        #while self.lock is True:
        #    pass

        #try:
        #    self.app_manager.update_async_configuration({"coap_rto": rto}, [node_id])
        #except:
        #    print("Unexpected error:")
        #    print(sys.exc_info()[0])

        pass

    def event(self, event_name, info):

        if event_name == "coap_rx_success":
            self.tx_success(info)
        if event_name == "coap_tx_failed":
            self.tx_failed(info)


    def tx_success(self, info):
        print(str(info))
        rtt = int(info[2])
        node_id = int(info[0])

        rto = (rtt + randint(0,rtt) , rtt * 2 + randint(0,rtt*2) , rtt * 3 + randint(0,rtt * 3),  rtt * 4 + randint(0,rtt * 4))

        _thread.start_new_thread(self.send_rto, (node_id, rto,))

    def tx_failed(self, info):
        pass

