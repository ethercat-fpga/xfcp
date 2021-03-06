#!/usr/bin/env python
"""

Copyright (c) 2017 Alex Forencich

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

from __future__ import print_function

import argparse
import time

import xfcp.interface, xfcp.node
import gty_node

def main():
    #parser = argparse.ArgumentParser(description=__doc__.strip())
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=str, default='/dev/ttyUSB1', help="Port")
    parser.add_argument('-b', '--baud', type=int, default=115200, help="Baud rate")
    parser.add_argument('-H', '--host', type=str, help="Host (i.e. 192.168.1.128:14000)")

    args = parser.parse_args()

    port = args.port
    baud = args.baud
    host = args.host

    intf = None

    if host is not None:
        # ethernet interface
        intf = xfcp.interface.UDPInterface(host)
    else:
        # serial interface
        intf = xfcp.interface.SerialInterface(port, baud)

    n = intf.enumerate()

    print("XFCP node tree:")
    print('\n'.join(format_tree(n)))

    print("Testing XFCP RAMs")
    n[0].write(0, b'RAM 0 test string!')
    n[1].write(0, b'RAM 1 test string!')
    print(n[0].read(0, 18))
    print(n[1].read(0, 18))

    n[0].write(0, b'Another RAM 0 test string!')
    print(n[0].read(0, 26))

    n[1].write_dword(16, 0x12345678)

    print(hex(n[1].read_dword(16)))

    # enumerate i2c bus

    print("I2C bus slave addresses:")
    for k in range(128):
        n[2].read_i2c(k, 1)
        if n[2].get_i2c_status() == 0:
            print(hex(k))

    # configure oscillator

    print("Set oscillator to 322.265625 MHz")
    n[2].write_i2c(0x75, b'\x00') # U80 (0x75) disconnect all outputs
    n[2].write_i2c(0x74, b'\x01') # U28 (0x74) connect only ouput 0 to SI570
    n[2].write_i2c(0x5d, b'\x89\x10') # freeze DCO (137: 0x10)
    # Freq: 322.2656250000 HS_DIV=4 N1=4 DCO=5156.2 RFREQ=0x02D1E36BF3
    n[2].write_i2c(0x5d, b'\x07\x00\xC2\xD1\xE3\x6B\xF3')
    n[2].write_i2c(0x5d, b'\x89\x00') # unfreeze DCO (137: 0x10)
    n[2].write_i2c(0x5d, b'\x87\x40') # new frequency (135: 0x40)

    # loopback test

    print("Place transceivers in PRBS7 mode")
    for i in range(4):
        n[3][i].set_tx_prbs_mode(gty_node.PRBS_MODE_PRBS7)
        n[3][i].set_rx_prbs_mode(gty_node.PRBS_MODE_PRBS7)

    for i in range(4):
        n[3][i].reset()

    time.sleep(0.01)

    for i in range(4):
        n[3][i].rx_err_count_reset()
        n[3][i].is_rx_prbs_error()

    time.sleep(0.01)

    for i in range(4):
        print("CH %d locked: %d  errors: %d  error count: %d" % (i,
            n[3][i].is_rx_prbs_locked(),
            n[3][i].is_rx_prbs_error(),
            n[3][i].get_rx_prbs_err_count()))

    time.sleep(0.01)

    print("Force errors")
    for i in range(4):
        n[3][i].tx_prbs_force_error()

    time.sleep(0.01)

    for i in range(4):
        print("CH %d locked: %d  errors: %d  error count: %d" % (i,
            n[3][i].is_rx_prbs_locked(),
            n[3][i].is_rx_prbs_error(),
            n[3][i].get_rx_prbs_err_count()))


def node_string(node):
    s = ''
    if len(node.path) > 0: s += '[%s] ' % '.'.join(str(x) for x in node.path)
    s += type(node).__name__
    s += ' [%s]' % node.name
    if len(node.ext_str) > 0:
        s += ' [%s]' % node.ext_str
    return s

def format_tree(node):
    s = node_string(node)
    lst = [s]
    for ni in range(len(node)):
        lst2 = format_tree(node[ni])
        for i in range(len(lst2)):
            if i == 0:
                lst.append(' |__'+lst2[i])
            else:
                if ni == len(node)-1:
                    lst.append('    '+lst2[i])
                else:
                    lst.append(' |  '+lst2[i])
    return lst

if __name__ == "__main__":
    main()

