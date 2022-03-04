from bcc import BPF
from datetime import datetime
from ctypes import c_uint32
from prometheus_client import start_http_server, Counter
from os import environ
from pwHelpers import *

#Hit PORTSCAN_PORT_THRESHOLD ports within PORTSCAN_TIME_THRESHOLD and you're now a scanner
PORTSCAN_TIME_THRESHOLD = 60 #constant, threshold (in seconds) above which someone is considered port scanning
PORTSCAN_PORT_THRESHOLD = 3  #constant, threshold (in ports) above which someone is considered port scanning

PROMETHEUS_PORT = 9090
IFDEV           = environ['PW_IFDEV']           
callers = {} #list of folks who have called the network stack
sHitList = [] #scanner hit list, list of source IPs caught port-scanning
b = BPF(src_file = "bpf/packetwatch.c") #TODO consider importing from  a file instead
b.attach_xdp(IFDEV, b.load_func("packetWork", BPF.XDP)) #get to work
connCount = Counter('conn_count', 'number of new connections')
start_http_server(PROMETHEUS_PORT)


#parses data straight from xdp, spits out a callerData construct
def parseCallerData(packet):
  #Get timestamp early, minimize drift from actual packet arrival, store as both datetime and human-readable
  rawTime = datetime.now()
  hrTime = rawTime.strftime("%H:%M:%S")
  port = port16ToHR(packet.destPort)
  hrIp = ip32ToHR(packet.sourceIP)

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
    print("DEBUG tattling on %s" % ip32ToHR(scanner) )
    try:
      b["sHitList"][c_uint32(scanner)] = c_uint32(1)
    except: #TODO figure out which exception causes a problem here...
      print("Could not blacklist scanner!  Scanner IP: %s" % ip32ToHR(scanner))

def processPacket(cpu, xdpData, size):
  #get data from XDP layer and tick the prometheus counter
  data = b["packets"].event(xdpData)
  connCount.inc()

  #parse and output data
  callerData = parseCallerData(data)
  outputHelper(callerData)

  #record callers and drop anything older than 1 min, get any new scanners
  recordCaller(callerData)
  newScanners = inspectCallers()

  #Tattle to XDP layer about scanners
  alertXDP(newScanners)

def safeList(hrIp):
  print("DEBUG blanket allowing %s" % hrIp)
  ip = ipHRTo32(hrIp)
  try:
    b["safeList"][c_uint32(ip)] = c_uint32(1)
  except:
    print("Could not safelist %s! Consider stopping the program in case your connection gets blacklisted!" % hrIp)


for ip in getSelfIPs(IFDEV):
  safeList(ip)

print("%-18s %-16s %-6s" % ("TIME", "IP", "PORT")) #TODO: print this using output helper
try: #if we fail, remove from xdp cuz like be safe okay
  b["packets"].open_perf_buffer(processPacket)
  while True:
    b.perf_buffer_poll()

except:
  b.remove_xdp(ifdev)