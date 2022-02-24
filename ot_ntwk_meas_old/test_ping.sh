#!/bin/bash

set -e

PING_PEERS=("8.8.8.8" "127.0.0.1")
PING_LOGFILE="node_2.log"
PING_PACKET_SIZES=(16 32 64 128 256 512 1024)
PING_COUNT=100

clear

echo "Begin ping tests"
echo

for PEER in "${PING_PEERS[@]}"
do
    echo "Pinging $PEER"
    echo

    for PACKET_SIZE in "${PING_PACKET_SIZES[@]}"
    do
        echo "Using $PACKET_SIZE payload"
        echo
        ping -6 -I wpan0 -c $PING_COUNT -s $PACKET_SIZE $PEER |& tee -a $PING_LOGFILE
        sleep 3
    done
done
