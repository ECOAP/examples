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
          
        self.tree = []
    
    def set_num_nodes(self, num):
        #print("Number of nodes in the network is %s"%str(num))
        
        for i in range(1, num+1):
            self.tree.append(TreeElement(i))

    def set_interface_list(self, mac_to_inter):
        self.mac_to_inter = mac_to_inter

    def print_tree(self):
        print("\n")
        for i in range(len(self.tree)):
            self.tree[i].print_element()
        print("\n")
    
    def send_rate_allocation(self, value, interface):
        msg = {'info': 'allocation',  'rate_allocation': value, 'interface': self.mac_to_inter[interface] }
        self.send((interface,msg))
        pass
            
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
    
    def count_descendants(self, elem_id):
        if len(self.tree[elem_id-1].get_children())==0:
            #print("%s: num_descendant=0"%str(elem_id))
            self.tree[elem_id-1].set_descendants(0)
            return 0
        descendants = 0
        for child in self.tree[elem_id-1].get_children():
            descendants += self.count_descendants(child) + 1
        self.tree[elem_id-1].set_descendants(descendants)
        #print("%s: num_descendant=%s"%(str(elem_id),str(descendants)))
        return descendants
    
    def reset_allocation(self):
        for i in range(len(self.tree)):
            self.tree[i-1].set_allocation(0)
    
    def compute_allocation(self, elem_id):
        print("\nComputing the allocation for node %s and its children"%str(elem_id))
        
        allocatable_rate = self.tree[elem_id-1].get_allocation()
        if allocatable_rate == 0:
            #no previous allocation: start from the capacity
            allocatable_rate = self.tree[elem_id-1].get_capacity()
        print("%s: allocatable_rate=%s"%(str(elem_id), str(allocatable_rate)))
        
        if len(self.tree[elem_id-1].get_children())==0:
            #leaf node, nothing to do
            print("%s: children=0"%str(elem_id))
            self.tree[elem_id-1].set_allocation(allocatable_rate)
            print("%s: allocated_rate=%s"%(str(elem_id), str(self.tree[elem_id-1].get_allocation())))
            return
        
        #the allocatable rate should be divided equally among the node and the descendants
        #so it is reset for now
        self.tree[elem_id-1].set_allocation(0)
        
        requiring_allocation = [elem_id] + self.tree[elem_id-1].get_children()
        residual_demand = [allocatable_rate]
        for child in self.tree[elem_id-1].get_children():
            capacity = self.tree[child-1].get_capacity()
            descendants = self.tree[child-1].get_descendants()
            residual_demand.append(capacity/(descendants+1))
        print("%s: requiring_allocation=%s; residual_demand=%s"%(str(elem_id), str(requiring_allocation), str(residual_demand)))
            
        while len(requiring_allocation)!=0 and allocatable_rate > 0:
            #there are still nodes requiring allocation and there is still rate that can be
            #allocated
            
            r = min(residual_demand)
            k = requiring_allocation[residual_demand.index(r)]
            print("%s: r=%s; k=%s"%(str(elem_id), str(r), str(k)))
            
            considered_nodes = 1
            for elem in requiring_allocation[1:]:
                #print("%s: element requiring allocation=%s"%(str(elem_id), str(elem)))
                descendants = self.tree[elem-1].get_descendants()+1
                considered_nodes += descendants
            print("%s: considered_nodes=%s"%(str(elem_id), str(considered_nodes)))
            delta = 0
            to_remove = []
            if r*considered_nodes <= allocatable_rate:
                delta = r
                to_remove.append(k)
                #print("%s: to_remove=%s"%(str(elem_id), str(to_remove)))
            else:
                delta = allocatable_rate/considered_nodes
            print("%s: delta=%s"%(str(elem_id), str(delta)))
                
            for elem in requiring_allocation:
                allocation = self.tree[elem-1].get_allocation()
                if elem==elem_id:
                    allocation += delta
                else:
                    allocation += delta*(self.tree[elem-1].get_descendants()+1)
                self.tree[elem-1].set_allocation(allocation)
                print("%s: temporary_allocation_%s=%s"%(str(elem_id), str(elem), str(allocation)))
            
            for i in range(len(residual_demand)):
                residual_demand[i] -= delta
            #print("%s: residual_demand=%s"%(str(elem_id), str(residual_demand)))
            if len(to_remove)!=0:
                elem_to_remove = to_remove.pop(0)
                #print("%s: elem_to_remove=%s"%(str(elem_id), str(elem_to_remove)))
                index_elem_to_remove = requiring_allocation.index(elem_to_remove)
                #print("%s: index_elem_to_remove=%s"%(str(elem_id), str(index_elem_to_remove)))
                del residual_demand[index_elem_to_remove]
                requiring_allocation.remove(elem_to_remove)
                #print("%s: requiring_allocation=%s; residual_demand=%s"%(str(elem_id), str(requiring_allocation), str(residual_demand)))
            allocatable_rate -= delta*considered_nodes
            print("%s: allocatable_rate=%s"%(str(elem_id), str(allocatable_rate)))
        
        #allocation for the current node is complete; repeat the procedure for every children
        print("%s: allocated_rate=%s"%(str(elem_id), str(self.tree[elem_id-1].get_allocation())))
        for child in self.tree[elem_id-1].get_children():
            self.compute_allocation(child)
        
    def periodic_send(self):
        print("Periodic send started")
        while True:
            gevent.sleep(30)
            
            #reinitialize the tree to work with the new information
            self.update_children()
            self.reset_allocation()
            root_children = self.search_root_children()
            print("Root children %s"%str(root_children))
            
            #run the algorithm to compute the new allocations
            for elem in root_children:
                descendants = self.count_descendants(elem)
                self.compute_allocation(elem)
            
            #send the new allocation to nodes
            print("\n")
            for i in range(len(self.tree)):
                mac_address = self.tree[i].get_mac_address()
                if mac_address != -1 :
                    self.send_rate_allocation(int(self.tree[i].get_allocation()), self.tree[i].get_mac_address())

    def report_capacity(self, mac_address, event_value):
        if self.thread_started is False:
            _thread.start_new_thread(self.periodic_send, ())
            self.thread_started = True
        
        print("%s: capacity=%s"%(str(mac_address), str(event_value)))
        self.tree[mac_address-1].set_mac_address(mac_address)
        self.tree[mac_address-1].set_capacity(event_value)

    def report(self, mac_address, measurement_report):
        for st in measurement_report:
            if st == "rpl_preferred_parent":
                if len(measurement_report[st])!=0:
                    print("%s: preferred_parent=%s"%(str(mac_address),str(measurement_report[st][0][15])))
                    self.tree[mac_address-1].set_parent(measurement_report[st][0][15])


