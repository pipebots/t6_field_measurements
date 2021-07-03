"""Pluto SDR control - Tx side

Automates the setup of a Pluto SDR unit as a CW transmitter. Fairly simple as
it uses the on-board DDS functionality to generate the tone to be sent over
the air. Once setup is complete the unit can be left alone until a different
combination of parameters needs to be configured.

Details of the unit are logged to make sure parameters have been properly
set up and to aid subsequent data analysis.
"""

import os
import time
import datetime
import argparse
import logging
import ntplib
import adi


NTP_SERVER = "0.uk.pool.ntp.org"


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
    ntp_retries = 3

    logger.info(f"Attempting to connect to {ntp_server}")

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


def main(args: argparse.Namespace):
    global_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    sdr_tx_logger = setup_logger(args.EXPERIMENT_NAME, global_timestamp)
    log_ntp_time(sdr_tx_logger, NTP_SERVER)

    try:
        pluto = adi.Pluto(args.SDR_URI)
    except Exception as error:
        sdr_tx_logger.critical(f"Could not connect to {args.SDR_URI}")
        sdr_tx_logger.critical(f"Error message returned: {error.args[0]}")
        exit()

    sdr_tx_logger.info(f"Connected to: {pluto._ctx.attrs['hw_model']}")
    sdr_tx_logger.info(f"Serial number: {pluto._ctx.attrs['hw_serial']}")
    sdr_tx_logger.info(f"Firmware version: {pluto._ctx.attrs['fw_version']}")
    sdr_tx_logger.info(f"PHY model: {pluto._ctx.attrs['ad9361-phy,model']}")
    sdr_tx_logger.info(
        f"XO Correction: " f"{pluto._ctx.attrs['ad9361-phy,xo_correction']}"
    )

    pluto.tx_lo = int(args.TX_LO_FREQ_HZ * 1e9)
    sdr_tx_logger.info(f"Tx LO set to {pluto.tx_lo} Hz")

    pluto.tx_rf_bandwidth = int(args.TX_RF_BW_HZ * 1e6)
    sdr_tx_logger.info(f"Tx RF bandwidth set to {pluto.tx_rf_bandwidth} Hz")

    pluto.tx_hardwaregain_chan0 = int(-args.TX_GAIN_DB)
    sdr_tx_logger.info(
        f"Tx attenuation set to" f" {pluto.tx_hardwaregain_chan0} dB"
    )

    pluto.dds_single_tone(int(args.DDS_FREQ_HZ * 1e3), args.DDS_SCALE)
    sdr_tx_logger.info(f"DDS frequency set to {args.DDS_FREQ_HZ} kHz")
    sdr_tx_logger.info(f"DDS scale set to {args.DDS_SCALE}")

    sdr_tx_logger.info(
        f"Tx Path Sample Rates: "
        f"{pluto._ctx.devices[1].attrs['tx_path_rates'].value}"
    )

    sdr_tx_logger.info("Setup complete")

    logging.shutdown()


def cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="prop_meas_tx",
        description="Sets up a Pluto SDR as a CW Tx. Saves IQ samples in"
                    " an np.complex64 format to an .iqbin file."
                    " Saves diagnostic information to a .log file.",
        usage="%(prog)s [parameters] sdr_uri",
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Please make sure you are transmitting in an ISM band. For any"
               " questions related to the meaning of the parameters consult"
               " the online documentation from Analog Devices"
               " (https://wiki.analog.com/university/tools/pluto)."
    )

    parser.add_argument(
        "SDR_URI",
        metavar="sdr_uri",
        type=str,
        help="The URI of the Pluto SDR, such as ip:192.168.7.1 or usb:1.5.2",
    )

    parser.add_argument(
        "-n",
        "--name",
        metavar="EXPERIMENT NAME",
        type=str,
        action="store",
        dest="EXPERIMENT_NAME",
        default="ICAIR_Short_Sand_Tx",
        help="A descriptive name of the measurements. Cannot contain spaces"
    )

    parser.add_argument(
        "-l",
        "--tx-lo",
        metavar="TX LO FREQ",
        type=float,
        action="store",
        dest="TX_LO_FREQ_HZ",
        default=2.45,
        help="The frequency, in GHz, of the Tx LO"
    )

    parser.add_argument(
        "-b",
        "--tx-bw",
        metavar="TX RF BANDWIDTH",
        type=float,
        action="store",
        dest="TX_RF_BW_HZ",
        default=0.5,
        help="The bandwidth, in MHz, of the Tx RF filter"
    )

    parser.add_argument(
        "-g",
        "--tx-gain",
        metavar="GAIN",
        type=int,
        action="store",
        dest="TX_GAIN_DB",
        default=20,
        help="The attenuation, in dB, of the Tx front end"
    )

    parser.add_argument(
        "-f",
        "--dds-freq",
        metavar="DDS FREQ",
        type=float,
        action="store",
        dest="DDS_FREQ_HZ",
        default=200,
        help="The DDS frequency, in kHz. Output tone frequency will be"
             " (Tx LO + DDS)"
    )

    parser.add_argument(
        "-s",
        "--dds-scale",
        metavar="SCALE",
        type=float,
        action="store",
        dest="DDS_SCALE",
        default=1.0,
        help="The scaling of the DDS signal amplitude, 0 <= SCALE <= 1"
    )

    args = parser.parse_args()

    return args

if __name__ == "__main__":
    args = cli_args()
    main(args)
