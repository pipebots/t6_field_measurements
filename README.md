```
 __________.__             ___.     |__|  __
 \______   \__|_____   ____\_ |__   _||__/  |_  ______ (C) George Jackson-Mills 2020
  |     ___/  \____ \_/ __ \| __ \ /  _ \   __\/  ___/
  |    |   |  |  |_> >  ___/| \_\ (  O_O )  |  \___ \
  |____|   |__|   __/ \___  >___  /\____/|__| /____  >
              |__|        \/    \/                 \/
```

# In-Pipe RF Propagation Measurements - ICAIR

## Overview

This repository holds all the test and measurement automation code used for running Theme 6's experiments at ICAIR, or really anywhere else that has suitable conditions. There are two main types of experiments, propagation measurements and OpenThread network measurements. **Please note, that both of these are for the case of empty, or partially-filled sewer pipes.**

The code is separated in different folders, `prop_meas` and `ot_ntwk_meas` respectively. For completeness, there are also some old bash scripts in `ot_ntwk_meas_old`, which serverd as a basis for the automated ones in `ot_ntwk_meas`.

### Propagation measurements

These are performed using two Pluto SDR units, themselves connected to two Raspberry Pis. The Pis are there to save the measurement data and provide power to the SDRs. The Pis themselves are powered through a PoE HAT and a PoE switch. This was the most straightforward setup I came up with, as it also provides quick and easy SSH access to the Pis.

The way the experiment is set up is to have one pair of Pi/Pluto be a transmitter, and the second one a receiver. Therefore, one runs the `prop_meas_tx.py` script, and one runs the `prop_meas_rx.py` one. Ideally, you would want to set up your transmitter before you start receiving and recording data.

Both scripts use a command-line interface, which makes it quicker and hopefully easier to specify parameters such as carrier frequency, power, offsets, number of recordings, name of experiments, and so on. The received data is stored in an HDF5 file, which is quite popular in the scientific/engineering worlds for storing data.

### OpenThread Network Measurements

These measurements aim to assess how well an OpenThread mesh network will perform when deployed in a sewer pipe. They are a bit more involved than the propagation ones, and consists of four (4) nRF52840 dongles connected to four Raspberry Pis. Similar to the propagation measurements case, the Pis are powered through PoE, and in turn power the dongles through standard USB. The dongles are introduced into the buried pipe through the observation holes.

Once in the pipe, the `ot_ntwk_meas` script should be run from a main computer/laptop, which is also connected to the same network as the Pis, through the PoE switch. The script connects to all four nodes, does all the necessary set up, and runs ping, i.e. latency tests, and TCP and UDP throughput tests. As part of the code for this experiment I have written up something called `remote_ot_node` which is responsible for configuring the individual OpenThread nodes. It does that through SSH commands.

Once all the measurements have completed, the script resets the OpenThread devices and disconnects from the Pis. All data is saved as plaintext for later analysis.

It is important to note that the `ot_ntwk_meas` script expects two configuration files - one for the login details for the Pis, and their logical names within the OpenThread network, and one which specifies the network topology, i.e. which node is connected to which other ones. There are four such configurations here, used in different cases:

- `four_nodes_linear` - the one used most often at ICAIR, or in 2.61B for baseline measurements. Four nodes connected in a linear daisy chain.
- `four_nodes_ros` - same as above, however the Pis are also running ROS2. I use different SD cards for this experiment, to avoid dependencies and compatibility issues.
- `two_nodes` - when running the measurements in the short pipe section, or obtaining a baseline for single-hop performance.
- `three_nodes_nitm` - used when measuring the energy consumption of an OpenThread node that acts as a simple relay, and does not transmit or receive its own traffic.

## Requirements

As my current `Python` development environment is a bit polluted, I'll list the required packages here. Apologies.

- `numpy`
- `pyyaml`
- `ntplib`
- `h5py`
- `netmiko`
- `pyadi` -> special one, requires `libiio` installed with Python bindings. Available from Analog Devices.

## TO DO

- Add modulated signals functionality
- Use generated signal instead of a DDS tone?
- Add unit and integration testing?
- Add CI for `Black` and `Bandit`?

## Contributing

Contributions are more than welcome and are in fact actively sought! Please contact Viktor either at [v.doychinov@bradford.ac.uk](mailto:v.doychinov@bradford.ac.uk).

## Acknowledgements

This work is supported by the UK's Engineering and Physical Sciences Research Council (EPSRC) Programme Grant EP/S016813/1
