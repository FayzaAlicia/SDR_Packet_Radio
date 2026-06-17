#Packet format:
#[Preamble] [Payload Length] [Payload Data] [CRC]

#Flow:
# User data
# ↓
# Convert data to bits
# ↓
# Build packet
# ↓
# Add payload length/header
# ↓
# Calculate and append CRC
# ↓
# Add preamble
# ↓
# Map bits to BPSK symbols
# ↓
# Pulse Shaping
# ↓
# Add noise
# ↓
# Transmit signal

import random
import numpy as math

import globals
from globals import preamble


#Random Data Generator
def generateData (dataSize):
    data = []
    for i in range(dataSize):
        data.append(random.randint(0,1))
    return data

#Noise Generator
def generateNoise(data):
    noisyData = []
    for i in data:
        noise = i + random.uniform(-0.1, 0.1)
        noisyData.append(noise)
    return noisyData

#Binary Conversion
def convertToBinary(data):
    return ' '.join(f"{ord(char):08b}" for char in data).replace(" ", "")

#Assemple Packet into proper format
def assemblePacket(data):
    packet = []

    #add payload length
    payloadLength = len(data)
    lengthString = format(payloadLength, "08b")

    for i in lengthString:
        packet.append(int(i))

    #add payload data
    for i in data:
        packet.append(int(i))

    #add crc
    for i in globals.crcCalculation(packet):
        packet.append(i)

    #add preamble
    for i in reversed (preamble):
        packet.insert(0, i)

    return packet

#BPSK Mapper
def bpskMapper (data):
    mappedData = [1 if bit == 0 else -1 for bit in data]
    return mappedData

#Sampling per Symbol
def sampleData(data, samples_per_symbol):
    sampledData = []
    for i in data:
        sampledData.append(data[i])
        for j in range(samples_per_symbol - 1):
            sampledData.append(0)
    return sampledData

#Final Transmitter
def transmitter(data):
    # Convert message to bits
    payloadBits = convertToBinary(data)

    # Build packet
    packetBits = assemblePacket(payloadBits)

    # Map bits to BPSK symbols
    symbols = bpskMapper(packetBits)

    # Upsample symbols
    upsampled = sampleData(symbols, globals.samples_per_symbol)

    # Pulse shape
    shapedSignal = globals.shapePulse(upsampled)

    # Add noise
    noisySignal = generateNoise(shapedSignal)

    return noisySignal