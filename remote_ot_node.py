import datetime
import logging
import time
from typing import Dict, Optional, Union

import netmiko
from typing_extensions import Self


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

        self._ipv6: Optional[str] = None
        self._exthwaddr: Optional[str] = None

        self._ntwk_name: Optional[str] = None
        self._ntwk_panid: Optional[str] = None
        self._ntwk_xpanid: Optional[str] = None
        self._ntwk_channel: Optional[int] = None
        self._ntwk_freq: Optional[int] = None
        self._ntwk_key: Optional[str] = None

        self.__joined = False

    @property
    def ipv6_addr(self) -> str:
        if not self.__joined:
            raise RuntimeError("Node is not part of an OT network")
        if self._ipv6 is None:
            response = self._conn.send_command(
                "sudo wpanctl get IPv6:MeshLocalAddress"
            )
            self._ipv6 = response.split(" ")[1][1:-1]

        return self._ipv6

    @property
    def ext_hw_addr(self) -> str:
        if not self.__joined:
            raise RuntimeError("Node is not part of an OT network")
        if self._exthwaddr is None:
            response = self._conn.send_command(
                "sudo wpanctl get NCP:ExtendedAddress"
            )
            self._exthwaddr = response.split(" ")[1][1:-1]

        return self._exthwaddr

    @property
    def network_name(self) -> str:
        if not self.__joined:
            raise RuntimeError("Node is not part of an OT network")

        return self._ntwk_name

    @property
    def panid(self) -> str:
        if not self.__joined:
            raise RuntimeError("Node is not part of an OT network")
        if self._ntwk_panid is None:
            response = self._conn.send_command("sudo wpanctl get Network:PANID")
            self._ntwk_panid = response.split(" ")[1]

        return self._ntwk_panid

    @property
    def xpanid(self) -> str:
        if not self.__joined:
            raise RuntimeError("Node is not part of an OT network")
        if self._ntwk_xpanid is None:
            response = self._conn.send_command("sudo wpanctl get Network:XPANID")
            self._ntwk_xpanid = response.split(" ")[1]

        return self._ntwk_xpanid

    @property
    def channel(self) -> int:
        if not self.__joined:
            raise RuntimeError("Node is not part of an OT network")
        if self._ntwk_channel is None:
            response = self._conn.send_command("sudo wpanctl get NCP:Channel")
            self._ntwk_channel = int(response.split(" ")[1])

        return self._ntwk_channel

    @property
    def frequency(self) -> int:
        if not self.__joined:
            raise RuntimeError("Node is not part of an OT network")
        if self._ntwk_freq is None:
            response = self._conn.send_command("sudo wpanctl get NCP:Frequency")
            self._ntwk_freq = int(response.split(" ")[1])

        return self._ntwk_freq

    @property
    def network_key(self) -> str:
        if not self.__joined:
            raise RuntimeError("Node is not part of an OT network")
        if self._ntwk_key is None:
            response = self._conn.send_command("sudo wpanctl get Network:Key")
            self._ntwk_key = response.split(" ")[1][1:-1]

        return self._ntwk_key

    @property
    def txpower(self) -> float:
        response = self._conn.send_command("sudo wpanctl get NCP:TXPower")
        response = response.split(" ")[-1]

        return float(response)

    @txpower.setter
    def txpower(self, new_power: Union[int, float]) -> None:
        if new_power < -20 or new_power > 8:
            self.logger.warning(
                f"{new_power} is outside device limits, will be coerced"
            )
            new_power = max(-20, min(new_power, 8))
        self._conn.send_command(f"sudo wpanctl set NCP:TXPower {new_power}")
        self.logger.info(f"Set NCP TX power to {new_power}")

    @property
    def node_state(self) -> str:
        if not self.__joined:
            raise RuntimeError("Node is not part of an OT network")
        response = self._conn.send_command("sudo wpanctl get NCP:State")
        return response.split(" ")[-1][1:-1]

    @property
    def node_type(self) -> str:
        if not self.__joined:
            raise RuntimeError("Node is not part of an OT network")
        response = self._conn.send_command("sudo wpanctl get Network:NodeType")
        return response.split(" ")[-1][1:-1]

    @property
    def mac_allowlist(self):
        pass

    @property
    def mac_denylist(self):
        pass

    def form_network(self, network_name) -> None:
        if self.__joined:
            raise RuntimeWarning("Node is already part of a network")

        response = self._conn.send_command(f"sudo wpanctl form {network_name}")
        if "success" in response.lower():
            self.logger.info(f"Successfully formed {network_name}")
            self._ntwk_name = network_name
            self.__joined = True
        else:
            self.logger.critical("Could not form network")

    def join_network(self, leader: Self):
        if not leader.__joined:
            raise RuntimeError("Leader is not part of an OT network")

        leader._conn.send_command("sudo wpanctl permit-join --network-wide")
        time.sleep(5)
        join_cmd = (
            f"sudo wpanctl join {leader.network_name} -T 2 -p {leader.panid} "
            f"-x {leader.xpanid} -c {leader.channel}"
        )
        self._conn.send_command(
            f"sudo wpanctl set Network:Key {leader.network_key}"
        )
        self._conn.send_command(join_cmd)
        time.sleep(5)
        if "associated" in self.node_state.lower():
            self.logger.info(
                f"{self._hostname} Successfully joined {leader.network_name}"
            )
            self.__joined = True
            self._ntwk_name = leader.network_name
        else:
            self.logger.error("Could not join network")


    def add_maclist_entry(self, peer: Self):
        if not self.__joined or not peer.__joined:
            raise RuntimeError("Nodes are not part of an OT network")
        self._conn.send_command(
            f"sudo wpanctl add MAC:Allowlist:Entries {peer.ext_hw_addr}"
        )
        self.logger.info(
            f"Added {peer._hostname} [{peer.ext_hw_addr}] to "
            f"{self._hostname} MAC Allowlist"
        )

    def enable_maclist(self):
        self._conn.send_command("sudo wpanctl set MAC:Allowlist:Enabled true")
        self.logger.info(f"Enabled MAC Allowlist on {self._hostname}")

    def disable_maclist(self):
        self._conn.send_command("sudo wpanctl set MAC:Allowlist:Enabled false")
        self.logger.info(f"Disabled MAC Allowlist on {self._hostname}")

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

