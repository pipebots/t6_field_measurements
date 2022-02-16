"""Set up an OpenThread network in a linear mesh topology

Semi-automated way of setting up an OpenThread network. Written for a very
specific scenario, where four MCUs with OpenThread capabilities are connected
to four Raspberry Pis, and are flashed with the Network Co-Processor (NCP)
firmware. The Pis themselves have `wpantund` installed on them, meaning they
get a `wpan0` network interface.

This script sets up a very particular topology, which is the one used for
taking measurements at ICAIR, i.e. a linear mesh. A lot of diagnostic info
is recorded at certain stages.

Once the mesh topology has been established, we remotely run `ping` and `iperf3`
test, to measure latency and throughput, respectively.
"""

from itertools import product
import time
import datetime
import logging

import yaml
import netmiko

import helpers


NTP_SERVER = "0.uk.pool.ntp.org"


def reset_ot_node(connection: netmiko.ConnectHandler) -> None:
    """Factory reset of an OpenThread node

    Starts the `wpantund` service on the target node, and resets the NCP
    to factory settings, to avoid rejoining networks from previous runs.

    Args:
        connection: A `netmiko.ConnectHandler` object with an established
                    connection to the remote Raspberry Pi.

    Returns:
        Nothing

    Raises:
        Nothing
    """

    connection.send_command("sudo wpantund &")
    connection.send_command("sudo wpanctl leave")
    connection.send_command("sudo wpanctl reset")
    connection.clear_buffer()


def log_ot_counters(logger: logging.Logger,
                    connection: netmiko.ConnectHandler) -> None:
    """Log the values of OpenThread packet counters

    OpenThread nodes keep internal packet error stats, both on MAC and IP
    level. This functions queries those and writes them to a log file.

    Args:
        logger: A `logging.Logger` object with the current log file
        connection: A `netmiko.ConnectHandler` object with an established
                    connection to the remote Raspberry Pi.

    Returns:
        Nothing

    Raises:
        Nothing
    """

    helpers.log_multiline_response(logger, connection.send_command(
        "sudo wpanctl get NCP:Counter:AllIPv6"
    ))
    helpers.log_multiline_response(logger, connection.send_command(
        "sudo wpanctl get NCP:Counter:AllMac"
    ))


def log_ot_neighbour_table(logger: logging.Logger,
                           connection: netmiko.ConnectHandler) -> None:
    """Log the values of OpenThread neighbour tables

    OpenThread nodes keep internal data on link-level neighbours, as well as
    stats on those links, such as RSSI, frame counters, and so on.
    This functions queries those and writes them to a log file.

    Args:
        logger: A `logging.Logger` object with the current log file
        connection: A `netmiko.ConnectHandler` object with an established
                    connection to the remote Raspberry Pi.

    Returns:
        Nothing

    Raises:
        Nothing
    """

    helpers.log_multiline_response(logger, connection.send_command(
        "sudo wpanctl get Thread:NeighborTable"
    ))
    helpers.log_multiline_response(logger, connection.send_command(
        "sudo wpanctl get Thread:NeighborTable:ErrorRates"
    ))


def ot_ncp_ext_address(connection: netmiko.ConnectHandler) -> str:
    """Gets the value of an OpenThread node's Extended Address

    OpenThread nodes have a few addresses. An Extended Address is used by the
    MAC Allowlist/Denylist functionality. It is not a fixed one, i.e. it does
    change every time the node is power-cycled or reset.
    This functions queries and returns that address

    Args:
        connection: A `netmiko.ConnectHandler` object with an established
                    connection to the remote Raspberry Pi.

    Returns:
        A `str` representation of the node's Extended Address in hex format,
        i.e. something like "CAFE000CAFE1111".

    Raises:
        Nothing
    """

    ncp_ext_address = connection.send_command(
        "sudo wpanctl get NCP:ExtendedAddress"
    )
    ncp_ext_address = ncp_ext_address.split(" ")[-1][1:-1]
    return ncp_ext_address


global_timestamp = datetime.datetime.now()
ot_logger = helpers.setup_logger(
    "OT_ICAIR", global_timestamp.strftime("%Y%m%d_%H%M%S")
)
helpers.log_ntp_time(ot_logger, NTP_SERVER)

day_timestamp = global_timestamp.strftime('%d%m%y')
ntwk_name = f"icair-{day_timestamp}"

# * Establish remote connections to the Pis. Credentials are hard-coded in the
# * first instance.
ot_leader = netmiko.ConnectHandler(
    device_type="linux", host="plutopi1.local", username="pi",
    password="orangeandmango2020"
)
ot_logger.info("Connected to PlutoPi1 - OT Leader")

ot_router_1 = netmiko.ConnectHandler(
    device_type="linux", host="plutopi2.local", username="pi",
    password="cherriesandberries2020"
)
ot_logger.info("Connected to PlutoPi2 - OT Router 1")

ot_router_2 = netmiko.ConnectHandler(
    device_type="linux", host="plutopi3.local", username="pi",
    password="appleandblackcurrant2020"
)
ot_logger.info("Connected to PlutoPi3 - OT Router 2")

ot_router_3 = netmiko.ConnectHandler(
    device_type="linux", host="plutopi4.local", username="pi",
    password="summerfruits2020"
)
ot_logger.info("Connected to PlutoPi4 - OT Router 3")

all_nodes = [ot_leader, ot_router_1, ot_router_2, ot_router_3]
routers = [ot_router_1, ot_router_2, ot_router_3]

# * We log the packet counter values just after initialisation as a baseline
# * for cross-referencing later after the ping and iperf tests.
for node in all_nodes:
    reset_ot_node(node)
    log_ot_counters(ot_logger, node)
    ot_logger.info(f"{node.host.split('.')[0]} - Initialised")

# * One of the OpenThread nodes must form the network, becoming its `leader`.
# * This should be possible all the time, but in case there is an issue with
# * the NCP we abort here.
response = ot_leader.send_command(f"sudo wpanctl form {ntwk_name}")
if "success" in response.lower():
    ot_logger.info(f"Leader formed OpenThread network {ntwk_name}")
else:
    ot_logger.critical("Could not form OpenThread network")
    for node in all_nodes:
        node.disconnect()
    logging.shutdown()
    raise RuntimeError("Could not form OpenThread network")

time.sleep(5)

# * Once the network has been formed we log and save the parameters which are
# * needed for the other nodes to join.
response = ot_leader.send_command("sudo wpanctl get IPv6:MeshLocalAddress")
leader_ipv6 = response.split(" ")[-1][1:-1]
ot_logger.info(f"Leader Mesh Local IPv6 address: {leader_ipv6}")

response = ot_leader.send_command("sudo wpanctl get Network:Key")
ntwk_key = response.split(" ")[-1][1:-1]
ot_logger.info(f"OpenThread Network Key: {ntwk_key}")

response = ot_leader.send_command("sudo wpanctl get Network:PANID")
ntwk_panid = response.split(" ")[-1]
ot_logger.info(f"OpenThread Network PAN ID: {ntwk_panid}")

response = ot_leader.send_command("sudo wpanctl get Network:XPANID")
ntwk_xpanid = response.split(" ")[-1]
ot_logger.info(f"OpenThread Network XPAN ID: {ntwk_xpanid}")

response = ot_leader.send_command("sudo wpanctl get NCP:Channel")
ntwk_channel = response.split(" ")[-1]
ot_logger.info(f"OpenThread Network Channel: {ntwk_channel}")

response = ot_leader.send_command("sudo wpanctl get NCP:Frequency")
ntwk_freq = response.split(" ")[-1]
ot_logger.info(f"OpenThread Channel Frequency: {ntwk_freq} kHz")

# * Setting the TX transmit power to the maximum of 8 dBm is necessary when
# * working in the pipe, and is specific to the nRF52840.
for node in all_nodes:
    node.send_command("sudo wpanctl set NCP:TXPower 8")
ot_logger.info("Set max TX power on all nodes")

# ! Since we are in full control of all nodes we skip the commissioning
# ! process and manually set the Network Key, PAN ID, and XPAN ID on all nodes.
for router in routers:
    router.send_command(f"sudo wpanctl set Network:Key {ntwk_key}")
ot_logger.info("Set OpenThread network key on all routers")

# ! From here on there are many `time.sleep()` calls. These are used to give
# ! the nodes time to join the OpenThread network and be promoted to routers.
# ! It is also necessary to wait for certain network data to be propagated
# ! from the leader to the rest of the nodes. We also check and wait more to
# ! make sure the nodes have associated with the network and been promoted to
# ! routers.
join_cmd = (
    f"sudo wpanctl join {ntwk_name} -T 2 -p {ntwk_panid} -x {ntwk_xpanid} "
    f"-c {ntwk_channel}"
)

# * We will hold the individual node's IPv6 addresses in a dict just in case, to
# * avoid any potential issues with mismatches between node names and IPv6
router_ipv6 = dict()

for router in routers:
    router_name = router.host.split(".")[0]
    ot_leader.send_command("sudo wpanctl permit-join --network-wide")
    time.sleep(5)
    router.send_command(join_cmd)

    while True:
        time.sleep(30)
        node_state = router.send_command("sudo wpanctl get NCP:State")
        node_state = node_state.split(" ")[-1][1:-1]
        node_type = router.send_command("sudo wpanctl get Network:NodeType")
        node_type = node_type.split(" ")[-1][1:-1]
        if "associated" in node_state.lower() and "router" in node_type.lower():
            ot_logger.info(
                f"Router {router_name} successfully joined the network"
            )
            response = router.send_command(
                "sudo wpanctl get IPv6:MeshLocalAddress"
            )
            router_ipv6[router_name] = response.split(" ")[-1][1:-1]
            ot_logger.info(
                f"Router {router_name} mesh local IPv6 address: "
                f"{router_ipv6[router_name]}"
            )
            break
        else:
            ot_logger.info(f"Current {router_name} node state: {node_state}")
            ot_logger.info(f"Current {router_name} node type: {node_type}")
            ot_logger.info("Waiting for 30 seconds...")

# ! This series of commands makes sure the linear mesh topology is established.
# ! Useful when running tests in free space in the lab, but also helps at
# ! ICAIR when multipath propagation through the sand enables
# ! cross-connections between non-adjacent nodes.
leader_mac = ot_ncp_ext_address(ot_leader)
ot_logger.info(f"Leader Extended Address: {leader_mac}")

router_1_mac = ot_ncp_ext_address(ot_router_1)
ot_logger.info(f"Router 1 Extended Address: {router_1_mac}")

router_2_mac = ot_ncp_ext_address(ot_router_2)
ot_logger.info(f"Router 2 Extended Address: {router_2_mac}")

router_3_mac = ot_ncp_ext_address(ot_router_3)
ot_logger.info(f"Router 3 Extended Address: {router_3_mac}")

ot_leader.send_command(
    f"sudo wpanctl add MAC:Allowlist:Entries {router_1_mac}"
)

ot_router_1.send_command(
    f"sudo wpanctl add MAC:Allowlist:Entries {leader_mac}"
)
ot_router_1.send_command(
    f"sudo wpanctl add MAC:Allowlist:Entries {router_2_mac}"
)

ot_router_2.send_command(
    f"sudo wpanctl add MAC:Allowlist:Entries {router_1_mac}"
)
ot_router_2.send_command(
    f"sudo wpanctl add MAC:Allowlist:Entries {router_3_mac}"
)

ot_router_3.send_command(
    f"sudo wpanctl add MAC:Allowlist:Entries {router_2_mac}"
)

ot_logger.info("Set up MAC Allowlists on all nodes")

# ! We activate the MAC Allowlist only after all the nodes have joined. We
# ! then wait 3 minutes for the changes to take effect and for the topology to
# ! stabilise. Finally, we record the packet counters and the neighbour
# ! tables, as a reference point before we start the actual experiments.
for node in all_nodes:
    node.send_command("sudo wpanctl set MAC:Allowlist:Enabled true")
ot_logger.info("MAC filtering enabled, waiting for 180 seconds...")
time.sleep(180)

for node in all_nodes:
    node_name = node.host.split(".")[0]
    ot_logger.info(
        f"Node {node_name} packet counters, neighbour table, and error rates"
    )
    log_ot_counters(ot_logger, node)
    log_ot_neighbour_table(ot_logger, node)
ot_logger.info("OpenThread linear mesh network setup complete")

# * Ping tests
ping_packet_sizes = [16, 32, 64, 128, 256, 512, 1024]
ping_count = 100

ot_logger.info("Running latency measurements using ping")

for router in routers:
    router_name = router.host.split('.')[0]
    result_filename = f"ping_{router_name}_{day_timestamp}.log"
    for pkt_size in ping_packet_sizes:
        ping_cmd = (
            f"ping -6 -I wpan0 -c {ping_count} -s {pkt_size} {leader_ipv6} "
            f"|& tee -a {result_filename}"
        )

        ot_logger.info(f"Pinging from {router_name} with {pkt_size} b payload")

        response = router.send_command(ping_cmd, delay_factor=4)

        with open(result_filename, "a") as fout:
            fout.write(response)
            fout.write("\n")

        ot_logger.info(
            "Leader packet counters, neighbour table, and error rates"
        )
        log_ot_counters(ot_logger, ot_leader)
        log_ot_neighbour_table(ot_logger, ot_leader)

        ot_logger.info(
            f"Router {router_name} counters, neighbours table, and error rates"
        )
        log_ot_counters(ot_logger, router)
        log_ot_neighbour_table(ot_logger, router)

        time.sleep(5)

ot_logger.info("Finished latency tests")

# * Common for iperf3 tests
iperf3_port = 2607
iperf3_time = 60
iperf3_packet_sizes = [32, 160, 288, 416, 544, 672, 800, 928]
iperf3_bandwidths = [20000, 70000, 100000]

iperf3_server_log = f"iperf3_server_{day_timestamp}.log"
ot_leader.send_command(
    f"sudo iperf3 --server --daemon --verbose --port {iperf3_port} "
    f"--logfile {iperf3_server_log}"
)
ot_logger.info("iperf3 server started on OpenThread leader node")

# * TCP tests
ot_logger.info("Running throughput tests using TCP")

for router in routers:
    router_name = router.host.split('.')[0]
    result_filename = f"iperf3_{router_name}_{day_timestamp}.log"
    for pkt_size, bw in product(iperf3_packet_sizes, iperf3_bandwidths):
        iperf3_cmd = (
            f"sudo iperf3 --client {leader_ipv6} --verbose --format k "
            f"--port {iperf3_port} --bandwidth {bw} --length {pkt_size} "
            f"--time {iperf3_time} |& tee -a {result_filename}"
        )

        ot_logger.info(
            f"Transmitting from {router_name} at {bw} bps with {pkt_size} bytes"
        )

        response = router.send_command(iperf3_cmd, delay_factor=4)

        with open(result_filename, "a") as fout:
            fout.write(response)
            fout.write("\n")

        ot_logger.info(
            "Leader packet counters, neighbour table, and error rates"
        )
        log_ot_counters(ot_logger, ot_leader)
        log_ot_neighbour_table(ot_logger, ot_leader)

        ot_logger.info(
            f"Router {router_name} counters, neighbours table, and error rates"
        )
        log_ot_counters(ot_logger, router)
        log_ot_neighbour_table(ot_logger, router)

        time.sleep(5)

ot_logger.info("Finished TCP throughput tests")

# * UDP tests
ot_logger.info("Running throughput tests using UDP")

for router in routers:
    router_name = router.host.split('.')[0]
    result_filename = f"iperf3_{router_name}_{day_timestamp}.log"
    for pkt_size, bw in product(iperf3_packet_sizes, iperf3_bandwidths):
        iperf3_cmd = (
            f"sudo iperf3 --client {leader_ipv6} --verbose --format k --udp "
            f"--port {iperf3_port} --bandwidth {bw} --length {pkt_size} "
            f"--time {iperf3_time} |& tee -a {result_filename}"
        )

        ot_logger.info(
            f"Transmitting from {router_name} at {bw} bps with {pkt_size} bytes"
        )

        response = router.send_command(iperf3_cmd, delay_factor=4)

        with open(result_filename, "a") as fout:
            fout.write(response)

        ot_logger.info(
            "Leader packet counters, neighbour table, and error rates"
        )
        log_ot_counters(ot_logger, ot_leader)
        log_ot_neighbour_table(ot_logger, ot_leader)

        ot_logger.info(
            f"Router {router_name} counters, neighbours table, and error rates"
        )
        log_ot_counters(ot_logger, router)
        log_ot_neighbour_table(ot_logger, router)

        time.sleep(5)

ot_logger.info("Finished UDP throughput tests")

for node in all_nodes:
    node_name = node.host.split(".")[0]
    ot_logger.info(
        f"Node {node_name} packet counters, neighbour table, and error rates"
    )
    log_ot_counters(ot_logger, node)
    log_ot_neighbour_table(ot_logger, node)

for node in all_nodes:
    node.disconnect()

ot_logger.info("Disconnected from all Raspberry Pis")

logging.shutdown()
