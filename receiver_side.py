import globals
import adi
import numpy as np
import transmitter_side

sdr = adi.Pluto(uri="ip:192.168.2.1")

#Flow:
# complex IQ samples from Pluto
# ↓
# remove DC offset
# ↓
# matched filter
# ↓
# try every sample offset
# ↓
# for each offset, sample every SPS
# ↓
# find preamble
# ↓
# estimate phase
# ↓
# rotate
# ↓
# demap to bits
# ↓
# remove preamble
# ↓
# read length
# ↓
# extract payload and CRC
# # ↓
# check CRC
# ↓
# recover original message
# ↓
#BER

def debugPreamblePhase(data, bestIndex):
    preamble = np.array(
        [1 if bit == 0 else -1 for bit in globals.PREAMBLE],
        dtype=complex
    )

    segment = np.array(data[bestIndex:bestIndex + len(preamble)], dtype=complex)

    # Remove known BPSK signs
    product = segment * np.conjugate(preamble)

    phases = np.unwrap(np.angle(product))

    # print("Preamble phases:")
    # print([round(p, 3) for p in phases])


#Find the offset index of the preamble
def findPreamble(data):
    bpskPreamble = np.array(
        [1 if bit == 0 else -1 for bit in globals.PREAMBLE],
        dtype=complex
    )

    data = np.array(data, dtype=complex)

    maxStrength = 0
    bestIndex = 0
    bestCorrelation = 0

    preambleEnergy = np.sqrt(np.sum(np.abs(bpskPreamble) ** 2))

    for i in range(len(data) - len(bpskPreamble) + 1):
        segment = data[i:i + len(bpskPreamble)]

        correlation = np.sum(segment * np.conjugate(bpskPreamble))

        segmentEnergy = np.sqrt(np.sum(np.abs(segment) ** 2))

        if segmentEnergy == 0:
            continue

        strength = abs(correlation) / (segmentEnergy * preambleEnergy)

        if strength > maxStrength:
            maxStrength = strength
            bestIndex = i
            bestCorrelation = correlation

    phaseShift = np.angle(bestCorrelation)

    preambleFound = data[bestIndex:]
    correctedData = shiftPhase(preambleFound, phaseShift)

    return correctedData, maxStrength, bestIndex, phaseShift


def shiftPhase(data, angle):
    shiftedData = []
    for i in data:
        corrected = i * np.exp(-1j * angle)
        shiftedData.append(corrected)
    return shiftedData


#Unsample data
def recoverSamples (data, offset = 0):
    unsampledData = []

    for i in range(offset, len(data) - 1, globals.SPS):
        unsampledData.append(data[i])

    return unsampledData


#Remap from bpsk to binary
def bpskDemapper(data):
    bpskDemappedData = []
    for i in data:
        if i.real > 0:
            bpskDemappedData.append(0)
        else:
            bpskDemappedData.append(1)
    return bpskDemappedData


#Find the best offset index and retrun data sampled at that index
def bestOffsetedData(data):
    bestStrength = 0
    bestDemappedData = []
    bestOffset = 0
    bestPreambleIndex = 0
    bestPhaseShift = 0
    bestUnsampledData = None

    for offset in range(globals.SPS):
        unsampledData = recoverSamples(data, offset)
        correctedData, strength, preambleIndex, phaseShift = findPreamble(unsampledData)
        demappedData = bpskDemapper(correctedData)

        matches = sum(
            a == b
            for a, b in zip(demappedData[:globals.PREAMBLE_LEN], globals.PREAMBLE)
        )

        if strength > bestStrength:
            bestStrength = strength
            bestDemappedData = demappedData
            bestOffset = offset
            bestPreambleIndex = preambleIndex
            bestPhaseShift = phaseShift
            bestUnsampledData = unsampledData

    # print("Chosen offset:", bestOffset)
    # print("Chosen preamble index:", bestPreambleIndex)
    # print("Chosen phase shift:", bestPhaseShift)
    # print("Expected preamble:", globals.PREAMBLE)
    # print("Received preamble:", bestDemappedData[:globals.PREAMBLE_LEN])
    # print("Preamble matches:", matches, "/", globals.PREAMBLE_LEN)
    # print("Chosen data:", bestDemappedData)

    if bestStrength < 0.75:
        print("No reliable preamble lock.")
        return []

    debugPreamblePhase(bestUnsampledData, bestPreambleIndex)

    return bestDemappedData


#Recover different sections of packet
def recoverPacket(data):
    #remove preamble
    rxPacket = data[globals.PREAMBLE_LEN : ]
    # print("Bits after preamble:", rxPacket[:32])
    # print("Length bits:", rxPacket[0:globals.PAYLOAD_LEN_LEN])

    #find payload length
    payloadLength = int("".join(map(str, rxPacket[0:globals.PAYLOAD_LEN_LEN])), 2) * 8 #convert from bytes to bits

    #find payload data
    payloadData = rxPacket[globals.PAYLOAD_LEN_LEN:globals.PAYLOAD_LEN_LEN + payloadLength]

    #find crc
    crc = rxPacket[globals.PAYLOAD_LEN_LEN + payloadLength : globals.PAYLOAD_LEN_LEN + payloadLength + globals.CRC_LEN]

    #Data used to calculate rx crc
    rxPacket = rxPacket[:globals.PAYLOAD_LEN_LEN + payloadLength]

    return payloadData, crc, rxPacket


#Calculate and check CRC
def checkCRC(data, txCRC):
    crc = globals.crcCalculation(data)
    if crc == txCRC:
        return True
    else:
        return False


#Re-convert binary into original message transmitted
def binaryToASCII(data, payloadLength):
    return "".join(
        chr(int("".join(map(str, data[i:i + payloadLength])), 2))
        for i in range(0, len(data), payloadLength)
    )


#Final Receiver
def receiver():
    #Convert from pluto form
    data = retreivePlutoIQ()

    # Convert to numpy array
    data = np.array(data)

    # Remove DC offset
    data = data - np.mean(data)

    # Matched filter FIRST, while data is still complex IQ samples
    data = matchedFilter(data)

    # Now find the best symbol timing offset, preamble, phase, and demap
    rxData = bestOffsetedData(data)

    packetValid = False

    ogMessage = ""
    print(bool(rxData))

    if bool(rxData):
        # Recover packet
        payloadData, crc, recoveredPacket = recoverPacket(rxData)

        # Check CRC
        validCRC = checkCRC(recoveredPacket, crc)

        if validCRC:
            ogMessage = binaryToASCII(payloadData, 8)
            packetValid = True

        return ogMessage, packetValid, rxData

    else:
        ogMessage = "CRC not matching"
        return ogMessage, packetValid, []


def rxBasicSettings():
    # Basic settings
    sdr.sample_rate = int(1e6)
    sdr.rx_lo = int(915e6)
    sdr.rx_rf_bandwidth = int(500e3)

    sdr.rx_buffer_size = 16384
    sdr.gain_control_mode_chan0 = "manual"
    sdr.rx_hardwaregain_chan0 = 20


def retreivePlutoIQ():
    # Receive samples
    rx_iq = sdr.rx()

    #Stop transmission
    transmitter_side.plutoStopTransmit()

    #Convery array to list  so receiver can decode it
    rx_iq = rx_iq.tolist()

    return rx_iq

#Match filter
def matchedFilter(data):
    pulseFilter = globals.createFilter(globals.ALPHA, globals.SPS, globals.NUM_SYMBOLS)
    data = np.asarray(data, dtype=complex)
    pulseFilter = np.asarray(pulseFilter, dtype=float)
    return np.convolve(data, pulseFilter, mode="same")