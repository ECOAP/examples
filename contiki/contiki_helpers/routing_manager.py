
class RoutingManager(object):
    def __init__(self, am, global_ipv6_prefix, ipv6_prefix, mac_prefix):
        self.app_manager = am
        self.pp = {} # dictionary self.pp[mac_address] = pp
        self.ipv6_prefix = ipv6_prefix #[0xfe80, 0x0000, 0x0000, 0x0000, 0xa9cd, 0x00ff, 0xfe00, 0x0000]
        self.mac_prefix = mac_prefix # [0xab, 0xcd, 0x00, 0xff, 0xfe, 0x00, 0x00, 0x00]
        self.global_ipv6_prefix = global_ipv6_prefix #[0xfd00, 0x0000, 0x0000, 0x0000, 0xa9cd, 0x00ff, 0xfe00, 0x0000]

    def load_routes_from_file(self, filename):
        f = open(str(filename), 'r')
        routes = f.readlines()
        for r in routes:
            (node, pp) = eval(r.strip()) #(node_id, pp)

            self.pp[node] = pp

        print(self.pp)

    def get_path(self, node):
        nh = 0
        n = node
        path = []

        if node not in self.pp:
            return path

        while n != 1 and nh < 20:
            if n not in self.pp or self.pp[n] == 0:
                path = []
                return path

            nh = nh + 1
            path.append(n)
            n = self.pp[n]

        if n != 1 :
            #LOOP
            path = []
            return path

        path.append(1)

        return path


    def apply_def_route(self):
        for r in self.pp:
            # set PP route
            addr = self.ipv6_prefix
            addr[-1] = self.pp[r]
            mac = self.mac_prefix
            mac[-1] = self.pp[r]
            self.app_manager.add_neighbor(addr,mac, [1], r)
            self.app_manager.add_route([0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000], [1], addr, r )

    def apply_reverse_route(self):
        for r in self.pp:
            path = self.get_path(r) # get path

            rpath = list(reversed(path))

            print(str(r))
            print(str(rpath))

            cur=rpath[0]
            for n in rpath[1:]:
                # set reverse route
                print("set to "+str(cur)+" dst "+str(r) + " via "+str(n))
                addr = self.ipv6_prefix
                addr[-1] = n
                mac = self.mac_prefix
                mac[-1] = n
                global_addr = self.global_ipv6_prefix
                global_addr[-1] = r
                self.app_manager.add_neighbor(addr,mac, [1], cur)
                self.app_manager.add_route(global_addr, [128], addr, cur)
                cur = n

    def clear_tables(self):
        self.app_manager.clear_table()

