import adi


pluto = adi.Pluto("ip:plutoalice.local")

tx_lo_freq = int(2.45e9)
tx_rf_bw = int(500e3)

# -20 for all except 5.8 GHz, -10 then
tx_gain = int(-20)

dds_freq = int(100e3)
dds_scale = 1.0

pluto.tx_lo = tx_lo_freq
pluto.tx_rf_bandwidth = tx_rf_bw
pluto.tx_hardwaregain_chan0 = tx_gain

pluto.dds_single_tone(dds_freq, dds_scale)

print(f"DDS tone set to {dds_freq}")
