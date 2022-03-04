import unittest
import requests
from time import sleep

class TestE2E(unittest.TestCase):

  def race_condition(self):
    "look, i'm lazy.  I have no idea if packetwatch is going to come up and be live before tester, so let's just give it 5s"
    sleep(5)
    self.assertTrue(True)

  def test_nginx_up(self):
    "local nginx server is up on the tester image and should return 'pong'"
    r = requests.get("http://localhost:8086")
    self.assertEqual(r.status_code, 200)
    self.assertEqual(r.text, "pong")

  def test_packetwatch_allow(self):
    "packetwatch should not stop a slow portscan (tweak portscan settings before beginning test)"
    requests.get("http://localhost:8086", timeout=1)
    sleep(1.5)
    requests.get("http://localhost:8087", timeout=1)
    sleep(1.5)
    requests.get("http://localhost:8088", timeout=1)
    sleep(1.5)
    r = requests.get("http://localhost:8086", timeout=1)
    self.assertEqual(r.status_code, 200)
    self.assertEqual(r.text, "pong")

  def test_packetwatch_singleport_allow(self):
    "packetwatch should not stop someone hammering a single port"
    requests.get("http://localhost:8086", timeout=1)
    requests.get("http://localhost:8086", timeout=1)
    requests.get("http://localhost:8086", timeout=1)
    r = requests.get("http://localhost:8086", timeout=1)
    self.assertEqual(r.status_code, 200)
    self.assertEqual(r.text, "pong")

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
