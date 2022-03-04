//NOTE: the location of these includes are dependent on the host machine and one of the volume mounts.  They're pretty fragile.
#include <uapi/linux/bpf.h>
#include <uapi/linux/if_ether.h>
#include <uapi/linux/ip.h>
#include <uapi/linux/tcp.h>
#include <uapi/linux/in.h>

BPF_PERF_OUTPUT(callers);   //outputs caller information
BPF_HASH(blacklist, __be32); //an array is better, but I'm not going to sit here and re-implement python's "in" operator in C.
BPF_HASH(whitelist, __be32); //a hash of IPs that should always be allowed through

struct connInfo {
  int destPort;
  int sourceIP;
};

int packetwatch(struct xdp_md *ctx) {
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

  //if this guy's on the black list, drop his conn.
  //but if the caller is on our whitelist, continue.
  int key = ip->saddr;
  u64 *ipBanned = blacklist.lookup(&key);
  u64 *ipSafe = whitelist.lookup(&key);
  if (ipBanned && !ipSafe) {
    return XDP_DROP;
  }

  //assemble useful info, but don't worry about human-readability yet
  struct connInfo retVal = {};
  retVal.destPort = tcp->dest;
  retVal.sourceIP = ip->saddr;

  //send it home
  callers.perf_submit(ctx, &retVal, sizeof(retVal));
  return XDP_PASS;
}
