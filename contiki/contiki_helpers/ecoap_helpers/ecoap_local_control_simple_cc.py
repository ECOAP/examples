__author__ = "Carlo Vallati"
__copyright__ = "Copyright (c) 2018, University of Pisa, Italy"
__version__ = "0.1.0"

# Definition of Local Control Program that is in place for monitoring and controlling CoAP Congestion Control.


def ecoap_local_monitoring_program_simple_cc(control_engine):
    # do all needed imports here!!!
    import gevent

    # Specific Congestion Control Functions
    import random as rnd
    import _thread

    def event(interface, event_name, info):
        if event_name == "coap_rx_success":
            tx_success(interface,info)
        if event_name == "coap_tx_failed":
            tx_failed(interface, info)

    def send_rto(interface,rto):
        control_engine.blocking(True).net.iface(interface).set_parameters_net({'coap_rto': rto})

        pass

    def tx_success(interface, info):

        rtt = int(info[2])

        rto = (rtt + rnd.randint(0, rtt), rtt * 2 + rnd.randint(0, rtt * 2), rtt * 3 + rnd.randint(0, rtt * 3), rtt * 4 + rnd.randint(0, rtt * 4))

        _thread.start_new_thread(send_rto, (interface,rto,))

    def tx_failed(self, interface, info):
        pass

    # end specific CC functions

    @control_engine.set_default_callback()
    def default_callback(cmd, data):
        control_engine.send_upstream({"msg_type": "cmd_result", "cmd": cmd, "result": data})
        pass

    def event_handler(interface, event_name, event_value):
        control_engine.send_upstream({"msg_type": "event", "interface": interface, "event_name": event_name, "event_value": event_value})
        event(interface,event_name, event_value)
        pass

    def report_callback(interface, report):
        control_engine.send_upstream({"msg_type": "report", "interface": interface, "report": report})
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
        elif type(msg) is dict:
            print("local monitoring unknown msg type {}".format(msg))

        gevent.sleep(1)

    print(("local monitor cp  - Name: {}, Id: {} - STOPPED".format(control_engine.name, control_engine.id)))
