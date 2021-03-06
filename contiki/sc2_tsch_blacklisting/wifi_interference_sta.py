__author__ = "Peter Ruckebusch"
__copyright__ = "Copyright (c) 2016, Ghent University, iMinds"
__version__ = "0.1.0"

# Definition of Local Control Program that is in place for generating wifi interference.


def wifi_interference_sta(control_engine):
    # do all needed imports here!!!
    import gevent
    import subprocess
    started = False
    print(("local monitor cp  - Name: {}, Id: {} - Started".format(control_engine.name, control_engine.id)))
    while not control_engine.is_stopped():
        msg = control_engine.recv(block=False)
        if msg is not None and type(msg) is dict:
            if msg['command'] == "start_wifi_interference":
                subprocess.call(['sudo','bash','/share/80211n/scripts/start80211nStation.sh'])
                gevent.sleep(5)
                subprocess.call(['sudo', 'iwconfig', 'wlan0', 'txpower', '1'])
                subprocess.call(['/usr/bin/screen','-h','1000','-dmS','80211acIPerf','/usr/bin/iperf','-c','172.23.23.1','-i','1','-t','1000000','-b','650M'])
                started = True
            elif msg['command'] == "stop_wifi_interference":
                subprocess.call(['sudo','killall','iperf'])
                subprocess.call(['sudo','killall','wpa_supplicant'])
                started = False
        gevent.sleep(1)
    if started:
        subprocess.call(['sudo','killall','iperf'])
        subprocess.call(['sudo','killall','wpa_supplicant'])
    print(("local monitor cp  - Name: {}, Id: {} - STOPPED".format(control_engine.name, control_engine.id)))
