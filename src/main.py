#!/bin/env python3
#TODO ^get rid of that and put it in the dockerfile instead

from bcc import BPF
import socket
import struct
from datetime import datetime

#build the necessary BPF.
program = """
//TODO: these includes are dependent on the host machine and one of the volume mounts.  They're pretty fragile.
#include <uapi/linux/bpf.h>
#include <uapi/linux/if_ether.h>
#include <uapi/linux/ip.h>
#include <uapi/linux/tcp.h>
#include <uapi/linux/in.h>

BPF_PERF_OUTPUT(packets); //outputs incoming packets
BPF_HASH(sHitList);       //an array is better, but I'm not going to sit here and re-implement python's "in" operator in C.
BPF_QUEUE(sHitListQ, __be32, 10240);     //receives new candidate IPs for the sHitList from userspace

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

  //assembleuseful info, but don't worry about human-readability yet
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

ifdev = "lo" #global device to listen on #TODO pass device
callers = {} #list of folks who have called the network stack
sHitList = [] #scanner hit list, list of source IPs caught port-scanning
b = BPF(text=program) #TODO consider importing from  a file instead
b.attach_xdp(ifdev, b.load_func("packetWork", BPF.XDP)) #get to work


#Spit out the output in a human readable format
def outputWatchLine(data):
  print("%-18.9s %-16s %-6s" % (data["hrTime"], data["hrIp"], data["port"]))


#parses data straight from xdp, spits out a callerData construct
def parseCallerData(packet):
  #Get timestamp early, minimize drift from actual packet arrival, store as both datetime and human-readable
  rawTime = datetime.now()
  hrTime = rawTime.strftime("%H:%M:%S")

  #port comes in network byte order, make it human-readable
  port = socket.ntohs(packet.destPort)

  #IP address comes in network byte order too, but it's 32 bit not 16 bit
  #Also we need to add all the dot notation
  ip32 = socket.ntohl(packet.sourceIP)
  ipBytes = struct.pack('!I', ip32)
  hrIp = socket.inet_ntoa(ipBytes)

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
  callersToDelete = []
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
      callersToDelete.append(ip)

    else: #not a scanner, remove old call records from largest index to smallest
      removeElements.sort(reverse=True)
      for i in removeElements:
        callers[ip].pop(i)

  #If someone has entered the sHitList, stop storing their data
  for ip in callersToDelete:
    callers.pop(ip, False)


def processPacket(cpu, xdpData, size):
  #get data from XDP layer
  data = b["packets"].event(xdpData)

  #parse and output data
  callerData = parseCallerData(data)
  outputWatchLine(callerData)

  #record callers and drop anything older than 1 min
  recordCaller(callerData)
  inspectCallers()


print("%-18s %-16s %-6s" % ("TIME", "IP", "PORT"))
try: #if we fail, remove from xdp cuz like be safe okay
  b["packets"].open_perf_buffer(processPacket)
  while True:
    b.perf_buffer_poll()

except:
  b.remove_xdp(ifdev)