#Packet sections
import numpy as math

preamble = [1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0]
crc8 = [1,0,0,0,0,0,1,1,1]
PREAMBLE_LEN = 16
PAYLOAD_LEN = 8
CRC_LEN = 8
samples_per_symbol = 8 # Samples per symbol (oversampling rate)
alpha = 0.35      # Roll-off factor (typically between 0.2 and 0.5)
num_symbols = 10  # Filter span (how many symbols wide the filter is)

# CRC Calculation
def crcCalculation(data):
    workingData = []

    # Copy data into workingData
    for bit in data:
        workingData.append(int(bit))

    # Add zeros at the end.
    # Since crc8 has 9 bits, the remainder will be 8 bits.
    for i in range(len(crc8) - 1):
        workingData.append(0)

    # Do binary long division using XOR
    for i in range(len(data)):
        match workingData[i]:
            case 1:
                for j in range(len(crc8)):
                    workingData[i + j] = workingData[i + j] ^ crc8[j]

            case 0:
                pass

    # The CRC remainder is the last 8 bits
    remainder = []

    for i in range(len(data), len(workingData)):
        remainder.append(workingData[i])

    return remainder

#Create Raised Cosine Filter
def createFilter(alpha, sps, numSymbs):
    pi = math.pi

    numTaps = sps * numSymbs + 1
    t = math.arange(-numTaps/2 + 1, numTaps/2 + 1,) / sps
    h = math.zeros(numTaps)

    for i in range (len(t)):
        if t[i] == 0:
            #h(0)=1 + α(4/π - 1)
            h[i] = 1 + alpha * ((4/pi) - 1)

        elif math.isclose(abs(t[i]), 1/(4 * alpha)):
            #h(t) = a/√2 [(1 + 2/π) sin(π/ 4a) + (1 - 2/π) cos(π/ 4a)]
            h[i] = (alpha / math.sqrt(2)) * ((1 + 2/pi) * math.sin(pi/ (4*alpha)) + (1 - 2/pi) * math.cos(pi/ (4*alpha)))

        else:
            #h(t) = [sin(πt(1−α))+4αtcos(πt(1+α))] / [πt(1−(4αt)2^)]
            numerator = math.sin(pi*t[i]*(1 - alpha)) + 4 * alpha * t[i] * math.cos(pi * t[i] * (1 + alpha))
            denominator = pi * t[i]*(1 - (4 * alpha * t[i])**2)
            h[i] = numerator/denominator

    return h

#Pulse Shaping
def shapePulse (data):
    pulseFilter = createFilter(alpha, samples_per_symbol, num_symbols)
    data = math.asarray(data, dtype=float)
    pulseFilter = math.asarray(pulseFilter, dtype=float)
    return math.convolve(data,pulseFilter, mode="same")