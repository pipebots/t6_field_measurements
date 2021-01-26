import os
import time
import datetime
import logging
import ntplib
import adi


def setup_logger(filename_base: str, timestamp: str) -> logging.Logger:
    """Sets up a `Logger` object for diagnostic and debug

    A standard function to set up and configure a Python `Logger` object
    for recording diagnostic and debug data.

    Args:
        filename_base: A `str` containing a user-supplied filename to better
                      identify the logs.
        timestamp: A `str` with the date and time the logger was started
                   to differentiate between different runs

    Returns:
        A `Logger` object with appropriate configurations. All the messages
        are duplicated to the command prompt as well.

    Raises:
        Nothing
    """
    log_filename = "_".join([timestamp, filename_base])
    log_filename = os.extsep.join([log_filename, "log"])

    logger = logging.getLogger(filename_base)

    logger_handler = logging.FileHandler(log_filename)
    logger_handler.setLevel(logging.DEBUG)

    fmt_string = "{asctime:s} {msecs:.3f} \t {levelname:^10s} \t {message:s}"
    datefmt_string = "%Y-%m-%d %H:%M:%S"
    logger_formatter = logging.Formatter(
        fmt=fmt_string, datefmt=datefmt_string, style="{"
    )

    # * This is to ensure consistent formatting of the miliseconds field
    logger_formatter.converter = time.gmtime

    logger_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_handler)

    # * This enables the streaming of messages to stdout
    logging.basicConfig(
        format=fmt_string,
        datefmt=datefmt_string,
        style="{",
        level=logging.DEBUG,
    )
    logger.info("Logger configuration done")

    return logger


def log_ntp_time(logger: logging.Logger, ntp_server: str) -> None:
    """A helper function to record the time as received from an NTP server

    Establishes a connection with a specified NTP server, receives the time,
    and logs it in both UTC and local time zones. When connecting to the
    NTP server there is a chance that no response is received. In this case
    the function will sleep (blocking) for three (3) seconds before attempting
    again. After three (3) retries with no response the function will log an
    error message and return.

    Args:
        logger: The `logging.Logger` object configured by `setup_logger`
        ntp_server: A `str` with the web address of an NTP server

    Returns:
        None, the time received from the NTP server is recorded in the log
        file and on the screen

    Raises:
        Nothing
    """

    ntp_client = ntplib.NTPClient()
    ntp_connected = False
    ntp_retries = 0

    while not ntp_connected:
        try:
            ntp_time = ntp_client.request(ntp_server)
        except ntplib.NTPException:
            logger.warning("No response from NTP server, sleeping for 3 sec")
            time.sleep(3)
            ntp_retries -= 1
        else:
            ntp_connected = True
            logger.info("Got response from NTP server")

            ntp_time_utc = ntp_time.dest_timestamp
            ntp_time_utc = datetime.datetime.fromtimestamp(ntp_time_utc)
            ntp_time_utc = ntp_time_utc.strftime("%Y-%m-%d %H:%M:%S %f")

            ntp_time_ltz = ntp_time.dest_time
            ntp_time_ltz = datetime.datetime.fromtimestamp(ntp_time_ltz)
            ntp_time_ltz = ntp_time_ltz.strftime("%Y-%m-%d %H:%M:%S %f")

            logger.info(f"NTP UTC time: {ntp_time_utc}")
            logger.info(f"NTP Local timezone time: {ntp_time_ltz}")

        if 0 >= ntp_retries:
            ntp_connected = True
            logger.error("Could not perform NTP sync")


EXPERIMENT_NAME = "ICAIR_Short_Sand_Tx"
NTP_SERVER = "0.uk.pool.ntp.org"
SDR_URI = "ip:plutoalice.local"

TX_LO_FREQ_HZ = int(2.45e9)
TX_RF_BW_HZ = int(500e3)
TX_GAIN_DB = int(-20)

DDS_FREQ_HZ = int(200e3)
DDS_SCALE = 1.0

if __name__ == "__main__":
    global_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    sdr_tx_logger = setup_logger(EXPERIMENT_NAME, global_timestamp)
    log_ntp_time(sdr_tx_logger, NTP_SERVER)

    pluto = adi.Pluto(SDR_URI)
    sdr_tx_logger.info(f"Connected to {pluto._device_name}")

    pluto.tx_lo = TX_LO_FREQ_HZ
    sdr_tx_logger.info(f"Tx LO set to {pluto.tx_lo} Hz")

    pluto.tx_rf_bandwidth = TX_RF_BW_HZ
    sdr_tx_logger.info(f"Tx RF bandwidth set to {pluto.tx_rf_bandwidth} Hz")

    pluto.tx_hardwaregain_chan0 = TX_GAIN_DB
    sdr_tx_logger.info(f"Tx attenuation set to"
                       f" {pluto.tx_hardwaregain_chan0} dB")

    pluto.dds_single_tone(DDS_FREQ_HZ, DDS_SCALE)
    sdr_tx_logger.info(f"DDS frequency set to {DDS_FREQ_HZ} Hz")
    sdr_tx_logger.info(f"DDS scale set to {DDS_SCALE}")

    logging.shutdown()

else:
    print("Please run this script from the command prompt")
