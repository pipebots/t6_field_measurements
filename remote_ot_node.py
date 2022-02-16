from ctypes import Union
import datetime
import logging
import time
from typing import Dict, Optional
from typing_extensions import Self

import netmiko


class RemoteOTNode:
    def __init__(self, netmiko_args: Dict,
                 logger: logging.Logger = None) -> None:
        self.logger = logger if logger is not None else self.__get_logger()

        try:
            self._conn = netmiko.ConnectHandler(**netmiko_args)
        except netmiko.ConfigInvalidException as error:
            self.logger.error("Invalid configuration for an SSH connection")
            raise RuntimeError from error
        except netmiko.NetmikoAuthenticationException as error:
            self.logger.error("Incorrect username and password")
            raise RuntimeError from error
        except netmiko.NetmikoTimeoutException as error:
            self.logger.error("Timed out while trying to connect")
            raise RuntimeError from error
        else:
            self._hostname = self._conn.host.split('.')[0]
            self.logger.info(f"Successfully connected to {self.hostname}")

        self.reset()
        self.logger.info(f"Successfully initialised {self.hostname}")
        self.__connected = True

        self._ipv6: Optional[str] = None
        self._exthwaddr: Optional[str] = None

        self._ntwk_panid: Optional[str] = None
        self._ntwk_xpanid: Optional[str] = None
        self._ntwk_channel: Optional[int] = None
        self._ntwk_freq: Optional[str] = None
        self._ntwk_key: Optional[str] = None

        self._ncp_txpower: Union[int, float] = 0
        self._ncp_state: Optional[int] = None
        self._ntwk_nodetype: Optional[str] = None

        self.__joined = False

    @property
    def ipv6_addr(self) -> str:
        pass

    @property
    def ext_hw_addr(self) -> str:
        pass

    @property
    def panid(self) -> str:
        pass

    @property
    def xpanid(self) -> str:
        pass

    @property
    def channel(self) -> int:
        pass

    @property
    def frequency(self) -> int:
        pass

    @property
    def network_key(self) -> str:
        pass

    @property
    def txpower(self) -> Union[int, float]:
        pass

    @txpower.setter
    def txpower(self, new_power: Union[int, float]) -> None:
        pass

    @property
    def node_state(self) -> str:
        pass

    @property
    def node_type(self) -> str:
        pass

    @property
    def mac_allowlist(self):
        pass

    @property
    def mac_denylist(self):
        pass

    def form_network(self, network_name):
        pass

    def join_network(self, leader: Self):
        pass

    def add_maclist_entry(self, peer: Self):
        pass

    def enable_maclist(self):
        pass

    def disable_maclist(self):
        pass

    def reset(self) -> None:
        self._conn.send_command("sudo wpantund &")
        self._conn.send_command("sudo wpanctl leave")
        self._conn.send_command("sudo wpanctl reset")
        self._conn.clear_buffer()

    def log_counters(self) -> None:
        response = self._conn.send_command(
            "sudo wpanctl get NCP:Counter:AllIPv6"
        )
        self.logger.info(f"{self.hostname} IPv6 Packet Counters")
        for line in response.split("\n"):
            self.logger.info(line)

        response = self._conn.send_command(
            "sudo wpanctl get NCP:Counter:AllMac"
        )
        self.logger.info(f"{self.hostname} 802.15.4 MAC Packet Counters")
        for line in response.split("\n"):
            self.logger.info(line)

    def log_neighbor_table(self) -> None:
        response = self._conn.send_command(
            "sudo wpanctl get Thread:NeighborTable"
        )
        self.logger.info(f"{self.hostname} Neighbour Details")
        for line in response.split("\n"):
            self.logger.info(line)

        response = self._conn.send_command(
            "sudo wpanctl get Thread:NeighborTable:ErrorRates"
        )
        self.logger.info(f"{self.hostname} Neighbour Links Error Rates")
        for line in response.split("\n"):
            self.logger.info(line)

    def __get_logger(self) -> logging.Logger:
        """Sets up a `Logger` object for diagnostic and debug

        A standard function to set up and configure a Python `Logger` object
        for recording diagnostic and debug data.

        Args:
            None

        Returns:
            A `Logger` object with appropriate configurations. All the messages
            are duplicated to the command prompt as well.

        Raises:
            Nothing
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = "_".join([self.hostname, timestamp])
        log_filename = ".".join([log_filename, "log"])

        logger = logging.getLogger(self.nhostname)

        logger_handler = logging.FileHandler(log_filename)
        logger_handler.setLevel(logging.INFO)

        fmt_str = "{asctime:s} {msecs:.3f} \t {levelname:^10s} \t {message:s}"
        datefmt_string = "%Y-%m-%d %H:%M:%S"
        logger_formatter = logging.Formatter(
            fmt=fmt_str, datefmt=datefmt_string, style="{"
        )

        # * This is to ensure consistent formatting of the miliseconds field
        logger_formatter.converter = time.gmtime

        logger_handler.setFormatter(logger_formatter)
        logger.addHandler(logger_handler)

        # * This enables the streaming of messages to stdout
        logging.basicConfig(
            format=fmt_str,
            datefmt=datefmt_string,
            style="{",
            level=logging.INFO,
        )
        logger.info("Logger configuration done")

        return logger

