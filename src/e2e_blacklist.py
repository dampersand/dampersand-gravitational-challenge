import subprocess
from time import sleep
import unittest
import requests

class e2eTests(unittest.TestCase):

  #tests that local nginx server is up on the tester image and returns pong
  def test_nginx_up(self):
    r = requests.get("http://localhost:8086")
    self.assertEqual(r.status_code, 200)
    self.assertEqual(r.text, "pong")

  #tests that packetwatch doesn't stop a slow portscan
  def test_slow_portscan(self):
    requests.get("http://localhost:8086", timeout=1)
    sleep(1.5)
    requests.get("http://localhost:8087", timeout=1)
    sleep(1.5)
    requests.get("http://localhost:8088", timeout=1)
    sleep(1.5)
    r = requests.get("http://localhost:8086", timeout=1)
    self.assertEqual(r.status_code, 200)
    self.assertEqual(r.text, "pong")

  #tests that packetwatch doesn't stop someone from hammering a single port even if it's faster than the threshold
  def test_packetwatch_singleport_allow(self):
    requests.get("http://localhost:8086", timeout=1)
    requests.get("http://localhost:8086", timeout=1)
    requests.get("http://localhost:8086", timeout=1)
    r = requests.get("http://localhost:8086", timeout=1)
    self.assertEqual(r.status_code, 200)
    self.assertEqual(r.text, "pong")

  #tests that packetwatch correctly stops a portscan
  def test_packetwatch_deny(self):
    "packetwatch should stop a portscan"
    requests.get("http://localhost:8086", timeout=1)
    requests.get("http://localhost:8087", timeout=1)
    requests.get("http://localhost:8088", timeout=1)
    try:
      r = requests.get("http://localhost:8086", timeout=4)
      self.assertTrue(False)
    except requests.exceptions.Timeout:
      self.assertTrue(True)



#turn nginx on.  Yes, it is a race condition, I know, I know.
print("Building nginx server for packetwatch to protect")
print("Make sure no traffic is coming over localhost during these tests, or it will interfere with packetwatch's port scanning!")
subprocess.call('service nginx start', shell=True)
sleep(5)

tester=e2eTests()

try:
  print("Checking to make sure nginx is up!")
  tester.test_nginx_up()
  print("Success!")
except AssertionError:
  print("nginx is not up!  This will skew future tests.")

try:
  print("Performing a slow portscan, packetwatch should allow this.  Be sure PW_PORTSCAN_TIME_THRESHOLD is 1 second or less.")
  tester.test_slow_portscan()
  print("Success!")
except AssertionError:
  print("Couldn't reach nginx server!  It may be down, or packetwatch may not be expiring calls correctly.")

try:
  print("Performing hammer test, faster than packetwatch's threshold but with fewer ports than PW_PORTSCAN_PORT_THRESHOLD.")
  tester.test_packetwatch_singleport_allow()
  print("Success!")
except AssertionError:
  print("Couldn't reach nginx server!  It may be down, or packetwatch may not be honoring port thresholds correctly.")

try:
  print("Performing packetwatch filter test.  Packetwatch should flag me as a portscanner and prevent nginx access.")
  tester.test_packetwatch_deny()
  print("Success, I'm blocked!!")
except AssertionError:
  print("Was able to reach nginx server!  That's bad, we should have been blocked.  is packetwatch running?")

print("Thus ends our tests.  Restart packetwatch to try again.")
