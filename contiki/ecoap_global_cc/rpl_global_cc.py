from random import *

import gevent
import _thread
import datetime
import wishful_controller


class RPLGlobalCC():


    def __init__(self, send_function, num_nodes):
        self.send = send_function

        self.max_rank = 127

        self.thread_started = False

        self.ranks = []

        self.pp = {}

        self.hops_to_root = {}

        self.num_flows = {}

        self.total_flows = 0

        self.num_nodes = num_nodes

        self.num_updates = 0

        self.RTOs = {}

        for i in range(1, self.num_nodes + 1):
            self.RTOs[i] = (2000, 3000, 1.5)

    def get_path(self, node):
        nh = 0
        n = node
        path = []

        if node not in self.pp:
            return path

        while n != 1 and nh < 20:
            if self.pp[n] == 0:
                path = []
                return path

            nh = nh + 1
            path.append(n)
            n = self.pp[n]

        if n != 1 :
            #LOOP
            path = []
            return path

        return path

    def update_data(self):
        for i in range(1, self.num_nodes + 1):
            self.num_flows[i] = 0
        self.total_flows = 0

        if len(self.pp) < self.num_updates:
            for i in range(1,self.num_nodes+1):
                self.RTOs[i] = (2000, 3000, 1.5)
        else:
            # calculate metrics for each node
            for i in range(1, self.num_nodes+1):
                p = self.get_path(i)
                self.hops_to_root[i] = len(p)

                if self.hops_to_root[i] > 0:
                    for h in p:
                        self.num_flows[h] = self.num_flows[h] + 1
                        self.total_flows = self.total_flows + 1

            # Calculate NEW RTO
            for i in range(1,self.num_nodes+1):
                if self.hops_to_root[i] != 0 and self.total_flows > 0:
                    self.RTOs[i] = (100 * self.hops_to_root[i], 150 * self.hops_to_root[i], round(1.5 + 1.5 * self.num_flows[i]/self.total_flows, 2) )
                else:
                    self.RTOs[i] = (2000, 3000, 1.5)


    def periodic_send(self):
        self.update_data()
        self.send_data()
        self.thread_started = False

    def send_data(self):

        for i in range(1, self.num_nodes + 1):
            msg = {'info': 'RTO', 'RTO': str(self.RTOs[i])}

            self.send((i,msg))

    def report(self, mac_address, measurement_report):
        for st in measurement_report:
            if st == "rpl_rank":
                rank = int(measurement_report[st][0])
                #if rank > self.max_rank:
                    #self.max_rank = rank
                self.ranks.append(rank)
            if st == "rpl_preferred_parent":
                p = int(measurement_report[st][0][-1])
                self.pp[mac_address] = p
                self.num_updates = self.num_updates + 1
                if self.num_updates == self.num_nodes:
                    # Trigger computation

                    if self.thread_started is False:
                        self.thread_started = True
                        _thread.start_new_thread(self.periodic_send, ())

                    self.num_updates  = 0


