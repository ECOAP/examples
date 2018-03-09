from random import *

import _thread
import sys
import gevent


class RPLGlobalCC():


    def __init__(self, global_controller):
        self.global_controller = global_controller

        self.max_rank = 127

        self.thread_started = False

    def periodic_send(self):
        while True:
            print("invio")
            self.send_max_rank()
            gevent.sleep(60)

    def send_max_rank(self):
        print("send max rank")
        msg = {'info': "rpl", 'max_rank': str(self.max_rank)}
        self.global_controller.send_downstream(msg)

        pass

    def report(self, mac_address, measurement_report):
        for st in measurement_report:
            print("%s @ %s " % (str(mac_address), str(st)))
            if st == "rpl_rank":
                rank = int(measurement_report[st][0])
                if rank > self.max_rank:
                    self.max_rank = rank

        if self.thread_started is False:
            print("start thread")
            _thread.start_new_thread(self.periodic_send, ())
            self.thread_started = True


