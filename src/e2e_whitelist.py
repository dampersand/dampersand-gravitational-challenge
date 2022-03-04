import subprocess
from time import sleep
import unittest
import requests
import logging
from sys import stdout

class e2eTests(unittest.TestCase):

  #tests that local nginx server is up on the tester image and returns pong
  def test_nginx_up(self):
    r = requests.get("http://localhost:8086")
    self.assertEqual(r.status_code, 200)
    self.assertEqual(r.text, "pong")

  #tests that we are protected by packetwatch whitelisting
  def test_packetwatch_deny(self):
    requests.get("http://localhost:8086", timeout=1)
    requests.get("http://localhost:8087", timeout=1)
    requests.get("http://localhost:8088", timeout=1)
    try:
      r = requests.get("http://localhost:8086", timeout=4)
      self.assertEqual(r.status_code, 200)
      self.assertEqual(r.text, "pong")
    except:
      self.assertTrue(False)

logging.basicConfig(stream = stdout, level=logging.INFO, format="%(message)s")

#turn nginx on.  Yes, it is a race condition, I know, I know.
logging.info("Building nginx server for packetwatch to protect")
logging.info("Make sure no traffic is coming over localhost during these tests, or it will interfere with packetwatch's port scanning!")
subprocess.call('service nginx start', shell=True)
sleep(5)

tester=e2eTests()

try:
  logging.info("Checking to make sure nginx is up!")
  tester.test_nginx_up()
  logging.info("SUCCESS")
except AssertionError:
  logging.info("FAIL nginx is not up!  This will skew future tests.")

try:
  logging.info("Performing packetwatch filter test.  Packetwatch whitelisting should prevent this from thinking I'm a scanner.")
  tester.test_packetwatch_deny()
  logging.info("SUCCESS")
except AssertionError:
  logging.info("FAIL We couldn't reach nginx.  Is it down, or is whitelisting not working correctly?")

logging.info("Thus ends our tests.  Press CTRL+C to exit.")
