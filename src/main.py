from prometheus_client import start_http_server
from os import getenv
from bpfBuddy import bpfBuddy
from pwHelpers import getSelfIPs, ipHRTo32, outputColumns
import logging
from sys import stdout

#constants
PORTSCAN_TIME_THRESHOLD = int(getenv('PW_PORTSCAN_TIME_THRESHOLD', 60))
PORTSCAN_PORT_THRESHOLD = int(getenv('PW_PORTSCAN_PORT_THRESHOLD', 3)) #Hit PORTSCAN_PORT_THRESHOLD ports within PORTSCAN_TIME_THRESHOLD and you're now a scanner
PROMETHEUS_PORT         = int(getenv('PW_PROMETHEUS_PORT', 9090))
IFDEV                   = getenv('PW_IFDEV', "lo")
WHITELIST_SELF          = getenv('PW_WHITELIST_SELF', 'True').lower() in ('true', '1') #sneaky trick, yes?

#log setup
logging.basicConfig(stream = stdout, level=logging.INFO, format="%(message)s") #doesn't get simpler than this

#prometheus setup
start_http_server(PROMETHEUS_PORT)

#instantiate bpf interface
interface = bpfBuddy("bpf/packetwatch.c", PORTSCAN_PORT_THRESHOLD, PORTSCAN_TIME_THRESHOLD, IFDEV)

#Greet the user and put up pretty columns
logging.info("Welcome to Packetwatch!")
logging.info("We will be logging all incoming connections on %s" % IFDEV)
logging.info("Any source IPs that hit %s different ports within %s second(s) will have their future connection attempts dropped!" % (PORTSCAN_PORT_THRESHOLD, PORTSCAN_TIME_THRESHOLD))
whitelistInfo = False
if WHITELIST_SELF:
  whitelistInfo = ("", IFDEV, "!")
else:
  whitelistInfo = (" NOT", IFDEV, ", so play nice!")
logging.info("We will%s whitelist any incoming connections originating from our own IPs on %s%s" % whitelistInfo)
outputColumns("TIME", "IP", "PORT", "MESSAGE")

#whitelist ourselves!
if WHITELIST_SELF:
  for ip in getSelfIPs(IFDEV):
    interface.forceWhitelist(ipHRTo32(ip))

#And get to work!
interface.load()
interface.listen()
