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

from measurement_logger import *
from stdout_measurement_logger import *
from file_measurement_logger import *
from gnuplot_measurement_logger import *
from mysql_measurement_logger import *
from contiki.contiki_helpers.global_node_manager import *
from contiki.contiki_helpers.taisc_manager import *
from contiki.contiki_helpers.app_manager import *


__author__ = "Carlo Vallati & Francesca Righetti"
__copyright__ = "Copyright (c) 2018, UNIPI"
__version__ = "0.1.0"
__email__ = "carlo.vallati@unipi.it"

log = logging.getLogger('contiki_global_control_program')

param_config_file = None

def default_callback(group, node, cmd, data, interface = ""):
    print("{} DEFAULT CALLBACK : Group: {}, NodeName: {}, Cmd: {}, Returns: {}, interface: {}".format(datetime.datetime.now(), group, node.name, cmd, data, interface))

def handle_event(mac_address, event_name, event_value):
    print("%s @ %s: %s"%(str(mac_address), event_name, str(event_value)))
    measurement_logger.log_measurement(event_name, event_value)

def handle_measurement(mac_address, measurement_report):
    for st in measurement_report:
        print("%s @ %s"%(str(mac_address), str(st)))
        measurement_logger.log_measurement(str(st), measurement_report[st])

def event_cb(mac_address, event_name, event_value):
    _thread.start_new_thread(handle_event, (mac_address, event_name, event_value))

def main():
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
        print("Set node %d as border router"%(border_router_id))
        app_manager.rpl_set_border_router([0xfd, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],border_router_id)
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
                    print("Setting %s to %s (%s)"%(setting[1],setting[2],err)) 
                
        print("Starting udp example")
        print("Activating server")
        app_manager.update_configuration({"app_activate": 1},[1])
        print("Activating clients")
        app_manager.update_configuration({"app_activate": 2},range(2,len(global_node_manager.get_mac_address_list())+1))

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
                        print("Suscribe event %s returns %s"%(event_setting[1],ret_events))

        #for m in measurement_logger.measurement_definitions:
        app_manager.get_measurements_periodic(measurement_logger.measurement_definitions,10,10,100000,handle_measurement) # TODO experiment duration

        # Run the experiment until keyboard interrupt is triggered:
        while True:
            #app_manager.update_configuration({"app_server_ipv6_address": (253, 0, 0, 0, 0, 0, 0, 0, 169, 205, 0, 255, 254, 0, 0, 1)})
            gevent.sleep(10)
            
    except KeyboardInterrupt:
        log.debug("Exit")
        global_node_manager.stop()
        log.debug("Controller exits")
        sys.exit(0)
        
def load_config(args): 
    global config, node_config, \
        param_config_file, event_config_file, \
        measurement_logger
    
    # a) Verbosity:
    log_level = logging.INFO  # default
    if args['--verbose']:
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

    return


if __name__ == "__main__":
    main()
    
