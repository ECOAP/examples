

def ecoap_local_monitoring_program_coapr_cc(control_engine):
    # do all needed imports here!!!
    import gevent

    # Specific Congestion Control Functions
    import random as rnd
    import _thread

    packet_service_time = -1
    alpha_A = 0.01
    beta = 1.2
    long_term_forecast = 0
    alpha_W = 0
    maximum_capacity = 0
    
    omega = 1.1
    eta = 1.1
    sending_rate = 0
    
    thread_started = False

    def event(interface, event_name, info):

        #if interface is None:
        #interface = "lowpan1" # testbed

        if event_name == "coap_rx_success":
            tx_success(interface, info)
        if event_name == "coap_tx_failed":
            tx_failed(interface, info)

    def new_rate_allocation(rate_allocation, interface, inter):
        nonlocal omega, eta, sending_rate
        
        print("\n")
        print("%s: sending_rate=%s"%(str(interface), str(sending_rate)))
        print("%s: allocatable_rate=%s"%(str(interface), str(rate_allocation)))
        
        #the rate is changed according to its history
        delta = sending_rate - rate_allocation
        print("%s: delta=%s (%s-%s)"%(str(interface),str(delta),str(sending_rate),str(rate_allocation)))
        #rate_allocation can be temporarily zero for cycles in the DOGAG
        if sending_rate > rate_allocation:
            if rate_allocation!=0 and sending_rate/rate_allocation > omega:
                sending_rate = sending_rate - abs(delta)/eta
        else: #sending rate < rate_allocation
            sending_rate = sending_rate + abs(delta)/eta    
        
        print("%s: sending_rate=%s"%(str(interface), str(int(sending_rate))))
        
        control_engine.blocking(True).net.iface(inter).set_parameters_net({'coap_max_rate': int(sending_rate)})
        
    def update_service_time(interface, time):
        nonlocal packet_service_time

        print("%s: service_time=%s"%(str(interface), str(time)))
        packet_service_time = time

    def send_rto(interface,rto):
        control_engine.blocking(True).net.iface(interface).set_parameters_net({'coap_rto': rto})

        # Send back to the controller the rto for statistical purposes
        control_engine.send_upstream( {"msg_type": "event", "interface": interface, "event_name": 'coap_rto', "event_value": rto})
        pass
    
    def send_capacity(interface):
        nonlocal alpha_A, beta, long_term_forecast, alpha_W, maximum_capacity, sending_rate
        
        print("%s thread 'send_capacity' started"%str(interface))
        
        while True:
            gevent.sleep(30)
            
            if packet_service_time != -1:
                #throughput expressed in b/s
                print("\n")
                print("%s: packet_service_time=%s"%(str(interface), str(packet_service_time)))
                if packet_service_time != 0:
                    instantaneous_throughput = 35/(packet_service_time/1000)
                else:
                    instantaneous_throughput = 35/(0.5/1000)
                print("%s: instantaneous_throughput=%s"%(str(interface), str(instantaneous_throughput)))
                long_term_forecast = alpha_A*instantaneous_throughput + (1-alpha_A)*long_term_forecast
                print("%s: long_term_forecast=%s"%(str(interface), str(long_term_forecast)))
                
                #to remove the fluctuations on the average link capacity use a weighted moving-average
                if instantaneous_throughput >= long_term_forecast:
                    alpha_W = alpha_A
                else:
                    alpha_W = beta * alpha_A
                
                maximum_capacity = alpha_W*instantaneous_throughput+(1-alpha_W)*maximum_capacity
                maximum_capacity_t = tuple([int(maximum_capacity)])
                print("%s: alpha_W=%s; capacity=%s"%(str(interface), str(alpha_W), str(maximum_capacity)))
                
                #the first time you need to initialize the sending_rate with the already computed value
                if sending_rate == 0:
                    sending_rate = int(maximum_capacity)
                print("Sending rate %s"%str(sending_rate))
                
                #send the computed average sending rate to the global controller       
                msg = {"msg_type": "event", "interface": interface, "event_name": 'capacity', "event_value": maximum_capacity_t}
                print("[US] %s: capacity %s"%(str(interface),str(msg)))
                control_engine.send_upstream(msg)
        pass

    def tx_success(interface, info):

        interval = rnd.randint(2000, 3000)

        rto = (interval, interval * 2, interval * 4, interval * 8)

        _thread.start_new_thread(send_rto, (interface, rto,))

    def tx_failed(interface, info):

        interval = rnd.randint(2000, 3000)

        rto = (interval, interval * 2, interval * 4, interval * 8)

        _thread.start_new_thread(send_rto, (interface, rto,))
        
    # end specific CC functions

    @control_engine.set_default_callback()
    def default_callback(cmd, data):
        control_engine.send_upstream({"msg_type": "cmd_result", "cmd": cmd, "result": data})
        pass

    def event_handler(interface, event_name, event_value):
        control_engine.send_upstream({"msg_type": "event", "interface": interface, "event_name": event_name, "event_value": event_value})
        event(interface, event_name, event_value)
        pass

    def report_callback(interface, report):
        nonlocal thread_started
        control_engine.send_upstream({"msg_type": "report", "interface": interface, "report": report})
        
        if thread_started is False:
            _thread.start_new_thread(send_capacity, (interface,))
            thread_started = True
                
        for st in report:
            if st == "IEEE802154_measurement_macStats":
                update_service_time(interface, int(report[st][0][0]))
        pass
    

    print(("local monitor cp started - Name: {}, Id: {} - STARTED".format(control_engine.name, control_engine.id)))

    # control loop
    while not control_engine.is_stopped():
        msg = control_engine.recv(block=False)
        if msg is not None and type(msg) is dict and 'command' in msg:
            if 'interface' in msg:
                ifaces = msg['interface']
            else:
                ifaces = control_engine.blocking(True).radio.iface("lowpan0").get_radio_platforms()
            if msg['command'] == 'SUBSCRIBE_EVENT':
                for iface in ifaces:
                    if msg['upi_type'] == 'net':
                        control_engine.blocking(False).net.iface(iface).subscribe_events_net(msg['event_key_list'], event_handler, msg['event_duration'])
                    elif msg['upi_type'] == 'radio':
                        control_engine.blocking(False).radio.iface(iface).subscribe_events(msg['event_key_list'], event_handler, msg['event_duration'])
                    else:
                        print("async event listener unsupported upi_type {}".format(msg['upi_type']))
            elif msg['command'] == 'GET_MEASUREMENTS_PERIODIC':
                for iface in ifaces:
                    if msg['upi_type'] == 'net':
                        control_engine.blocking(False).iface(iface).net.get_measurements_periodic_net(msg['measurement_key_list'], msg['collect_period'], msg['report_period'], msg['num_iterations'], report_callback)
                    elif msg['upi_type'] == 'radio':
                        control_engine.blocking(False).iface(iface).radio.get_measurements_periodic(msg['measurement_key_list'], msg['collect_period'], msg['report_period'], msg['num_iterations'], report_callback)
                    else:
                        print("periodic measurement collector unsupported upi_type {}".format(msg['upi_type']))
            else:
                print("local monitoring unknown command {}".format(msg['command']))

        #MESSAGE FROM THE GLOBAL CONTROLLER
        elif msg is not None and type(msg) is dict and 'info' in msg:
            if msg['info'] == 'allocation':

                print(str(msg))

                if 'interface' in msg:
                    inter = msg['interface']
                else:
                    inter = 'lowpan0'

                #new_rate_allocation(msg['rate_allocation'], control_engine.id, inter)

                _thread.start_new_thread(new_rate_allocation, (msg['rate_allocation'], control_engine.id, inter,))

        elif msg is not None and type(msg) is dict:
            print("local monitoring unknown msg type {}".format(msg))



        gevent.sleep(1)

    print(("local monitor cp  - Name: {}, Id: {} - STOPPED".format(control_engine.name, control_engine.id)))


