#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
global_cp.py: Example Contiki global control program

Usage:
   global_cp.py [options] [-q | -v]

Options:
   --logfile name Name of the logfile
   --config configFile Config file path
   --nodes nodesFile   Config file with node info
   --abs_log_dir Absolute path of the logging directory
   --measurements measurementsConfig Config file with measurement info
   --param_config_file Parameter configuration file (csv)
   --event_config_file Events configuration file (csv)
   --congestion_policy Congestion policy

Example:
   python global_cp.py --config config/localhost/global_cp_config.yaml

Other options:
   -h, --help          show this help message and exit
   -q, --quiet         print less text
   -v, --verbose       print more text
   --version           show version and exit
"""
import logging
import yaml
import gevent
import datetime
import numpy
import wishful_upis as upis
import signal
import _thread
import csv
import os
import sys
import random as rand
import sys
import subprocess

from gevent import monkey, sleep
from contiki.ecoap_global_cc.rpl_global_cc import *
from measurement_logger import *
from stdout_measurement_logger import *
from file_measurement_logger import *
from gnuplot_measurement_logger import *
from mysql_measurement_logger import *
from contiki.contiki_helpers.global_node_manager import *
from contiki.contiki_helpers.taisc_manager import *
from contiki.contiki_helpers.app_manager import *
from contiki.contiki_helpers.ecoap_helpers.ecoap_local_control_simple_cc import ecoap_local_monitoring_program_simple_cc
from contiki.contiki_helpers.ecoap_helpers.ecoap_local_control_default_cc import ecoap_local_monitoring_program_default_cc
from contiki.contiki_helpers.ecoap_helpers.ecoap_local_control_rpl_cc import ecoap_local_monitoring_program_rpl_cc
from contiki.contiki_helpers.ecoap_helpers.ecoap_local_control_cocoa_cc import ecoap_local_monitoring_program_cocoa_cc

__author__ = "Carlo Vallati & Francesca Righetti"
__copyright__ = "Copyright (c) 2018, UNIPI"
__version__ = "0.1.0"
__email__ = "carlo.vallati@unipi.it"

log = logging.getLogger('contiki_global_control_program')

param_config_file = None
cc_manager = None

message_queue = []


def add_message(msg):
    message_queue.append(msg)


def default_callback(group, node, cmd, data, interface=""):
    print("{} DEFAULT CALLBACK : Group: {}, NodeName: {}, Cmd: {}, Returns: {}, interface: {}".format(datetime.datetime.now(), group, node.name, cmd, data, interface))


def handle_event(mac_address, event_name, event_value):
    print("%s @ %s: %s" % (str(mac_address), event_name, str(event_value)))
    e = (mac_address,) + event_value

    measurement_logger.log_measurement(event_name, e)


def handle_measurement(mac_address, measurement_report):
    for st in measurement_report:
        print("%s @ %s " % (str(mac_address), str(st)))
        if len(measurement_report[st]) > 0:
            m = (mac_address,) + (measurement_report[st][0],)
            measurement_logger.log_measurement(str(st), m)

    if cc_manager is not None:
        cc_manager.report(mac_address, measurement_report)


def event_cb(mac_address, event_name, event_value):
    _thread.start_new_thread(handle_event, (mac_address, event_name, event_value))


def main():
    global cc_manager, message_queue
    try:
        from docopt import docopt
    except:
        print("""
        Please install docopt using:
            pip install docopt==0.6.1
        For more refer to:
        https://github.com/docopt/docopt
        """)
        raise

    ##############################
    # Load script configuration: #
    ##############################

    script_arguments = docopt(__doc__, version=__version__)
    load_config(script_arguments)

    ##############################
    # Start script:              #
    ##############################

    try:
        # Setup the sensor node helpers:
        global_node_manager = GlobalNodeManager(config)
        app_manager = AppManager(global_node_manager)
        taisc_manager = TAISCMACManager(global_node_manager, "CSMA")

        # Configure the default callback:
        global_node_manager.set_default_callback(default_callback)

        # Wait for the agents to connect to the global controller:
        global_node_manager.wait_for_agents(node_config['ip_address_list'])

        # Configure the first sensor node as border router and start the local monitoring control programs:
        border_router_id = 1
        print("Set node %d as border router" % (border_router_id))
        app_manager.rpl_set_border_router([0xfd, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00], border_router_id)

        if cc_policy == "rpl":
            global_node_manager.set_local_control_process(ecoap_local_monitoring_program_rpl_cc)
            cc_manager = RPLGlobalCC(add_message, len(global_node_manager.get_mac_address_list()))
        elif cc_policy == "cocoa":
            global_node_manager.set_local_control_process(ecoap_local_monitoring_program_cocoa_cc)
        elif cc_policy == "simple":
            global_node_manager.set_local_control_process(ecoap_local_monitoring_program_simple_cc)
        # elif cc_policy == "default":
        else:
            global_node_manager.set_local_control_process(ecoap_local_monitoring_program_default_cc)

        global_node_manager.start_local_monitoring_cp()

        gevent.sleep(3)

        # Load the sensor node settings:
        if param_config_file is not None:
            with open(param_config_file, 'r') as csvfile:
                settings = csv.reader(csvfile, delimiter=',')
                for setting_iterator in settings:
                    setting = list(setting_iterator)
                    if setting[0] == "mac":
                        err = taisc_manager.update_macconfiguration({setting[1]: int(setting[2])})
                    elif setting[0] == "app":
                        err = app_manager.update_configuration({setting[1]: int(setting[2])})
                    print("Setting %s to %s (%s)" % (setting[1], setting[2], err))

                    # Register events:
        if event_config_file is not None:
            with open(event_config_file, 'r') as csvfile:
                event_settings = csv.reader(csvfile, delimiter=',')
                for event_setting_it in event_settings:
                    event_setting = list(event_setting_it)
                    print(event_setting)
                    if event_setting[0] == "1":
                        ret_events = taisc_manager.subscribe_events([event_setting[1]], event_cb, 0)
                        ret_events = app_manager.subscribe_events([event_setting[1]], event_cb, 0)
                        print("Suscribe event %s returns %s" % (event_setting[1], ret_events))

        # for m in measurement_logger.measurement_definitions:
        app_manager.get_measurements_periodic(measurement_logger.measurement_definitions, 60, 60, 100000,handle_measurement)  # TODO experiment duration
        taisc_manager.get_measurements_periodic(measurement_logger.measurement_definitions, 60, 60, 100000, handle_measurement)  # TODO experiment duration

        # Set routing operations (it sould be done on the root node, here we assume that the agent of the root runs on the same host of the controller)
        if int(subprocess.check_output("sudo ip -6 addr add fd00::1/8 dev tun0 2> /dev/null; echo $?", shell=True,
                                       universal_newlines=True).strip()) > 0:
            subprocess.check_output("sudo ip -6 addr add fd00::1/8 dev tun0", shell=True,
                                    universal_newlines=True).strip()
        if int(subprocess.check_output("sudo ip6tables -C INPUT -d fd00::/8 -j ACCEPT 2> /dev/null; echo $?",
                                       shell=True, universal_newlines=True).strip()) > 0:
            subprocess.check_output("sudo ip6tables -I INPUT 1 -d fd00::/8 -j ACCEPT", shell=True,
                                    universal_newlines=True).strip()
        if int(subprocess.check_output("sudo ip6tables -C OUTPUT -s fd00::/8 -j ACCEPT 2> /dev/null; echo $?",
                                           shell=True, universal_newlines=True).strip()) > 0:
            subprocess.check_output("sudo ip6tables -I OUTPUT 1 -s fd00::/8 -j ACCEPT", shell=True,
                            universal_newlines=True).strip()

        gevent.sleep(10)

        print("Starting udp example")
        print("Activating server")

        global_node_manager.control_engine.delay(1).node(global_node_manager.connected_nodes[global_node_manager.mac_address_to_node_id[1]]).iface('lo').net.create_packetflow_sink(port=5683)

        #global_node_manager.control_engine.delay(1).node(global_node_manager.connected_nodes[global_node_manager.mac_address_to_node_id[1]]).iface('lo').net.subscribe_events_net('coap_message_rx', event_cb, 0)

        #app_manager.subscribe_events_interface(['coap_block_rx'], event_cb, 'lo', global_node_manager.mac_address_to_node_id[1] )

        #gevent.sleep(2)

        #global_node_manager.control_engine.delay(1).node(global_node_manager.connected_nodes[global_node_manager.mac_address_to_node_id[16]]).iface('lo').net.get_measurements_periodic_net(["app_stats"], 60, 60, 100000)

        gevent.sleep(2)

        print("Activating clients")
        for i in range(2, len(global_node_manager.get_mac_address_list()) + 1):
            app_manager.update_configuration({"app_activate": 2}, i)
            gevent.sleep(rand.uniform(0.1, 5))


        # Run the experiment until keyboard interrupt is triggered:
        while True:
            #global global_node_manager
            #ret = global_node_manager.control_engine.blocking(True).node(global_node_manager.connected_nodes[global_node_manager.mac_address_to_node_id[16]]).iface('lo').net.get_measurements_net(['app_stats'])
            #print(str(ret))
            while message_queue:
                mess = message_queue.pop(0)
                if type(mess) is dict:
                    # Message to all
                    global_node_manager.send_downstream(mess)
                else:
                    global_node_manager.send_downstream(mess[1],[mess[0]])
            gevent.sleep(5)


    except KeyboardInterrupt:
        log.debug("Exit")
        global_node_manager.stop()
        log.debug("Controller exits")

        if int(subprocess.check_output("sudo ip -6 addr del fd00::1/8 dev tun0 2> /dev/null; echo $?", shell=True,
                                       universal_newlines=True).strip()) > 0:
            subprocess.check_output("sudo ip -6 addr del fd00::1/8 dev tun0", shell=True,
                            universal_newlines=True).strip()
        if int(subprocess.check_output("sudo ip6tables -D INPUT -d fd00::/8 -j ACCEPT 2> /dev/null; echo $?",
                                       shell=True, universal_newlines=True).strip()) > 0:
            subprocess.check_output("sudo ip6tables -D INPUT -d fd00::/8 -j ACCEPT", shell=True,
                                universal_newlines=True).strip()
        if int(subprocess.check_output("sudo ip6tables -D OUTPUT -s fd00::/8 -j ACCEPT 2> /dev/null; echo $?",
                                           shell=True, universal_newlines=True).strip()) > 0:
            subprocess.check_output("sudo ip6tables -D OUTPUT -s fd00::/8 -j ACCEPT", shell=True,
                            universal_newlines=True).strip()
        sys.exit(0)


def load_config(args):
    global config, node_config, \
        param_config_file, event_config_file, \
        measurement_logger, cc_policy

    # a) Verbosity:
    log_level = logging.INFO  # default
    if args['--verbose']:
        print("DEBUG")
        log_level = logging.DEBUG
    elif args['--quiet']:
        log_level = logging.ERROR

    # b) Log file location:
    logfile = None
    if args['--logfile']:
        logfile = args['--logfile']
    logging.basicConfig(filename=logfile, level=log_level, format='%(asctime)s - %(name)s.%(funcName)s() - %(levelname)s - %(message)s')

    # c) Load measuremts config (yaml):
    if args['--measurements'] is not None:
        measurements_file_path = args['--measurements']
        with open(measurements_file_path, 'r') as f:
            measurement_config = yaml.load(f)
        measurement_logger = MeasurementLogger.load_config(measurement_config)
        measurement_logger.start_logging()
    else:
        log_measurements = False

    # d) Load the configuration file path (yaml):
    if args['--config'] is not None:
        config_file_path = args['--config']
        with open(config_file_path, 'r') as f:
            config = yaml.load(f)
    else:
        logging.fatal("Please provide config file (--config)")
        sys.exit(0)

    # e) Load the ip's of the agents (yaml):
    if args['--nodes'] is not None:
        nodes_file_path = args['--nodes']
        with open(nodes_file_path, 'r') as f:
            node_config = yaml.load(f)
    else:
        logging.fatal("Please provide nodes file (--nodes)")
        sys.exit(0)

    # f) Load the node configuration file(csv):
    if args['--param_config_file'] is not None:
        param_config_file = args['--param_config_file']

    # g) Load the event configuration file (csv):
    if args['--event_config_file'] is not None:
        event_config_file = args['--event_config_file']

    if args['--congestion_policy'] is not None:
        cc_policy = args['--congestion_policy']

    return


if __name__ == "__main__":
    main()

