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

BPF_PERF_OUTPUT(packets);

struct connInfo {
  int destPort;
  int sourceIP;
};

int getPacket(struct xdp_md *ctx) {
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

  //spit out useful info, but don't worry about human-readability yet
  struct connInfo retVal = {};
  retVal.destPort = tcp->dest;
  retVal.sourceIP = ip->saddr;

  //great, now let's do something for real
  packets.perf_submit(ctx, &retVal, sizeof(retVal));
  return XDP_PASS;
}

"""

ifdev = "lo" #TODO pass device
b = BPF(text=program) #TODO consider importing from  a file instead
b.attach_xdp(ifdev, b.load_func("getPacket", BPF.XDP)) #get to work


#Take all the output from XDP and make it human readable
def outputWatchLine(cpu, data, size):
  #get the packet
  packet = b["packets"].event(data)

  #port comes in network byte order, make it human-readable
  port = socket.ntohs(packet.destPort)

  #IP address comes in network byte order too, but it's 32 bit not 16 bit
  #Also we need to add all the dot notation
  ip32 = socket.ntohl(packet.sourceIP)
  ipBytes = struct.pack('!I', ip32)
  readableIP = socket.inet_ntoa(ipBytes)

  #Get timestamp
  time = datetime.now().strftime("%H:%M:%S")
  print("%-18.9s %-16s %-6s" % (time, readableIP, port))




print("%-18s %-16s %-6s" % ("TIME", "IP", "PORT"))
try: #if we fail, remove from xdp cuz like be safe okay
  b["packets"].open_perf_buffer(outputWatchLine)
  while True:
    b.perf_buffer_poll()

except:
  b.remove_xdp(ifdev)