__author__ = "Giacomo Tanganelli"
__copyright__ = "Copyright (c) 2018, University of Pisa, Italy"
__version__ = "0.1.0"

# Definition of Local Control Program that is in place for monitoring and controlling CoAP Congestion Control.


def ecoap_local_monitoring_program_cocoa_cc(control_engine):
    # do all needed imports here!!!
    import gevent

    # Specific Congestion Control Functions
    import random as rnd
    import _thread
    import time
    import math

    rto_strong = 2000
    rto_weak = 2000
    rto_overall = 2000
    rtt_strong = None
    rtt_weak = None
    rttvar_strong = None
    rttvar_weak = None
    timestamp = 0
    agingThread_started = False

    def event(interface, event_name, info):

        #if interface is None:
        #interface = "lowpan1" # testbed

        if event_name == "coap_rx_success":
            tx_success(interface,info)
        if event_name == "coap_tx_failed":
            tx_failed(interface, info)

    def send_rto(interface, rto):

        control_engine.blocking(True).net.iface(interface).set_parameters_net({'coap_rto': rto})

        # Send back to the controller the rto for statistical purposes
        control_engine.send_upstream( {"msg_type": "event", "interface": interface, "event_name": 'coap_rto', "event_value": rto})


        pass

    def agingThread(interface):
        nonlocal timestamp
        nonlocal rto_overall

        DEFAULT = 2000
        THRESHOLD = 30000

        while True:
            now = int(round(time.time() * 1000))
            if rto_overall > DEFAULT and now - timestamp > THRESHOLD:
                rto_overall = int((2 + rto_overall) / rto_overall)
                rto = compute_rto_init(rto_overall)
                timestamp = now
                _thread.start_new_thread(send_rto, (interface, rto,))
            elif rto_overall < 1000 and now - timestamp > 16*rto_overall:
                rto_overall = 1000
                rto = compute_rto_init(rto_overall)
                timestamp = now
                _thread.start_new_thread(send_rto, (interface, rto,))
            gevent.sleep(100)


    def tx_success(interface, info):

        nonlocal rto_strong
        nonlocal rto_weak
        nonlocal rto_overall
        nonlocal rtt_strong
        nonlocal rtt_weak
        nonlocal rttvar_strong
        nonlocal rttvar_weak
        nonlocal timestamp
        nonlocal agingThread_started

        alpha = 0.25
        beta = 0.125
        k_strong = 4
        k_weak = 1
        lambda_strong = 0.5
        lambda_weak = 0.25

        r = int(info[2])
        retransmissions = int(info[3]) > 0
        if rtt_strong is None:
            rtt_strong = r
            rttvar_strong = float(r / 2)
            rtt_weak = r
            rttvar_weak = float(r / 2)
        elif not retransmissions:
            rtt_strong = (1 - alpha) * rtt_strong + alpha * r
            rttvar_strong = (1 - beta) * rttvar_strong + beta * abs(rtt_strong - r)
            rto_strong = rtt_strong + k_strong * rttvar_strong
            rto_overall = int(lambda_strong * rto_strong + (1 - lambda_strong) * rto_overall)
        else:
            rtt_weak = (1 - alpha) * rtt_weak + alpha * r
            rttvar_weak = (1 - beta) * rttvar_weak + beta * abs(rtt_weak - r)
            rto_weak = rtt_weak + k_weak * rttvar_weak
            rto_overall = int(lambda_weak * rto_weak + (1 - lambda_weak) * rto_overall)
        timestamp = int(round(time.time() * 1000))

        rto = compute_rto_init(rto_overall)

        _thread.start_new_thread(send_rto, (interface, rto,))
        if not agingThread_started:
            _thread.start_new_thread(agingThread, (interface,))
            agingThread_started = True

    def tx_failed(interface, info):

        pass

    # end specific CC functions

    def compute_rto_init(rto):

        FACTOR = 1.5
        rto_init = rnd.randrange(rto, int(math.ceil(FACTOR * rto)))
        if int(rto) < 1000:
            vbf = 3
        elif 1000 >= int(rto) <= 3000:
            vbf = 2
        else:
            vbf = 1.3

        rto_lst = [rto_init]
        rto_previous = rto_init
        for i in range(1, 4):
            rto_new = int(rto_previous * vbf)
            rto_previous = rto_new
            if rto_new < 4294967295:
                rto_lst.append(rto_new)
            else:
                rto_lst.append(4294967295)
        rto_tuple = tuple(rto_lst)
        return rto_tuple

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
