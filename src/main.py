#!/bin/env python3
#TODO ^get rid of that and put it in the dockerfile instead

from bcc import BPF

#build the necessary BPF.
program = """
//TODO: these includes are dependent on the host machine and one of the volume mounts.  They're pretty fragile.
#include <uapi/linux/bpf.h>
#include <uapi/linux/if_ether.h>
#include <uapi/linux/ip.h>
#include <uapi/linux/tcp.h>
#include <uapi/linux/in.h>
#include <config/usb/ohci/little/endian.h>

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

  struct connInfo retVal = {};
  retVal.destPort = ntohs(tcp->dest); //you know the hardest dang part is figuring out what format these variables come in?
  retVal.sourceIP = 1

  //great, now let's do something for real
  packets.perf_submit(ctx, &retVal, sizeof(retVal));
  return XDP_PASS;
}

"""

ifdev = "lo" #TODO pass device
b = BPF(text=program) #TODO consider importing from  a file instead
b.attach_xdp(ifdev, b.load_func("getPacket", BPF.XDP)) #get to work



#parse the packets
def printPacket(cpu, data, size):
  packet = b["packets"].event(data)
  print(packet.destPort)
  print(packet.sourceIP)



try: #if we fail, remove from xdp cuz like be safe okay
  b["packets"].open_perf_buffer(printPacket)
  while True:
    b.perf_buffer_poll()

except:
  b.remove_xdp(ifdev)