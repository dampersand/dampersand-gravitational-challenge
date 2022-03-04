
#Spit out a human readable output line
def outputHelper(data):
  print("%-18.9s %-16s %-6s" % (data["hrTime"], data["hrIp"], data["port"]))