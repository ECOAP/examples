#!/bin/sh
BUILD_DIR=../build_release/src
cd $BUILD_DIR
./dyspanradio --freq=2.49e9 --channel_bandwidth=5000000 --channel_rate=5000000 --rxgain=25 --num_channels=4 --txgain_uhd=5 --txgain_soft=-12  --rxsubdev="A:0" --txsubdev="A:0"
./dyspanradio --freq=2.4125e9 --channel_bandwidth=5000000 --channel_rate 5000000 --num_channels=4 --txgain_uhd=18 --txgain_soft=-10 --challenge=true --debug=false --txsubdev="A:0" --mod qam16 --learning=true --reconfig_wait=10 --second_av_size=1.5
