

class TreeElement():

    def __init__(self, id):
        self.id = id
        self.mac_address = -1
        self.capacity = 0
        self.allocation = 0
        self.parent = -1
        self.children = []
        self.num_descendants = 0
    
    def get_id(self):   
        return self.id
    
    def set_mac_address(self, mac_address):
        self.mac_address = mac_address
    
    def get_mac_address(self):
        return self.mac_address
    
    def set_capacity(self, capacity):
        self.capacity = capacity
        
    def get_capacity(self):
        return self.capacity
    
    def set_allocation(self, allocation):
        self.allocation = allocation
        
    def get_allocation(self):
        return self.allocation
    
    def set_parent(self, parent):
        self.parent = parent
        
    def get_parent(self):
        return self.parent
        
    def add_child(self, child):   
        self.children.append(child) 
        
    def get_children(self):
        return self.children
    
    def set_descendants(self, num_descendants):
        self.num_descendants = num_descendants
        
    def get_descendants(self):
        return self.num_descendants
        
    def print_element(self):
        print("[%s: capacity=%s; parent=%s; children=%s]"%(str(self.id), str(self.capacity), str(self.parent), str(self.children)))
        
        
        