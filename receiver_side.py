#Packet format:
#[Preamble] [Payload Length] [Payload Data] [CRC]
import globals
from globals import PAYLOAD_LEN


#INITIAL ASSUMPTIONS:
#No preamble search yet.
# No timing recovery yet.
# Assume the packet starts at sample 0.
# Use clean signal first, not noisy signal.

#Flow:
# noisySignal
# ↓
# matched filter / sampling
# ↓
# recover BPSK symbols (symbols per sample)
# ↓
# BPSK demap
# ↓
# recover packet bits
# ↓
# find preamble
# ↓
# read length
# ↓
# extract payload
# ↓
# check CRC
# ↓
# recover original message
# ↓
#BER

#Unsample data
def recoverSamples (data):
    unsampledData = []

    for i in range(0, len(data) - 1, globals.samples_per_symbol):
        unsampledData.append(data[i])

    return unsampledData

#Remap from bpsk to binary
def bpskDemapper(data):
    bpskDemappedData = []
    for i in data:
        if i > 0:
            bpskDemappedData.append(0)
        else:
            bpskDemappedData.append(1)
    return bpskDemappedData

#Recover different sections of packet
def recoverPacket(data):
    payloadData = []
    crc = []
    crcCheckPacket = data.copy()

    #remove preamble and crc
    del crcCheckPacket[0:globals.PREAMBLE_LEN]
    del crcCheckPacket[-globals.CRC_LEN:]

    #remove preamble, payload length, and crc
    payloadData = data[:-globals.CRC_LEN]
    del payloadData[0:globals.PREAMBLE_LEN + globals.PAYLOAD_LEN]

    #find crc
    crc = data[-globals.CRC_LEN:]

    return payloadData, crc, crcCheckPacket

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
def receiver (data):
    #Return data to before it was sampled
    unsampledData = recoverSamples(data)

    #return bpsk mapping to binary
    demappedData = bpskDemapper(unsampledData)

    #Recover format of original packet
    recoveredPacked, crc, crcCheckPacket = recoverPacket(demappedData)

    #Check if crc is valid
    validCRC = checkCRC(crcCheckPacket, crc)

    #If crc is correct, recover original message
    ogMessage = ""
    if validCRC:
        ogMessage = binaryToASCII(recoveredPacked, globals.PAYLOAD_LEN)

    return (ogMessage)