import random
from transmitter_side import generate_random_string, transmitter
from receiver_side import receiver

def sendMultiplePackets (numPackets):
    packetErrors = numPackets
    ber = 0
    totalNumBits = 0

    for i in range(numPackets):
        txData = generate_random_string(random.randint(1,100))
        txPacketBits = transmitter(txData)
        _, validPacket, rxPacketBits = receiver()

        if validPacket:
            packetErrors -= 1
            temp1, temp2 = berCalc(rxPacketBits, txPacketBits)
            ber += temp1
            totalNumBits += temp2

    ber = ber / totalNumBits * 100
    packetErrors = packetErrors/numPackets * 100

    return ber, packetErrors

def berCalc(txBits, rxBits):
    matchingBits = 0
    for i in range (len(rxBits)):
        if txBits[i] == rxBits[i]:
            matchingBits += 1
    return matchingBits, len(rxBits)
