"""Pluto SDR control - Tx side

Automates the setup of a Pluto SDR unit as a CW transmitter. Fairly simple as
it uses the on-board DDS functionality to generate the tone to be sent over
the air. Once setup is complete the unit can be left alone until a different
combination of parameters needs to be configured.

Details of the unit are logged to make sure parameters have been properly
set up and to aid subsequent data analysis.
"""

import datetime
import argparse
import logging
from typing import Dict

import adi

import helpers


NTP_SERVER = "0.uk.pool.ntp.org"


def pluto_cw_tone_dds(params: Dict, logger: logging.Logger) -> None:
    """Sets up a Pluto SDR as a CW transmitter

    Uses the built-in DDS inside a Pluto SDR to continuously transmit a
    single tone. There are also two ways of controlling the output power level,
    either via the Tx attenuator or via DDS scaling.

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

    pluto.tx_lo = int(params["TX_LO_FREQ_GHZ"] * 1e9)
    logger.info(f"Tx LO set to {pluto.tx_lo} Hz")

    pluto.tx_rf_bandwidth = int(params["TX_RF_BW_MHZ"] * 1e6)
    logger.info(f"Tx RF bandwidth set to {pluto.tx_rf_bandwidth} Hz")

    pluto.tx_hardwaregain_chan0 = int(-params["TX_GAIN_DB"])
    logger.info(
        f"Tx attenuation set to" f" {pluto.tx_hardwaregain_chan0} dB"
    )

    pluto.dds_single_tone(
        int(params["DDS_FREQ_KHZ"] * 1e3), params["DDS_SCALE"]
    )
    logger.info(f"DDS frequency set to {params['DDS_FREQ_HZ']} kHz")
    logger.info(f"DDS scale set to {params['DDS_SCALE']}")

    logger.info(
        f"Tx Path Sample Rates: "
        f"{pluto._ctx.devices[1].attrs['tx_path_rates'].value}"
    )

    logger.info("Setup complete")


def cli_args() -> argparse.Namespace:
    """Process command-line arguments for Tx Pluto SDR

    Collects all necessary arguments for setting up a Pluto SDR as a CW
    transmitter. Default values are present for everything except the URI
    of the Pluto.

    Returns:
        argparse.Namespace: The processed parameters for later use

    Raises:
        Nothing

    Notes:
        The script will terminate if the URI of the SDR is not specified
    """

    parser = argparse.ArgumentParser(
        prog="prop_meas_tx",
        description="Sets up a Pluto SDR as a CW Tx. Uses the built-in DDS"
                    " to set the frequency of the output tone."
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
        dest="TX_LO_FREQ_GHZ",
        default=2.45,
        help="The frequency, in GHz, of the Tx LO"
    )

    parser.add_argument(
        "-b",
        "--tx-bw",
        metavar="TX RF BANDWIDTH",
        type=float,
        action="store",
        dest="TX_RF_BW_MHZ",
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
        dest="DDS_FREQ_KHZ",
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

    return parser.parse_args()


if __name__ == "__main__":
    args = cli_args()

    global_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    sdr_tx_logger = helpers.setup_logger(
        args.EXPERIMENT_NAME, global_timestamp
    )
    helpers.log_ntp_time(sdr_tx_logger, NTP_SERVER)

    try:
        pluto_cw_tone_dds(vars(args), sdr_tx_logger)
    except RuntimeError:
        sdr_tx_logger.info(
            "Please check the Pluto SDR is connected to this PC and running"
        )

    logging.shutdown()
