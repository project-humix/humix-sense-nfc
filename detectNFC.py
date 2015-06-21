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

import Adafruit_PN532 as PN532


# Setup how the PN532 is connected to the Raspbery Pi/BeagleBone Black.
# It is recommended to use a software SPI connection with 4 digital GPIO pins.

# Configuration for a Raspberry Pi:
CS   = 17  # GPIO 17, Pin# 11
MOSI = 27  # GPIO 27, Pin# 13
MISO = 22  # GPIO 22, Pin# 15
SCLK = 04  # GPIO 04, Pin# 07

# Configuration for a BeagleBone Black:
# CS   = 'P8_7'
# MOSI = 'P8_8'
# MISO = 'P8_9'
# SCLK = 'P8_10'

        

def read_block(block):
    # Authenticate block 4 for reading with default key (0xFFFFFFFFFFFF).
    if not pn532.mifare_classic_authenticate_block(uid, block, PN532.MIFARE_CMD_AUTH_B, 
                                                   [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]):
        print 'Failed to authenticate block %d!' % block
        return None
    # Read block 4 data.
    #data = pn532.mifare_classic_read_block(4)
    data = pn532.mifare_classic_read_block(block)
    if data is None:
        print 'Failed to read block %d!' % block
        return None
    # Note that 16 bytes are returned, so only show the first 4 bytes for the block.
    #print 'Read block 4: 0x{0}'.format(binascii.hexlify(data[:4]))
    print 'Read block %d: 0x%s' % (block, format(binascii.hexlify(data[:])))
    return data
    # Example of writing data to block 4.  This is commented by default to
    # prevent accidentally writing a card.
    # Set first 4 bytes of block to 0xFEEDBEEF.
    # data[0:4] = [0xFE, 0xED, 0xBE, 0xEF]
    # # Write entire 16 byte block.
    # pn532.mifare_classic_write_block(4, data)
    # print 'Wrote to block 4, exiting program!'
    # # Exit the program to prevent continually writing to card.
    # sys.exit(0)
    
def read_all_blocks():
    print 'read_all_blocks'
    blk=0
    while True:
        data = read_block(blk)
        if data is None:
            return
        blk +=1

def test():
    print 'test'

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


def ping_callback(msg):
    print 'Received a message: %s' % msg.data
    c.publish('humix.sense.nfc.status.pong','received')
#    c.wait(count=1)
    

c.subscribe('humix.sense.nfc.status.ping', ping_callback)
#c.wait(count=1)



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
        continue
    else:
        if isCardDetected is 0:
	    isCardDetected = 1
   	    print 'card detected!'
  	    payload = {"id":"0x%s" % (binascii.hexlify(uid))}
	    c.publish('humix.sense.detect.event', json.dumps(payload))
        #read_block(0)
        #read_block(1)
        test()
        #read_all_blocks()
	continue

    print 'Found card with UID: 0x{0}'.format(binascii.hexlify(uid))
    
