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

These scripts are used to automate the measurement of in-pipe RF propagation at ICAIR. There are two scripts, `prop_meas_rx.py` and `prop_meas_tx.py`, for the Rx and Tx unit respectively.

The scripts control and record data from two Analog Devices Pluto SDR units, nicknamed `plutoalice` and `plutobob`. There are two usage scenarios:

1. Both SDR units are connected to the same control computer. In this case just run the scripts one after the other with the parameters of your choice.
2. The SDR units are connected to single-board computers (SBCs), such as a Raspberry Pi, which themselves are remotely accessible. In this case each file needs to be copied to the respective SBC and then run locally.

The scripts take several command line arguments, the most important of which is the experiment name. Use that one to make sure your measurement files are not overwritten.

## Requirements

As my current `Python` development environment is a bit polluted, I'll list the required packages here. Apologies.

- `Python==3.6`
- `numpy==1.19.2`
- `ntplib==0.3.4`
- `pyadi>=0.0.6` -> special one, requires `libiio` installed with Python bindings

## TO DO

- Add modulated signals functionality
- Use generated signal instead of a DDS tone?
- Add unit and integration testing?
- Add CI for `Black` and `Bandit`?

## Contributing

Contributions are more than welcome and are in fact actively sought! Please contact Viktor either at [eenvdo@leeds.ac.uk](mailto:eenvdo@leeds.ac.uk) or on the `Pipebots` Slack.
