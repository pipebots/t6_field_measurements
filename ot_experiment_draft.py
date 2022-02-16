from itertools import product
import time
import datetime
import logging

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


global_timestamp = datetime.datetime.now()
ot_logger = helpers.setup_logger(
    "OT_ICAIR", global_timestamp.strftime("%Y%m%d_%H%M%S")
)
helpers.log_ntp_time(ot_logger, NTP_SERVER)

day_timestamp = global_timestamp.strftime('%d%m%y')
ntwk_name = f"icair-{day_timestamp}"
