"""Pluto SDR control - Rx side

Automates the setup of a Pluto SDR unit as a CW receiver. Fairly simple as
it just captures a predetermined number of samples and saves them in a binary
file. Once the number of measurements is complete, the script exits but the
Pluto SDR configuration persists.

Details of the unit are logged to make sure parameters have been properly
set up and to aid subsequent data analysis.
"""

import time
import datetime
import argparse
import logging
from typing import Dict

import numpy as np
import h5py
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
    log_filename = ".".join([log_filename, "log"])

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


def pluto_cw_tone_rx(params: Dict, logger: logging.Logger) -> None:
    """Sets up a Pluto SDR as a simple receiver and captures data

    Sets the Pluto SDR as a simple receiver that captures a specified number
    of samples a specified number of times, and saves everything to an HDF5
    file. The filename is constructed from data in the `params` input and
    the current date.

    Notes:
        1. There is an one (1) second delay between subsequent captures.
        2. The HDF5 file is reused for measurements with different parameters
        taken in the same day.

    Args:
        params: A `dict` object with the necessary parameters. These can be
                obtained either through a CLI or supplied from another
                function. There are no input checks so use responsibly.
        logger: A `Logger` object that has been pre-configured and set up, for
                recording diagnostic and error messages.

    Raises:
        RuntimeError: In case a connection to the Pluto cannot be established.
    """
    try:
        pluto = adi.Pluto(params["SDR_URI"])
    except Exception as error:
        logger.critical(f"Could not connect to {params['SDR_URI']}")
        logger.critical(f"Error message returned: {error.args[0]}")
        raise RuntimeError("Could not connect to Pluto SDR") from error

    logger.info(f"Connected to: {pluto._ctx.attrs['hw_model']}")
    logger.info(f"Serial number: {pluto._ctx.attrs['hw_serial']}")
    logger.info(f"Firmware version: {pluto._ctx.attrs['fw_version']}")
    logger.info(f"PHY model: {pluto._ctx.attrs['ad9361-phy,model']}")
    logger.info(
        f"XO Correction: " f"{pluto._ctx.attrs['ad9361-phy,xo_correction']}"
    )

    # ! Turning off the Tx LO on the receiver helps with noise and
    # ! self-interference performance.
    ad9361_phy = pluto._ctrl
    tx_lo = ad9361_phy.find_channel("TX_LO")
    tx_lo.attrs["powerdown"].value = str(int(1))
    logger.info("Tx LO powered down on Rx side")

    pluto.rx_lo = int(params["RX_LO_FREQ_GHZ"] * 1e9)
    logger.info(f"Rx LO set to {pluto.rx_lo} Hz")

    pluto.rx_rf_bandwidth = int(params["RX_RF_BW_MHZ"] * 1e6)
    logger.info(f"Rx RF bandwidth set to {pluto.rx_rf_bandwidth} Hz")

    pluto.sample_rate = int(params["SAMPLE_RATE"] * 1e6)
    logger.info(f"ADC set to {pluto.sample_rate} samples per second")

    pluto.rx_buffer_size = params["RX_BUFFER_SIZE"]
    logger.info(f"Rx buffer size set to {pluto.rx_buffer_size} samples")

    pluto.gain_control_mode_chan0 = "manual"
    pluto.rx_hardwaregain_chan0 = params["RX_GAIN_DB"]
    logger.info(f"Rx gain set to {pluto.rx_hardwaregain_chan0} dB")

    logger.info(
        f"Rx Path Sample Rates: "
        f"{pluto._ctx.devices[1].attrs['rx_path_rates'].value}"
    )

    meas_filename = "_".join(
        [
            params["EXPERIMENT_NAME"],
            datetime.datetime.now().strftime("%Y%m%d")
        ]
    )
    meas_filename = ".".join([meas_filename, "hdf5"])

    with h5py.File(meas_filename, "a") as meas_file:
        meas_file.attrs["place"] = params["EXPERIMENT_NAME"]
        meas_file.attrs["user"] = "Viktor Doychinov"

        meas_file.attrs["rx_rf_bw_hz"] = pluto.rx_rf_bandwidth
        meas_file.attrs["rx_gain_control"] = "manual"
        meas_file.attrs["rx_tx_lo_state"] = "powered down"
        meas_file.attrs["rx_sample_rate"] = pluto.sample_rate
        meas_file.attrs["rx_buf_size"] = pluto.rx_buffer_size

        group_name = "/".join([
            f"{params['RX_LO_FREQ_GHZ']*1e3}MHz",
            params["POL"],
            f"{params['DDS_FREQ_KHZ']}kHz",
            f"rx_gain_db_{params['RX_GAIN_DB']}",
            params["MEAS_HINT"]
        ])

        if group_name not in meas_file:
            meas_file.create_group(group_name)

        for idx in range(params["NUM_MEAS"]):
            try:
                samples = pluto.rx()

                samples = samples.astype(np.complex64)
                samples_real = np.real(samples).astype(np.int16)
                samples_imag = np.imag(samples).astype(np.int16)
                samples_hdf5 = np.column_stack((samples_real, samples_imag))

                dset_name = f"measurement_{idx+1}"

                meas_file[group_name].create_dataset(
                    dset_name, np.shape(samples_hdf5), dtype="i2",
                    data=samples_hdf5, compression="gzip", compression_opts=6
                )

                logger.info(
                    f"Measurement {idx+1} out of {params['NUM_MEAS']} done."
                    f" Imax: {np.max(samples_real)}"
                    f" Imin: {np.min(samples_real)}"
                    f" Qmax: {np.max(samples_imag)}"
                    f" Qmin: {np.min(samples_imag)}"
                )

                # ! Important for data analysis - samples are not contiguous
                time.sleep(1)

            except KeyboardInterrupt:
                logger.warning("Received Ctrl-C interrupt")
                break

    logger.info("Measurements complete")


def cli_args() -> argparse.Namespace:
    """Process command-line arguments for Tx Pluto SDR

    Collects all necessary arguments for setting up a Pluto SDR as a simple Rx
    at a particular frequency. Default values are present for everything
    except the URI of the Pluto.

    Returns:
        argparse.Namespace: The processed parameters for later use

    Raises:
        Nothing

    Notes:
        The script will terminate if the URI of the SDR is not specified
    """
    parser = argparse.ArgumentParser(
        prog="prop_meas_rx",
        description="Sets up a Pluto SDR as a Rx. Saves IQ samples in"
                    " a pair of np.int16 arrays to a .h5py file."
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
        help="The URI of the Pluto SDR, such as ip:192.168.7.1 or usb:1.5.2"
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
        "-t",
        "--hint",
        metavar="MEASUREMENT HINT",
        type=str,
        action="store",
        dest="MEAS_HINT",
        default="standard",
        help="A name for a subset of the measurements. Cannot contain spaces"
    )

    parser.add_argument(
        "-l",
        "--rx-lo",
        metavar="RX LO FREQ",
        type=float,
        action="store",
        dest="RX_LO_FREQ_GHZ",
        default=2.45,
        help="The frequency, in GHz, of the Rx LO"
    )

    parser.add_argument(
        "-b",
        "--rx-bw",
        metavar="RX RF BANDWIDTH",
        type=float,
        action="store",
        dest="RX_RF_BW_MHZ",
        default=0.5,
        help="The bandwidth, in MHz, of the Rx RF filter"
    )

    parser.add_argument(
        "-g",
        "--rx-gain",
        metavar="GAIN",
        type=int,
        action="store",
        dest="RX_GAIN_DB",
        default=20,
        help="The total gain, in dB, of the Rx chain"
    )

    parser.add_argument(
        "-s",
        "--sample-rate",
        type=float,
        action="store",
        dest="SAMPLE_RATE",
        default=1.024,
        help="The sample rate, in Msps, of the Rx ADC"
    )

    parser.add_argument(
        "-u",
        "--buf-size",
        type=int,
        action="store",
        dest="RX_BUFFER_SIZE",
        default=32768,
        help="The size, in samples, of the Rx buffer"
    )

    parser.add_argument(
        "-f",
        "--dds-freq",
        metavar="DDS FREQ",
        type=float,
        action="store",
        dest="DDS_FREQ_KHZ",
        default=200,
        help="The DDS frequency, in kHz. Input tone will be expected at"
             " (Rx LO + DDS)"
    )

    parser.add_argument(
        "-p",
        "--pol",
        metavar="POLARISATION",
        type=str,
        action="store",
        dest="POL",
        default="VV",
        help="The polarisation of the Tx and the Rx, e.g. VV, HH, VH, etc."
    )

    parser.add_argument(
        "-c",
        "--count",
        metavar="NUMBER",
        type=int,
        action="store",
        dest="NUM_MEAS",
        default=300,
        help="The number of measurements to take"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = cli_args()

    global_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    sdr_rx_logger = setup_logger(args.EXPERIMENT_NAME, global_timestamp)
    log_ntp_time(sdr_rx_logger, NTP_SERVER)

    try:
        pluto_cw_tone_rx(vars(args), sdr_rx_logger)
    except RuntimeError:
        sdr_rx_logger.info(
            "Please check the Pluto SDR is connected to this PC and running"
        )

    logging.shutdown()
