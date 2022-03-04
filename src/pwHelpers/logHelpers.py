#Spit out a human readable output line
#Rudimentary, always the same col size. guess it's up to you to figure out if your data fits, cuz I ain't doin' any intelligent detection/truncation
def outputColumns(col1, col2, col3, col4):
  print("%-18s %-16s %-6s %-18s" % (col1, col2, col3, col4))
