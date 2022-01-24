import time
import datetime
import logging

import netmiko

import helpers


NTP_SERVER = "0.uk.pool.ntp.org"


def reset_ot_node(connection: netmiko.ConnectHandler) -> None:
    connection.send_command("sudo wpantund &")
    connection.send_command("sudo wpanctl leave")
    connection.send_command("sudo wpanctl reset")
    connection.clear_buffer()


def log_ot_counters(logger: logging.Logger,
                    connection: netmiko.ConnectHandler) -> None:
    helpers.log_multiline_response(logger, connection.send_command(
        "sudo wpanctl get NCP:Counter:AllIPv6"
    ))
    helpers.log_multiline_response(logger, connection.send_command(
        "sudo wpanctl get NCP:Counter:AllMac"
    ))


def log_ot_neighbour_table(logger: logging.Logger,
                           connection: netmiko.ConnectHandler) -> None:
    helpers.log_multiline_response(logger, connection.send_command(
        "sudo wpanctl get Thread:NeighborTable"
    ))
    helpers.log_multiline_response(logger, connection.send_command(
        "sudo wpanctl get Thread:NeighborTable:ErrorRates"
    ))


def ot_ncp_ext_address(connection: netmiko.ConnectHandler) -> str:
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

ntwk_name = f"icair-{global_timestamp.strftime('%y%m%d')}"

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

reset_ot_node(ot_leader)
log_ot_counters(ot_logger, ot_leader)
ot_logger.info("PlutoPi1 - OT Leader - Initialised")

reset_ot_node(ot_router_1)
log_ot_counters(ot_logger, ot_router_1)
ot_logger.info("PlutoPi2 - OT Router 1 - Initialised")

reset_ot_node(ot_router_2)
log_ot_counters(ot_logger, ot_router_2)
ot_logger.info("PlutoPi2 - OT Router 2 - Initialised")

reset_ot_node(ot_router_3)
log_ot_counters(ot_logger, ot_router_3)
ot_logger.info("PlutoPi2 - OT Router 3 - Initialised")

response = ot_leader.send_command(f"sudo wpanctl form {ntwk_name}")
if "success" in response:
    ot_logger.info(f"Leader formed OpenThread network {ntwk_name}")
else:
    ot_logger.critical("Could not form OpenThread network")
    ot_leader.disconnect()
    ot_router_1.disconnect()
    ot_router_2.disconnect()
    ot_router_3.disconnect()
    logging.shutdown()
    raise RuntimeError("Could not form OpenThread network")

time.sleep(5)

response = ot_leader.send_command("sudo wpanctl get IPv6:MeshLocalAddress")
leader_ipv6 = response.split(" ")[-1][1:-1]
ot_logger.info(f"Leader Mesh Local IPv6 address: {leader_ipv6}")

response = ot_leader.send_command("sudo wpanctl get Network:PANID")
ntwk_panid = response.split(" ")[-1]
ot_logger.info(f"OpenThread Network PAN ID: {ntwk_panid}")

response = ot_leader.send_command("sudo wpanctl get Network:XPANID")
ntwk_xpanid = response.split(" ")[-1]
ot_logger.info(f"OpenThread Network XPAN ID: {ntwk_xpanid}")

response = ot_leader.send_command("sudo wpanctl get Network:Key")
ntwk_key = response.split(" ")[-1][1:-1]
ot_logger.info(f"OpenThread Network Key: {ntwk_key}")

response = ot_leader.send_command("sudo wpanctl get NCP:Channel")
ntwk_channel = response.split(" ")[-1]
ot_logger.info(f"OpenThread Network Channel: {ntwk_channel}")

response = ot_leader.send_command("sudo wpanctl get NCP:Frequency")
ntwk_freq = response.split(" ")[-1]
ot_logger.info(f"OpenThread Channel Frequency: {ntwk_freq} kHz")

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

ot_router_1.send_command(f"sudo wpanctl set Network:Key {ntwk_key}")
ot_router_2.send_command(f"sudo wpanctl set Network:Key {ntwk_key}")
ot_router_3.send_command(f"sudo wpanctl set Network:Key {ntwk_key}")

ot_logger.info("Set OpenThread network key on all routers")

ot_leader.send_command("sudo wpanctl set NCP:TXPower 8")
ot_router_1.send_command("sudo wpanctl set NCP:TXPower 8")
ot_router_2.send_command("sudo wpanctl set NCP:TXPower 8")
ot_router_3.send_command("sudo wpanctl set NCP:TXPower 8")

ot_logger.info("Set max TX power on all nodes")

ot_leader.send_command("sudo wpanctl permit-join --network-wide")
time.sleep(5)
ot_router_1.send_command(
    f"sudo wpanctl join {ntwk_name} -T 2 -p {ntwk_panid} -x {ntwk_xpanid}"
)
time.sleep(30)
node_state = ot_router_1.send_command("sudo wpanctl get NCP:State")
node_tpe = ot_router_1.send_command("sudo wpanctl get NCP:NodeType")

ot_leader.send_command("sudo wpanctl permit-join --network-wide")
time.sleep(5)
ot_router_2.send_command(
    f"sudo wpanctl join {ntwk_name} -T 2 -p {ntwk_panid} -x {ntwk_xpanid}"
)
time.sleep(30)
node_state = ot_router_2.send_command("sudo wpanctl get NCP:State")
node_tpe = ot_router_2.send_command("sudo wpanctl get NCP:NodeType")

ot_leader.send_command("sudo wpanctl permit-join --network-wide")
time.sleep(5)
ot_router_3.send_command(
    f"sudo wpanctl join {ntwk_name} -T 2 -p {ntwk_panid} -x {ntwk_xpanid}"
)
time.sleep(30)
node_state = ot_router_3.send_command("sudo wpanctl get NCP:State")
node_tpe = ot_router_3.send_command("sudo wpanctl get NCP:NodeType")

ot_leader.send_command("sudo wpanctl set MAC:Allowlist:Enabled true")
ot_router_1.send_command("sudo wpanctl set MAC:Allowlist:Enabled true")
ot_router_2.send_command("sudo wpanctl set MAC:Allowlist:Enabled true")
ot_router_3.send_command("sudo wpanctl set MAC:Allowlist:Enabled true")

time.sleep(180)

log_ot_counters(ot_logger, ot_leader)
log_ot_counters(ot_logger, ot_router_1)
log_ot_counters(ot_logger, ot_router_2)
log_ot_counters(ot_logger, ot_router_3)

log_ot_neighbour_table(ot_logger, ot_leader)
log_ot_neighbour_table(ot_logger, ot_router_1)
log_ot_neighbour_table(ot_logger, ot_router_2)
log_ot_neighbour_table(ot_logger, ot_router_3)

logging.shutdown()
