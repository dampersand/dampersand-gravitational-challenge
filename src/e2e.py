import logging
from sys import stdout
from test import *
from os import getenv
from sys import stdout
from time import sleep

#detect test type and set up logs
WHITELIST = getenv('PW_WHITELIST_SELF', 'False').lower() in ('true', '1') #defaults to non-whitelist testing
logging.basicConfig(stream = stdout, level=logging.INFO, format="%(message)s")

#Intro
logging.info("Packetwatch E2E testing suite")
logging.info("We will perform a series of tests against packetwatch over the local ifdev.")
logging.info("Please be sure no extraneous tcp traffic is flowing over the local ifdev during this time, as that is likely to interfere with the test.")

if WHITELIST:
  logging.info("Performing e2e testing assuming our IP is whitelisted")
else:
  logging.info("Performing e2e testing assuming our IP is not whitelisted")

try:
  #Set up environment
  logging.info("Building nginx server for packetwatch to protect...")
  startNginx()

  logging.info("Waiting 5 seconds for race condition purposes") #race condition: soooooo it's possible that packetwatch isn't up yet.  But at this point I just want quick and dirty tests, so I ain't gonna check.
  sleep(5)

  #######
  #both-list tests go here
  #######
  logging.info("Checking to make sure nginx is up")
  logging.info("Assumptions: None")
  logging.info("Expected Behavior: nginx should return 200 and 'pong'")
  if canReachHttp(8086, "pong"):
    logging.info("SUCCESS")
  else:
    logging.info("FAIL")
  logging.info("")


  logging.info("Performing a slow portscan, then testing result.")  
  logging.info("Assumptions: PW_PORTSCAN_TIME_THRESHOLD is < 1s, or that whitelisting is on.")
  logging.info("Expected Behavior: packetwatch should not blacklist this traffic, nginx should return 200 and 'pong'")
  portScan(3, 1.5)
  if canReachHttp(8086, "pong"):
    logging.info("SUCCESS")
  else:
    logging.info("FAIL")
  logging.info("")


  logging.info("Performing hammer test (multiple connections in quick succession on a single port)")
  logging.info("Assumptions: PW_PORTSCAN_PORT_THRESHOLD is < 3")
  logging.info("Expected Behavior: packetwatch should not blacklist this traffic, nginx should return 200 and 'pong'")
  for i in range(3): #hit this thing four times
    canReachHttp(8086, "pong")
  if canReachHttp(8086, "pong"):
    logging.info("SUCCESS")
  else:
    logging.info("FAIL")
  logging.info("")


  #######
  #divergent tests
  #######

  #Preamble, different for each test
  if not WHITELIST:
    logging.info("Sleeping for a second so we don't accidentally irritate packetwatch") #this is kludgy.  It assumes our test has PW_PORTSCAN_TIME_THRESHOLD < 1, and prevents us from getting blacklisted by running the next test too soon after the above test.
    sleep(2)
    logging.info("Performing fast portscan, then testing result.")
    logging.info("Assumptions: PW_PORTSCAN_TIME_THRESHOLD is < 1s and PW_PORTSCAN_PORT_THRESHOLD is == 3 and we are not whitelisted")
    logging.info("Expected Behavior: packetwatch should allow the first 3 scans, and then block subsequent connection attempts, resulting in exception")
  else:
    logging.info("Performing fast portscan, then testing result.")
    logging.info("Assumptions: our IP address is whitelisted")
    logging.info("Expected Behavior: packetwatch should allow all of this traffic.")

  #Portscan, same for each test
  try:
    portScan(3)
  except e:
    logging.warning("WARNING - unexpected %s type exception caught on portScan.  Test inconclusive, please exec in and debug" % type(e).__name__ )


  #Check results for non-whitelist response
  if not WHITELIST:
    try:
      if canReachHttp(8086, "pong"):
        logging.info("FAIL - could reach nginx")
      else:
        logging.warning("WARNING - expected an exception here, but attempting to reach to nginx did not throw one.  However, nginx did not respond correctly.  Something is likely wrong.")
    except:
      logging.info("SUCCESS")

  #Check results for whitelist response
  else:
    if canReachHttp(8086, "pong"):
      logging.info("SUCCESS")
    else:
      logging.info("FAIL")


      
except e:
  logging.error("Unhandled exception of type %s.  Recommend execing into pod to debug." % type(e).__name__ )

logging.info("Thus ends our tests.  Press CTRL+C to exit.")
