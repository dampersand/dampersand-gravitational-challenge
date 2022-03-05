from prometheus_client import start_http_server
from os import getenv
from bpfBuddy import bpfBuddy
from pwHelpers import getSelfIPs, ipHRTo32, outputColumns
import logging
from sys import stdout

#######
#SETUP
#######

#constants
#Not using os.getenv's default setting because that doesn't detect empty strings.  Booooooooooo.
ENV = {
  "PORTSCAN_TIME_THRESHOLD" : getenv('PW_PORTSCAN_TIME_THRESHOLD'),
  "PORTSCAN_PORT_THRESHOLD" : getenv('PW_PORTSCAN_PORT_THRESHOLD'), #Hit PORTSCAN_PORT_THRESHOLD ports within PORTSCAN_TIME_THRESHOLD and you're now a scanner
  "PROMETHEUS_PORT"         : getenv('PW_PROMETHEUS_PORT'),
  "IFDEV"                   : getenv('PW_IFDEV'),
  "WHITELIST_SELF"          : getenv('PW_WHITELIST_SELF')
}

ENVDEFAULT = {
  "PORTSCAN_TIME_THRESHOLD" : 60,
  "PORTSCAN_PORT_THRESHOLD" : 3,
  "PROMETHEUS_PORT"         : 9090,
  "IFDEV"                   : "lo",
  "WHITELIST_SELF"          : True
}

#Python's treatment of environment variables is trash.  Because '' is "falsey" but not falsey enough to count as "None",
#we can't use os.getenv's 'default' argument, so we gotta set our default values and types manually
for key in ENV:
  if ENV[key] == '':
    ENV[key] = ENVDEFAULT[key]

#Booleans are special cases.  We need to cast them from strings regardless.
if type(ENV['WHITELIST_SELF']) != bool:
  ENV['WHITELIST_SELF'] = ENV['WHITELIST_SELF'].lower() in ('true', '1') #sneaky trick, yes?

#Now typecast everything.
for key in ENV:
  type(ENVDEFAULT[key])(ENV[key])



#log setup
logging.basicConfig(stream = stdout, level=logging.INFO, format="%(message)s") #doesn't get simpler than this

#prometheus setup
start_http_server(ENV["PROMETHEUS_PORT"])

#instantiate bpf interface
interface = bpfBuddy("bpf/packetwatch.c", ENV["PORTSCAN_PORT_THRESHOLD"], ENV["PORTSCAN_TIME_THRESHOLD"], ENV["IFDEV"])


#######
#START
#######

#Greet the user and put up pretty columns
logging.info("Welcome to Packetwatch!")
logging.info("We will be logging all incoming connections on %s" % ENV["IFDEV"])
logging.info("Any source IPs that hit %s different ports within %s second(s) will have their future connection attempts dropped!" % (ENV["PORTSCAN_PORT_THRESHOLD"], ENV["PORTSCAN_TIME_THRESHOLD"]))
whitelistInfo = False
if ENV["WHITELIST_SELF"]:
  whitelistInfo = ("", ENV["IFDEV"], "!")
else:
  whitelistInfo = (" NOT", ENV["IFDEV"], ", so play nice!")
logging.info("We will%s whitelist any incoming connections originating from our own IPs on %s%s" % whitelistInfo)
outputColumns("TIME", "IP", "PORT", "MESSAGE")

#whitelist ourselves!
if ENV["WHITELIST_SELF"]:
  for ip in getSelfIPs(ENV["IFDEV"]):
    interface.forceWhitelist(ipHRTo32(ip))

#And get to work!
interface.load()
try:
  interface.listen()
except:
  print("Thank you for playing Wing Commander!")
