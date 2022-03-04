"""
ip-based helpers for packetwatch
"""

import struct
import socket
from netifaces import ifaddresses, AF_INET

#Converts a raw ip32 into a human readable IP
#I define an "ip32" as a 32 byte ip address (ie ipv4) in network-byte order.
def ip32ToHR(ip32):
  ip32HostOrder = socket.ntohl(ip32)
  ipBytes = struct.pack('!I', ip32HostOrder)
  return socket.inet_ntoa(ipBytes)

#Converts a human readable IP into raw ip32
#I define an "ip32" as a 32 byte ip address (ie ipv4) in network-byte order.
def ipHRTo32(ip):
  ipBytes = socket.inet_aton(ip)
  ip32HostOrder = struct.unpack('!I', ipBytes)[0]
  return socket.htonl(ip32HostOrder) 

#Converts a raw port16 into a human readable IP
#Guess what I define a port16 as.
def port16ToHR(port16):
  return socket.ntohs(port16)

#Get all the ipv4s attached to a hardware device
def getSelfIPs(ifdev):
  addresses = []
  for entry in ifaddresses(ifdev)[AF_INET]:
    addresses.append(entry["addr"])

  return addresses