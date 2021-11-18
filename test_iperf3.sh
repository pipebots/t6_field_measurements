#!/bin/bash

set -e

IPERF3_SERVER="8.8.8.8"
IPERF3_SERVER_PORT=6969
IPERF3_LOGFILE="node_2.log"
IPERF3_TIME=60
IPERF3_PACKET_SIZES=(32 160 288)
IPERF3_BWS=(20000 70000 100000)

clear

echo "Begin iperf3 tests"
echo
echo "Sending data to $PEER"
echo

for BW in "${IPERF3_BWS[@]}"
do
    echo "Testing with $BW bits per second"
    echo
    for PACKET_SIZE in "${IPERF3_PACKET_SIZES[@]}"
    do
        echo "Using $PACKET_SIZE payload"
        echo
        echo "TCP Packets"
        echo
        sudo iperf3 --port $IPERF3_SERVER_PORT --format k --client $IPERF3_SERVER --verbose --bandwidth $BW --length $PACKET_SIZE --time $IPERF3_TIME |& tee -a $IPERF3_LOGFILE
        sleep 3
        echo "UDP Packets"
        echo
        sudo iperf3 --port $IPERF3_SERVER_PORT --format k --client $IPERF3_SERVER --verbose --bandwidth $BW --length $PACKET_SIZE --time $IPERF3_TIME --udp |& tee -a $IPERF3_LOGFILE
        sleep 3
    done
done
