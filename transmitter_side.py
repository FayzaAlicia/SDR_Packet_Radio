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
import numpy as np
import globals
import adi
import time
sdr = adi.Pluto(uri="ip:192.168.2.1")


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
        noise = i + random.uniform(-globals.NOISE, globals.NOISE)
        noisyData.append(noise)
    return noisyData


#Binary Conversion
def convertToBinary(data):
    return ' '.join(f"{ord(char):08b}" for char in data).replace(" ", "")


#Assemple Packet into proper format
def assemblePacket(data):
    packet = []

    #add payload length
    payloadLength = len(data)//8 #convert from bits to bytes
    lengthString = format(payloadLength, "08b")

    for i in lengthString:
        packet.append(int(i))

    #add payload data
    for i in data:
        packet.append(int(i))

    #add crc
    for i in globals.crcCalculation(packet):
        packet.append(i)

    #add preamble & zeros buffer
    packet = globals.PREAMBLE + packet

    return packet


#BPSK Mapper
def bpskMapper (data):
    mappedData = [1 if bit == 0 else -1 for bit in data]
    return mappedData


#Sampling per Symbol
def sampleData(data, samples_per_symbol):
    sampledData = []
    for i in data:
        sampledData.append(i)
        for j in range(samples_per_symbol - 1):
            sampledData.append(0)
    return sampledData


#Final Transmitter
def transmitter(data):
    # Convert message to bits
    payloadBits = convertToBinary(data)

    # Build packet
    packetBits = assemblePacket(payloadBits)
    print (packetBits)

    # Map bits to BPSK symbols
    symbols = bpskMapper(packetBits)

    #silence/guard: symbol value 0
    guardSymbols = [0.0] * 50

    symbols = guardSymbols + symbols + guardSymbols

    # Upsample symbols
    upsampled = sampleData(symbols, globals.SPS)

    # Pulse shape
    shapedSignal = shapePulse(upsampled)

    #Convert to form pluto can read
    plutoIQ = makePlutoIQ(shapedSignal)

    # Add noise
    #noisySignal = generateNoise(shapedSignal)

    return plutoIQ


def makePlutoIQ(data):
    # Convert to numpy array so pluto can read wave
    tx = np.asarray(data, dtype=np.float32)

    #Remove dc offset and center baseband around 0
    tx = tx - np.mean(tx)

    # Find the largest sample magnitude then scale the whole waveform so the largest value becomes 1
    maxVal = np.max(np.abs(tx))
    tx = tx / maxVal

    # Scale the waveform down to 30% of full amplitude
    tx = tx * (2**14) * 0.3

    # Convert to IQ samples (complex numbers)
    tx_iq = tx.astype(np.complex64)

    #Transmit to pluto
    plutoTransmit(tx_iq)
    return tx_iq


def plutoTransmit(data):
    # Send repeatedly
    sdr.tx_cyclic_buffer = True
    sdr.tx(data)

    time.sleep(0.5)

def plutoStopTransmit():
    # Stop TX buffer
    sdr.tx_destroy_buffer()


def txBasicSettings(loopBack):
    # Basic settings
    sdr.sample_rate = int(1e6)
    sdr.tx_lo = int(915e6)
    sdr.tx_rf_bandwidth = int(500e3)

    sdr.gain_control_mode_chan0 = "slow_attack"
    sdr.tx_hardwaregain_chan0 = -30

    # Try internal loopback
    if loopBack:
        try:
            sdr.loopback = 1   # digital TX -> RX loopback on AD936x-style devices
            print("Loopback enabled.")
        except Exception as e:
            print("Loopback could not be enabled:", e)

#Pulse Shaping
def shapePulse (data):
    pulseFilter = globals.createFilter(globals.ALPHA,globals.SPS, globals.NUM_SYMBOLS)
    data = np.asarray(data, dtype=float)
    pulseFilter = np.asarray(pulseFilter, dtype=float)
    return np.convolve(data,pulseFilter, mode="same")
