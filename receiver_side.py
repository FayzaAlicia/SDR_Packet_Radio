#Packet format:
#[Preamble] [Payload Length] [Payload Data] [CRC]
import globals

#INITIAL ASSUMPTIONS:
#No preamble search yet.
# No timing recovery yet.
# Assume the packet starts at sample 0.

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

#Find the offset index of the preamble
def findPreamble(data):
    for i in range(len(data) - globals.PREAMBLE_LEN + 1):
        if data[i:i + globals.PREAMBLE_LEN] == globals.PREAMBLE:
            return i
    return -1


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
        if i > 0:
            bpskDemappedData.append(0)
        else:
            bpskDemappedData.append(1)
    return bpskDemappedData


#Find the best offset index and retrun data sampled at that index
def bestOffsetedData(data):
    for i in range (globals.SPS):
        unsampledData = recoverSamples(data, i)
        demappedData = bpskDemapper(unsampledData)
        offsetIndex = findPreamble(demappedData)

        if offsetIndex != -1:
            return demappedData


#Recover different sections of packet
def recoverPacket(data):
    #remove preamble
    rxPacket = data[globals.PREAMBLE_LEN : ]

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
def receiver (data):
    #Find data at optimal sampled section
    rxData = bestOffsetedData(data)

    #Recover format of original packet
    payloadData, crc, recoveredPacket = recoverPacket(rxData)

    #Check if crc is valid
    validCRC = checkCRC(recoveredPacket, crc)

    #If crc is correct, recover original message
    ogMessage = ""
    if validCRC:
        ogMessage = binaryToASCII(payloadData, globals.PAYLOAD_LEN_LEN)

    return (ogMessage)