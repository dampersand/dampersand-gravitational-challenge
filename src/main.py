from prometheus_client import start_http_server
from os import getenv
from bpfBuddy import bpfBuddy
from pwHelpers import getSelfIPs, ipHRTo32, outputColumns

#constants
PORTSCAN_TIME_THRESHOLD = getenv('PW_PORTSCAN_TIME_THRESHOLD', 60) 
PORTSCAN_PORT_THRESHOLD = getenv('PW_PORTSCAN_PORT_THRESHOLD', 3) #Hit PORTSCAN_PORT_THRESHOLD ports within PORTSCAN_TIME_THRESHOLD and you're now a scanner
PROMETHEUS_PORT         = getenv('PW_PROMETHEUS_PORT', 9090)
IFDEV                   = getenv('PW_IFDEV', "lo")
WHITELIST_SELF          = getenv('PW_WHITELIST_SELF', 'True').lower() in ('true', '1') #sneaky trick, yes?

#prometheus setup
start_http_server(PROMETHEUS_PORT)

#instantiate bpf interface
interface = bpfBuddy("bpf/packetwatch.c", PORTSCAN_PORT_THRESHOLD, PORTSCAN_TIME_THRESHOLD, IFDEV)

#Put up some pretty columns
outputColumns("TIME", "IP", "PORT", "MESSAGE")

#whitelist ourselves!
if WHITELIST_SELF:
  for ip in getSelfIPs(IFDEV):
    interface.forceWhitelist(ipHRTo32(ip))

#And get to work!
interface.load()
interface.listen()
