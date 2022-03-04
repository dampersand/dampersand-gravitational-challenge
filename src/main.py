#!/bin/env python3
#TODO ^get rid of that and put it in the dockerfile instead

from bcc import BPF
import socket
import struct
from datetime import datetime
from ctypes import c_uint32
from netifaces import ifaddresses, AF_INET
from prometheus_client import start_http_server, Counter

#build the necessary BPF.
program = """
//TODO: these includes are dependent on the host machine and one of the volume mounts.  They're pretty fragile.
#include <uapi/linux/bpf.h>
#include <uapi/linux/if_ether.h>
#include <uapi/linux/ip.h>
#include <uapi/linux/tcp.h>
#include <uapi/linux/in.h>

BPF_PERF_OUTPUT(packets);   //outputs processed packets
BPF_HASH(sHitList, __be32); //an array is better, but I'm not going to sit here and re-implement python's "in" operator in C.
BPF_HASH(safeList, __be32); //a hash of IPs that should always be allowed through

struct connInfo {
  int destPort;
  int sourceIP;
};

int packetWork(struct xdp_md *ctx) {
  //NOTE: xdp_md is a struct OF MEMORY ADDRESSES, NOT OF THE ACTUAL DATA.  Remember this when you're tearing your hair out.
  //data      = the memory address that starts the xdp data
  //data_end  = the memory address at the end of the edp data

  //cast raw xdp data data and data_end into void pointers so we can make assumptions about them
  void *data = (void *)(long)ctx->data;
  void *data_end = (void *)(long)ctx->data_end;

  //let's assume the XDP came in as ethhdr (ie L2) data.  Test the assumption (rudimentary, just by size) and back off if we're wrong.
  struct ethhdr *frame = data;
  if ((void*)frame + sizeof(*frame) > data_end){
    return XDP_PASS;
  }

  //okay now let's see if it's ipv4 data.  Test and back off if we're wrong.
  struct iphdr *ip = data + sizeof(*frame);
  if ((void*)ip + sizeof(*ip) > data_end) {
    return XDP_PASS;
  }

  //if it's ipv4 data and this guy's on the sHitList, drop his packets.
  //but if the caller is on our safelist, continue.
  int key = ip->saddr;
  u64 *ipBanned = sHitList.lookup(&key);
  u64 *ipSafe = safeList.lookup(&key);
  if (ipBanned && !ipSafe) {
    return XDP_DROP;
  }

  //for now, let's scope down into TCP only.
  if (ip->protocol != IPPROTO_TCP) {
    return XDP_PASS;
  }

  //size check the tcp header now
  struct tcphdr *tcp = (void*)ip + sizeof(*ip);
  if ((void*)tcp + sizeof(*tcp) > data_end) {
    return XDP_PASS;
  }

  //now we're in business!  We have some tcp data.  Let's ONLY continue on 'syn' (not syn-ack) packets.
  if (!(tcp->syn) || (tcp->ack)) {
    return XDP_PASS;
  }

  //assemble useful info, but don't worry about human-readability yet
  struct connInfo retVal = {};
  retVal.destPort = tcp->dest;
  retVal.sourceIP = ip->saddr;

  //send it home
  packets.perf_submit(ctx, &retVal, sizeof(retVal));
  return XDP_PASS;
}

"""

#Hit PORTSCAN_PORT_THRESHOLD ports within PORTSCAN_TIME_THRESHOLD and you're now a scanner
PORTSCAN_TIME_THRESHOLD = 60 #constant, threshold (in seconds) above which someone is considered port scanning
PORTSCAN_PORT_THRESHOLD = 3  #constant, threshold (in ports) above which someone is considered port scanning
PROMETHEUS_PORT         = 9090

ifdev = "lo" #global device to listen on #TODO pass device
callers = {} #list of folks who have called the network stack
sHitList = [] #scanner hit list, list of source IPs caught port-scanning
b = BPF(text=program) #TODO consider importing from  a file instead
b.attach_xdp(ifdev, b.load_func("packetWork", BPF.XDP)) #get to work
connCount = Counter('connCount', 'number of new connections')
start_http_server(PROMETHEUS_PORT)



#Spit out the output in a human readable format
def outputWatchLine(data):
  print("%-18.9s %-16s %-6s" % (data["hrTime"], data["hrIp"], data["port"]))

#Collects a human readable IP from a raw ip32
def parseIP(ip):
  #IP address comes in network byte order just like port, but it's 32 bit not 16 bit
  #Also we need to add all the dot notation
  ip32 = socket.ntohl(ip)
  ipBytes = struct.pack('!I', ip32)
  return socket.inet_ntoa(ipBytes)

#takes a human readable IP and changes it back to raw ip32 in network byte order
def unParseIP(ip):
  ipBytes = socket.inet_aton(ip)
  ip32 = struct.unpack('!I', ipBytes)[0]
  return socket.htonl(ip32) 


#parses data straight from xdp, spits out a callerData construct
def parseCallerData(packet):
  #Get timestamp early, minimize drift from actual packet arrival, store as both datetime and human-readable
  rawTime = datetime.now()
  hrTime = rawTime.strftime("%H:%M:%S")

  #port comes in network byte order, make it human-readable.  same with IP, but use our parseIP helper.
  port = socket.ntohs(packet.destPort)
  hrIp = parseIP(packet.sourceIP)

  #return all info in a nicely packaged dict
  retVal = {
    "time"  : rawTime,
    "hrTime": hrTime,
    "ip"    : packet.sourceIP,
    "hrIp"  : hrIp,
    "port"  : port
  }
  return retVal

#Records a new caller into the caller DB (dict)
def recordCaller(caller):
  if caller["ip"] not in callers:
    callers[caller["ip"]] = [{"time": caller["time"], "port": caller["port"]}]

  else:
    callers[caller["ip"]].append({"time": caller["time"], "port": caller["port"]})


#checks caller list for any scanners, blacklists them.
#Also cleans up the caller list by removing old call records or deleting scanners from the caller list
def inspectCallers():
  global sHitList
  now = datetime.now()
  newScanners = []
  for ip in callers:
    portsHit = [] #ports that a caller has hit in the last minute
    removeElements = [] #old call records to be removed

    #Check each of a caller's calls, see if they've been a bit scan-happy
    for i, call in enumerate(callers[ip]):
      if (now - call["time"]).seconds > 60:
        removeElements.append(i)
      else:
        portsHit.append(call["port"])

    if len(set(portsHit)) >= 3: #scanner detected #TODO: don't flag our own IPs as scanners
      sHitList.append(ip)
      sHitList = list(set(sHitList))
      newScanners.append(ip)

    else: #not a scanner, remove old call records from largest index to smallest
      removeElements.sort(reverse=True)
      for i in removeElements:
        callers[ip].pop(i)

  #If someone has entered the sHitList, stop storing their data
  for ip in newScanners:
    callers.pop(ip, False)

  return newScanners

#alerts XDP of a new set of scanners
def alertXDP(scanners):
  for scanner in scanners:
    print("DEBUG tattling on %s" % parseIP(scanner) )
    try:
      b["sHitList"][c_uint32(scanner)] = c_uint32(1)
    except: #TODO figure out which exception causes a problem here...
      print("Could not blacklist scanner!  Scanner IP: %s" % parseIP(scanner))

def processPacket(cpu, xdpData, size):
  #get data from XDP layer and tick the prometheus counter
  data = b["packets"].event(xdpData)
  connCount.inc()

  #parse and output data
  callerData = parseCallerData(data)
  outputWatchLine(callerData)

  #record callers and drop anything older than 1 min, get any new scanners
  recordCaller(callerData)
  newScanners = inspectCallers()

  #Tattle to XDP layer about scanners
  alertXDP(newScanners)

def getSelfIPs():
  addresses = []
  for entry in ifaddresses(ifdev)[AF_INET]:
    addresses.append(entry["addr"])

  return addresses

def safeList(hrIp):
  print("DEBUG blanket allowing %s" % hrIp)
  ip = unParseIP(hrIp)
  try:
    b["safeList"][c_uint32(ip)] = c_uint32(1)
  except:
    print("Could not safelist %s! Consider stopping the program in case your connection gets blacklisted!" % hrIp)


for ip in getSelfIPs():
  safeList(ip)

print("%-18s %-16s %-6s" % ("TIME", "IP", "PORT"))
try: #if we fail, remove from xdp cuz like be safe okay
  b["packets"].open_perf_buffer(processPacket)
  while True:
    b.perf_buffer_poll()

except:
  b.remove_xdp(ifdev)