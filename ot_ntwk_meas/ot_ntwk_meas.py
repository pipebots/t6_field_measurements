import datetime
import logging
import time
from itertools import product

import yaml

import helpers
from remote_ot_node import RemoteOTNode

EXPERIMENT = "two_nodes"
PING_TESTS = True
TCP_TESTS = True
UDP_TESTS = True

repeated_experiment = False

nodes_file = f"{EXPERIMENT}/nodes.yml"
topology_file = f"{EXPERIMENT}/topology.yml"

global_timestamp = datetime.datetime.now()
day_timestamp = global_timestamp.strftime('%d%m%y')

ot_logger = helpers.setup_logger(
    f"OT_{EXPERIMENT}", global_timestamp.strftime("%Y%m%d_%H%M%S")
)
helpers.log_ntp_time(ot_logger)

ntwk_name = f"ot-{day_timestamp}"

with open(nodes_file, "r") as fin:
    all_nodes = yaml.safe_load(fin)

with open(topology_file, "r") as fin:
    topology = yaml.safe_load(fin)

leader_node = RemoteOTNode(
    all_nodes["leader"], previously_joined=repeated_experiment
)

router_nodes = {
    router: RemoteOTNode(
        all_nodes["routers"][router], previously_joined=repeated_experiment
        )
    for router in all_nodes["routers"]
}

leader_node.form_network(ntwk_name)
leader_node.logger.info(
    f"Leader mesh-local IPv6 address: {leader_node.ipv6_addr}"
)
leader_node.logger.info(f"Extended HW address: {leader_node.ext_hw_addr}")
leader_node.logger.info(f"OpenThread Network Key: {leader_node.network_key}")
leader_node.logger.info(f"OpenThread Network PAN: {leader_node.panid}")
leader_node.logger.info(f"OpenThread Network XPAN: {leader_node.xpanid}")
leader_node.logger.info(f"OpenThread Network Chan: {leader_node.channel}")
leader_node.logger.info(f"OpenThread Network Freq: {leader_node.frequency}")

leader_node.txpower = 8
for node in router_nodes:
    router_nodes[node].txpower = 8

ot_logger.info("Set max TX power on all nodes")

for node in router_nodes:
    router_nodes[node].join_network(leader_node)

    while True:
        if "router" in router_nodes[node].node_type:
            router_nodes[node].logger.info(
                f"Mesh-local IPv6 address: {router_nodes[node].ipv6_addr}"
            )
            router_nodes[node].logger.info(
                f"Extended HW address: {router_nodes[node].ext_hw_addr}"
            )
            break
        else:
            ot_logger.info("Sleeping for 30 seconds...")
            time.sleep(30)

ot_logger.info("OpenThread Network set up and all nodes joined")

for node in topology["leader"]:
    leader_node.add_maclist_entry(router_nodes[node])

for router in router_nodes:
    for node in topology[router]:
        if "leader" in node:
            router_nodes[router].add_maclist_entry(leader_node)
        else:
            router_nodes[router].add_maclist_entry(router_nodes[node])

leader_node.enable_maclist()

for router in router_nodes:
    router_nodes[router].enable_maclist()

ot_logger.info("MAC Allowlists set up and enabled")

time.sleep(180)

leader_node.logger.info("After forming OT Network")
leader_node.log_counters()
leader_node.log_neighbor_table()

for router in router_nodes:
    router_nodes[router].logger.info("After forming OT Network")
    router_nodes[router].log_counters()
    router_nodes[router].log_neighbor_table()

# * Ping tests
if PING_TESTS:
    ping_packet_sizes = [16, 32, 64, 128, 256, 512, 1024]
    ping_count = 100

    ot_logger.info("Running latency measurements using ping")

    for router in router_nodes:
        router_name = router_nodes[router]._hostname
        result_filename = f"ping_{router_name}_{day_timestamp}.log"

        for pkt_size in ping_packet_sizes:
            ping_cmd = (
                f"ping -6 -I wpan0 -c {ping_count} -s {pkt_size} "
                f"{leader_node.ipv6_addr} |& tee -a {result_filename}"
            )

            ot_logger.info(
                f"Pinging from {router_name} with a {pkt_size} byte payload"
            )

            response = router_nodes[router]._conn.send_command(
                ping_cmd, delay_factor=4
            )

            with open(result_filename, "a") as fout:
                fout.write(response)
                fout.write("\n")

            leader_node.logger.info(
                f"After receiving {pkt_size} pings from {router_name}"
            )
            leader_node.log_counters()
            leader_node.log_neighbor_table()

            router_nodes[router].logger.info(
                f"After pinging with {pkt_size} payload"
            )
            router_nodes[router].log_counters()
            router_nodes[router].log_neighbor_table()

            time.sleep(5)

    ot_logger.info("Finished latency tests")

# * Common for iperf3 tests
iperf3_port = 2607
iperf3_time = 60
iperf3_packet_sizes = [32, 160, 288, 416, 544, 672, 800, 928]
iperf3_bandwidths = [20000, 70000, 100000]

iperf3_server_log = f"iperf3_server_{day_timestamp}.log"
leader_node._conn.send_command(
    f"sudo iperf3 --server --daemon --verbose --port {iperf3_port} "
    f"--logfile {iperf3_server_log}"
)
ot_logger.info("iperf3 server started on OpenThread leader node")

if TCP_TESTS:
    ot_logger.info("Running throughput tests using TCP")

    for router in router_nodes:
        router_name = router_nodes[router]._hostname
        result_filename = f"iperf3_{router_name}_{day_timestamp}.log"

        for pkt_size, bw in product(iperf3_packet_sizes, iperf3_bandwidths):
            iperf3_cmd = (
                f"sudo iperf3 --client {leader_node.ipv6_addr} --verbose "
                f"--format k --port {iperf3_port} --bandwidth {bw} "
                f"--length {pkt_size} --time {iperf3_time} "
                f"|& tee -a {result_filename}"
            )

            ot_logger.info(
                f"Transmitting from {router_name} at {bw} bps with "
                f"{pkt_size} bytes"
            )

            response = router_nodes[router]._conn.send_command(
                iperf3_cmd, delay_factor=4
            )

            with open(result_filename, "a") as fout:
                fout.write(response)
                fout.write("\n")

            leader_node.logger.info(
                f"After TCP with {pkt_size} at {bw} bps from {router_name}"
            )
            leader_node.log_counters()
            leader_node.log_neighbor_table()

            router_nodes[router].logger.info(
                f"After TCP with {pkt_size} at {bw} bps"
            )
            router_nodes[router].log_counters()
            router_nodes[router].log_neighbor_table()

            time.sleep(5)

    ot_logger.info("Finished TCP throughput tests")

# * UDP tests
if UDP_TESTS:
    ot_logger.info("Running throughput tests using UDP")

    for router in router_nodes:
        router_name = router_nodes[router]._hostname
        result_filename = f"iperf3_{router_name}_{day_timestamp}.log"

        for pkt_size, bw in product(iperf3_packet_sizes, iperf3_bandwidths):
            iperf3_cmd = (
                f"sudo iperf3 --client {leader_node.ipv6_addr} --verbose "
                f"--format k --port {iperf3_port} --bandwidth {bw} "
                f"--length {pkt_size} --time {iperf3_time} "
                f"--udp "
                f"|& tee -a {result_filename}"
            )

            ot_logger.info(
                f"Transmitting from {router_name} at {bw} bps with "
                f"{pkt_size} bytes"
            )

            response = router_nodes[router]._conn.send_command(
                iperf3_cmd, delay_factor=4
            )

            with open(result_filename, "a") as fout:
                fout.write(response)
                fout.write("\n")

            leader_node.logger.info(
                f"After UDP with {pkt_size} at {bw} bps from {router_name}"
            )
            leader_node.log_counters()
            leader_node.log_neighbor_table()

            router_nodes[router].logger.info(
                f"After UDP with {pkt_size} at {bw} bps"
            )
            router_nodes[router].log_counters()
            router_nodes[router].log_neighbor_table()

            time.sleep(5)

    ot_logger.info("Finished UDP throughput tests")

leader_node.disconnect()

for router in router_nodes:
    router_nodes[router].disconnect()

ot_logger.info("Disconnected from all Raspberry Pis")

logging.shutdown()
