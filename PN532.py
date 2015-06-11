# Example of detecting and reading a block from a MiFare NFC card.
# Author: Tony DiCola
# Copyright (c) 2015 Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import binascii
import sys
import pynats
import json
import ndef

import Adafruit_PN532 as PN532


# Setup how the PN532 is connected to the Raspbery Pi/BeagleBone Black.
# It is recommended to use a software SPI connection with 4 digital GPIO pins.

# Configuration for a Raspberry Pi:
CS   = 17  # GPIO 17, Pin# 11
MOSI = 27  # GPIO 27, Pin# 13
MISO = 22  # GPIO 22, Pin# 15
SCLK = 04  # GPIO 04, Pin# 07


def read_block(block):
    # Authenticate block for reading with default key (0xFFFFFFFFFFFF).
    if not pn532.mifare_classic_authenticate_block(uid, block, PN532.MIFARE_CMD_AUTH_B, 
                                                   [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]):
        print 'Failed to authenticate block %d!' % block
        return None

    # Read block data.
    data = pn532.mifare_classic_read_block(block)
    if data is None:
        print 'Failed to read block %d!' % block
        return None

    # 16 bytes data are returned
    print 'Read block %d: 0x%s' % (block, format(binascii.hexlify(data[:])))
    return data
    
def read_all_blocks():
    print 'read_all_blocks'
    blk=0
    while True:
        data = read_block(blk)
        if data is None:
            return
        blk +=1

def read_MAD_section(sec):
    blksPerSec = 4
    blk = (sec * blksPerSec)
    secData = bytearray()
    while blk < ((sec+1) * blksPerSec): 
        blkData = read_block(blk)
        if blkData is not None:
            secData = secData + blkData
            blk += 1
        else:
            return None

    return secData

MAD_HDR_TYPE = 0
MAD_HDR_LENGTH = 1
MAD_HDR_VALUE = 2

def get_NDEF_from_MAD(sec_byte_array):
    # process TLV
    hex = 0x00
    idx = 0
    rec = 0
    mad_hdr_curr = MAD_HDR_TYPE
    msgLen = 0
    while hex is not 0xfe: 
        hex = sec_byte_array[idx]
        if mad_hdr_curr is MAD_HDR_TYPE:
            print 'Type is 0x%02x' %  hex
            mad_hdr_curr = MAD_HDR_LENGTH
        elif mad_hdr_curr is MAD_HDR_LENGTH:
            print 'Length is %d' % hex
            if hex is 0x00:
                rec += 1
                mad_hdr_curr = MAD_HDR_TYPE # type of next record
                print 'Get next record: %d' % rec
            else:
                msgLen = hex
                mad_hdr_curr = MAD_HDR_VALUE
        elif mad_hdr_curr is MAD_HDR_VALUE:
            print sec_byte_array[idx:(idx+msgLen)]
            return sec_byte_array[idx:(idx+msgLen)]
            
        idx = idx + 1

def parseNDEF(sec):
    sectionData = read_MAD_section(sec)
    #print sectionData

    if sectionData is None:
        print 'Unable to parse NDEF since MAD section %d is not completely read' % (sec)
        return None

    ndefData = get_NDEF_from_MAD(sectionData)
    #print ndefData

    message_data = '%s' % binascii.hexlify(ndefData[:])
    message_data = message_data.decode('hex')
    message = ndef.NdefMessage(message_data)
    record = message.records[0]

    payload = "%s" % (record.payload)
    payloadNoISOCode = payload[3:]
    #print 'payload: %s' % payloadNoISOCode
    return payloadNoISOCode

# Create an instance of the PN532 class.
pn532 = PN532.PN532(cs=CS, sclk=SCLK, mosi=MOSI, miso=MISO)

# Call begin to initialize communication with the PN532.  Must be done before
# any other calls to the PN532!
pn532.begin()

# Get the firmware version from the chip and print it out.
ic, ver, rev, support = pn532.get_firmware_version()
print 'Found PN532 with firmware version: {0}.{1}'.format(ver, rev)

# Configure PN532 to communicate with MiFare cards.
pn532.SAM_configuration()

isCardDetected = 0

# nats.io
c= pynats.Connection(verbose=True)
c.connect()

# Main loop to detect cards and read a block.
print 'Waiting for MiFare card...'
while True:
    # Check if a card is available to read.
    uid = pn532.read_passive_target()
    # Try again if no card is available.
    if uid is None:
        if isCardDetected is 1:
            isCardDetected = 0
            print 'card left'
    else:
        if isCardDetected is 0:
            isCardDetected = 1
            print 'card detected! UID: 0x{0}'.format(binascii.hexlify(uid))

            payload = {"id":"0x%s" % (binascii.hexlify(uid))}
            c.publish('humix.sense.detect.event', json.dumps(payload))

            payload = parseNDEF(1)
            if payload is None:
                continue
            msg = {"text":"%s" % payload}
            print 'publishing speech.command with msg: %s...' % msg
            c.publish('humix.sense.speech.command', json.dumps(msg))
