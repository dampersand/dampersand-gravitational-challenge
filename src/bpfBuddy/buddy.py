from src.pwHelpers import *
from datetime import datetime
from bcc import BPF
from ctypes import c_uint32


#Class for loading OUR bpf code into xdp, then working with it.
#Note that this is not great programming... this class can ONLY work with our bpf code, it's not super modular.
class bpfBuddy:
  def __init__(self, sourceFile, portThresh, timeThresh, ifdev):
    self.callers    = {}
    self.blacklist  = []
    self.whitelist  = []
    self.bpf        = BPF(src_file = sourceFile)
    self.portThresh = portThresh
    self.timeThresh = timeThresh
    self.ifdev      = ifdev


  #Loads bpf into an interface via xdp
  def load(self):
    self.bpf.attach_xdp(self.ifdev, self.bpf.load_func("packetwatch", BPF.XDP))

  #expects to receive raw data from the bpf code.
  #returns a 'callerData' dict
  #NOTE: this implementation of callerData is bad!  It requires knowledge of just what bpf code is happening!  It would be better to have a sort of 'plugin' that could be loaded.  The plugin would load the bpf AND parse the data according to the bpf's retVal struct!
  def parseCallerData(self, data):
    #The timestamp may have some drift from when we actually received it.  Depends how long it takes the bpf code to process it.
    rawTime = datetime.now()
    hrTime = rawTime.strftime("%H:%M:%S")
    port = port16ToHR(data.destPort)
    hrIp = ip32ToHR(data.sourceIP)

    #return all info in a nicely packaged dict
    #I'm going to call this a 'callerData'.  I could probably explicitly set it by making it a prototype dict, but I'm only so bored.
    callerData = {
      "time"  : rawTime,
      "hrTime": hrTime,
      "ip"    : data.sourceIP,
      "hrIp"  : hrIp,
      "port"  : port
    }
    return callerData

  #records a caller into our caller dict
  def recordCaller(self, caller):
    if caller["ip"] not in callers:
      self.callers[caller["ip"]] = [{"time": caller["time"], "port": caller["port"]}]

    else:
      self.callers[caller["ip"]].append({"time": caller["time"], "port": caller["port"]})

  #cleans up the caller list - removes any call records older than timeThresh, detects and deletes scanners.
  #returns a list of the scanners found.
  def cleanCallers(self):
    now = datetime.now()
    newScanners = []
    for ip in self.callers:
      portsHit = [] #ports that a caller has hit in the last minute
      removeElements = [] #old call records to be removed

      #Check each of a caller's calls, see if they've been a bit scan-happy
      for i, call in enumerate(self.callers[ip]):
        if (now - call["time"]).seconds > self.timeThresh:
          removeElements.append(i)
        else:
          portsHit.append(call["port"])

      if len(set(portsHit)) >= self.portThresh: #scanner detected #TODO: don't flag our own IPs as scanners
        self.blacklist.append(ip)
        self.blacklist = list(set(self.blacklist))
        newScanners.append(ip)

      else: #not a scanner, remove old call records from largest index to smallest
        removeElements.sort(reverse=True)
        for i in removeElements:
          self.callers[ip].pop(i)

    #If someone has entered the blacklist, stop storing their data
    for ip in newScanners:
      self.callers.pop(ip, False)

    return newScanners

  #blacklists an ip
  #expects to receive an ip32
  def blacklist(self, ip):
    print("DEBUG tattling on %s" % ip32ToHR(ip) )
    try:
      self.bpf["blacklist"][c_uint32(ip)] = c_uint32(1)
    except:
      print("Tried, but could not blacklist IP: %s" % ip32ToHR(ip))

  #whitelists an IP
  #expects to receive an ip32
  def whitelist(self, ip):
    print("DEBUG tattling on %s" % ip32ToHR(ip) )
    try:
      self.bpf["blacklist"][c_uint32(ip)] = c_uint32(1)
    except:
      print("Tried, but could not whitelist IP: %s" % ip32ToHR(ip))

  def process(self, cpu, xdpData, size):
    #get data from XDP layer and tick the prometheus counter
    data = self.bpf["callers"].event(xdpData)
    #connCount.inc() #TODO this is in a weird place now

    #parse and output data
    callerData = self.parseCallerData(data)
    #outputHelper(callerData) #TODO gotta hook this in now

    #record callers and drop anything older than 1 min, get any new scanners
    self.recordCaller(callerData)
    newScanners = self.cleanCallers()

    #blacklist all the scanners
    for scanner in newScanners:
      self.blacklist(scanner)

  #This function blocks.  Start polling our xdp interface for new packets or whatever
  #Call the process function on each new packet
  def listen(self):
    try: #if we fail, remove from xdp cuz like be safe okay
      self.bpf["callers"].open_perf_buffer(self.process)
      while True:
        self.bpf.perf_buffer_poll()

    except:
      self.bpf.remove_xdp(self.ifdev)
      