import time
import numpy as np
import adi


SDR_URI = "ip:plutobob.local"

rx_lo_freq = int(2.45e9)
rx_rf_bw = int(500e3)
samp_rate = int(1024000)
rx_buf_size = int(32768)

filename_base = "meas_100"
tx_pol = "H"
rx_pol = "H"

num_meas = 500

pluto = adi.Pluto(SDR_URI)
ad9361_phy = pluto._ctrl
tx_lo = ad9361_phy.find_channel("TX_LO")
tx_lo.attrs["powerdown"].value = str(int(1))

pluto.rx_lo = rx_lo_freq
pluto.rx_rf_bandwidth = rx_rf_bw
pluto.sample_rate = samp_rate
pluto.rx_buffer_size = rx_buf_size

pluto.gain_control_mode_chan0 = "manual"
pluto.rx_hardwaregain_chan0 = 20

for idx in range(num_meas):
    filename = '_'.join([filename_base, str(rx_lo_freq), str(20),
                         tx_pol, rx_pol, str(idx)])
    filename = '.'.join([filename, 'iqbin'])
    samples = pluto.rx()
    samples = samples.astype(np.complex64)
    samples.tofile(filename)
    print(f"Wrote data: {filename}")
    time.sleep(1)
