"""
Center frequency of key fob: 312.25MHz

~715 samples / bit
"""
from rtlsdr import RtlSdr
import numpy as np
import numpy.fft as fft
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter, freqz


def read_sdr():
    sdr = RtlSdr()
    sdr.center_freq = 312.25e6
    sdr.gain = 'auto'

    while True:
        samples = sdr.read_samples(sdr.sample_rate)
        print(np.max(np.abs(samples)))

        if np.max(np.abs(samples)) > 0.2:
            with open('keyfob_data.npy', 'wb') as f:
                np.save(f, samples)

            break


def lowpass(data, cutoff, fs, order=5):
    b, a = butter(order, cutoff, fs=fs, btype='low', analog=False)
    return lfilter(b, a, data)


def digital_decode(data, padding=0.1, samples_per_bit=715):
    data_abs = np.abs(data)
    data_max = np.max(data_abs)
    data_min = np.min(data_abs)
    data_range = data_max - data_min
    data_padding = data_range * padding
    data_mid = data_min + (data_range / 2)

    threshold_high = data_mid + data_padding
    threshold_low = data_mid - data_padding

    # algorithm:
    # 1 - find transition
    # 2 - move forward samples_per_bit / 2
    # 3 - move forward samples_per_bit or until transition
    # 4 - if transition, adjust samples_per_bit, GOTO 2
    # 5 - if no transition, GOTO 3
    # 6 - if no transition for two cycles, break

    data_idx = 0
    decoded = [0]
    high = False

    # find first edge
    while data_abs[data_idx] < threshold_high:
        data_idx += 1

    data_idx += samples_per_bit // 2

    while data_idx < len(data_abs):
        for offset in range(samples_per_bit):
            if data_idx >= len(data_abs):
                break

            data_point = data_abs[data_idx]
            data_idx += 1

            # check for transition
            # TODO: adjust samples_per_bit based on edge
            if high and data_point < threshold_low:
                high = False
                decoded.append(0)
                data_idx += samples_per_bit // 2
                break
            elif not high and data_point > threshold_high:
                high = True
                decoded.append(1)
                data_idx += samples_per_bit // 2
                break
        else:
            decoded.append(1 if high else 0)
            if decoded[:-3] in ([0, 0, 0] or [1, 1, 1]):
                break

    return decoded


def manchester_decode(data):
    decoded = []

    for idx in range(0, len(data) - 1, 2):
        a, b = data[idx], data[idx + 1]

        if a == b:
            print(f'Manchester decoding error: {idx}')

        decoded.append(a)

    return decoded


def process():
    with open('keyfob_data.npy', 'rb') as f:
        samples = np.load(f)

    filtered = lowpass(samples, 15e6, 312.25e6)

    digital = digital_decode((np.abs(filtered)))
    print(digital)
    decoded = manchester_decode(digital)
    print(decoded)

    print(hex(int(''.join(str(d) for d in decoded), 2)))

    plt.plot(np.abs(filtered))
    plt.show()


if __name__ == '__main__':
    process()