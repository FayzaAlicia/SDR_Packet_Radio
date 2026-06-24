#Packet format:
#[Preamble] [Payload Length] [Payload Data] [CRC]
import numpy as np

PREAMBLE = [
    1, 1, 1, 0, 1, 0, 0, 1,
    0, 1, 1, 0, 0, 0, 1, 0,
    1, 0, 1, 1, 1, 0, 0, 1,
    1, 0, 0, 0, 1, 1, 0, 1
]
CRC8 = [1, 0, 0, 0, 0, 0, 1, 1, 1]
PREAMBLE_LEN = len(PREAMBLE)
PAYLOAD_LEN_LEN = 8
CRC_LEN = len(CRC8) - 1
NOISE = 0.1
SPS = 8 # Samples per symbol (oversampling rate)
ALPHA = 0.35      # Roll-off factor (typically between 0.2 and 0.5)
NUM_SYMBOLS = 10  # Filter span (how many symbols wide the filter is)

# CRC Calculation
def crcCalculation(data):
    workingData = data.copy()

    # Add zeros at the end.
    # Since crc8 has 9 bits, the remainder will be 8 bits.
    for i in range(len(CRC8) - 1):
        workingData.append(0)

    # Do binary long division using XOR
    for i in range(len(data)):
        match workingData[i]:
            case 1:
                for j in range(len(CRC8)):
                    workingData[i + j] = workingData[i + j] ^ CRC8[j]

            case 0:
                pass

    # The CRC remainder is the last 8 bits
    remainder = []

    for i in range(len(data), len(workingData)):
        remainder.append(workingData[i])

    return remainder

#Create Root Raised Cosine Filter
def createFilter(alpha, sps, numSymbs):
    pi = np.pi

    numTaps = sps * numSymbs + 1
    t = np.arange(-numTaps//2 + 1, numTaps//2 + 1,) / sps
    h = np.zeros(numTaps)

    for i in range (len(t)):
        if t[i] == 0:
            #h(0)=1 + α(4/π - 1)
            h[i] = 1 + alpha * ((4/pi) - 1)

        elif np.isclose(abs(t[i]), 1/(4 * alpha)):
            #h(t) = a/√2 [(1 + 2/π) sin(π/ 4a) + (1 - 2/π) cos(π/ 4a)]
            h[i] = (alpha / np.sqrt(2)) * ((1 + 2/pi) * np.sin(pi/ (4*alpha)) + (1 - 2/pi) * np.cos(pi/ (4*alpha)))

        else:
            #h(t) = [sin(πt(1−α))+4αtcos(πt(1+α))] / [πt(1−(4αt)2^)]
            numerator = np.sin(pi*t[i]*(1 - alpha)) + 4 * alpha * t[i] * np.cos(pi * t[i] * (1 + alpha))
            denominator = pi * t[i]*(1 - (4 * alpha * t[i])**2)
            h[i] = numerator/denominator

    h = h / np.sqrt(np.sum(h ** 2))
    return h