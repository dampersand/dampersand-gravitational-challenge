import unittest
import requests
import subprocess
import logging
from time import sleep

#This will NOT be automatically run by green.  These are helper functions for e2e tests.
#note that the ports for nginx are hardcoded, and the helper functions assume you're using the built-in e2e tests.
#This means they're probably not suitable for use elsewhere.

def startNginx():
  logging.info("Starting nginx server on ports 8086, 8087, 8088")
  subprocess.call('service nginx start', shell=True)

def httpResponse(port, **kwargs):
  return requests.get("http://localhost:%s" % port, kwargs)

#tries to hit a local port using http.  Return true if the port is available and if optional expected text matches
def canReachHttp(port, text = False):
  r = httpResponse(port)
  if r.status_code == 200 and ((r.text == text) or (not text)):
    return True
  else:
    return False

#Scan numPorts ports with optional sleep time between them
#hardcode: start at port 8086 where we know nginx is listening
def portScan(numPorts, sleepTime=0):
  for i in range(numPorts - 1): #subtract 1 because range starts at 0
    try:
      httpResponse(8086 + i, timeout=1)
    except:
      pass #drop exceptions.  We expect exceptions, because requests raises them on timeouts/drops/whatever.
    sleep(sleepTime)
