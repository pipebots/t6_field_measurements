import datetime
import logging
import time
from itertools import product

import yaml

import helpers
from remote_ot_node import RemoteOTNode

nodes_file = "nodes.yml"
topology_file = "topology.yml"

global_timestamp = datetime.datetime.now()
day_timestamp = global_timestamp.strftime('%d%m%y')

ot_logger = helpers.setup_logger(
    "OT_ICAIR", global_timestamp.strftime("%Y%m%d_%H%M%S")
)
helpers.log_ntp_time(ot_logger)

ntwk_name = f"icair-{day_timestamp}"

with open(nodes_file, "r") as fin:
    all_nodes = yaml.safe_load(fin)

with open(topology_file, "r") as fin:
    topology = yaml.safe_load(fin)

leader_node = RemoteOTNode(all_nodes["leader"])

router_nodes = {
    router: RemoteOTNode(all_nodes["routers"][router])
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
