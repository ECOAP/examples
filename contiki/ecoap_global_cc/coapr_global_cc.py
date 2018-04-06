from random import *

import gevent
import _thread
import datetime
import wishful_controller
from contiki.ecoap_global_cc.tree_element import *
from asyncio.locks import Event


class COAPRGlobalCC():


    def __init__(self, send_function):
        self.send = send_function
        self.thread_started = False
        
        self.nodes = 0    
        self.tree = []
    
    def set_num_nodes(self, num):
        self.nodes = num
        print("Number of nodes in the network is %s"%str(num))
        
        for i in range(1,num+1):
            self.tree.append(TreeElement(i))
        
    def print_tree(self):
        for i in range(len(self.tree)):
            self.tree[i].print_element()
            
    def update_children(self):
        for i in range(len(self.tree)):
                self.tree[i].children.clear()
        for i in range(len(self.tree)):
            if self.tree[i].get_parent()!=-1 and self.tree[i].get_parent()!=0:
                parent = self.tree[i].get_parent()
                self.tree[parent-1].add_child(i+1)
        self.print_tree()
    
    def search_root_children(self):  
        children = []    
        for elem in self.tree:
            if elem.get_parent() == 0:
                children.append(elem.get_id())
        return children
    
    def send_rate_allocation(self, value, interface):
        msg = {'info': 'allocation', 'interface': interface, 'rate_allocation': value}
        self.send(msg)
        pass
    
    def compute_allocation(self, elem):
        print("Computing the allocation for children of node %s"%str(elem))
        if len(self.tree[elem-1].get_children())==0:
            print("Elem %s has no children"%str(elem))
            return
        print("%s: children %s"%(str(elem),str(self.tree[elem-1].get_children())))
        node_allocation = self.tree[elem-1].get_allocation()
        print("%s: node allocation %s"%(str(elem),str(node_allocation)))
        sum_children_capacity = 0
        for child in self.tree[elem-1].get_children():
            sum_children_capacity += self.tree[child-1].get_capacity()
        print("%s: sum children capacity %s"%(str(elem),str(sum_children_capacity)))
        for child in self.tree[elem-1].get_children():
            allocation = 0
            if node_allocation >= sum_children_capacity:
                allocation = self.tree[child-1].get_capacity()
            else:
                allocation = node_allocation/sum_children_capacity*self.tree[child-1].get_capacity()
            self.tree[child-1].set_allocation(allocation)
            print("In compute allocation: element %s is allocated %s"%(str(child),str(allocation)))
            self.compute_allocation(child)            

    def periodic_send(self):
        print("Periodic send started")
        while True:
            gevent.sleep(60)
            
            self.update_children()
            root_children = self.search_root_children()
            print("Root children %s"%str(root_children))
            for elem in root_children:
                self.tree[elem-1].set_allocation(self.tree[elem-1].get_capacity())
                print("Element %s is allocated %s"%(str(elem),str(self.tree[elem-1].get_capacity())))
                self.compute_allocation(elem)
            
            for i in range(len(self.tree)):
                mac_address = self.tree[i].get_mac_address()
                if mac_address != -1 :
                    self.send_rate_allocation(self.tree[i].get_allocation(), self.tree[i].get_mac_address())

    def report_capacity(self, mac_address, event_value):
        if self.thread_started is False:
            _thread.start_new_thread(self.periodic_send, ())
            self.thread_started = True
        
        print("mac=%s: capacity=%s"%(str(mac_address), str(event_value)))
        self.tree[mac_address-1].set_mac_address(mac_address)
        self.tree[mac_address-1].set_capacity(event_value)

    def report(self, mac_address, measurement_report):
        for st in measurement_report:
            if st == "rpl_preferred_parent":
                if len(measurement_report[st])!=0:
                    print("mac=%s: preferred_parent=%s"%(str(mac_address),str(measurement_report[st][0][15])))
                    self.tree[mac_address-1].set_parent(measurement_report[st][0][15])

        #if self.thread_started is False:
            #_thread.start_new_thread(self.periodic_send, ())
            #self.thread_started = True


