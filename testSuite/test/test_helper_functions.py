import unittest
from pwHelpers import *


#These tests will be automatically run by green, in parallel.
class TestHelpers(unittest.TestCase):

  def test_ip32ToHR_answer(self):
    "ip32ToHR on localhost 32 byte network-order (16777343) should return 127.0.0.1 string"
    self.assertEqual(ip32ToHR(16777343), "127.0.0.1")

  def test_ip32ToHR_malformed(self):
    "ip32ToHR on malformed non-IP address should raise exception"
    try:
      ip32ToHR(1677734) #this should raise an exception
      self.assertTrue(False)
    except:
      self.assertTrue(True)


  def test_ipHRTo32_answer(self):
    "ipHRTo32 on 127.0.0.1 should return localhost 32 byte network-order 16777343"
    self.assertEqual(ipHRTo32("127.0.0.1"), 16777343)

  def test_ipHRTo32_malformed(self):
    "ipHRTo32 on malformed non-IP address should raise exception"
    try:
      ipHRTo32("127.0.0.") #this should raise an exception
      self.assertTrue(False)
    except:
      self.assertTrue(True)


  def test_port16ToHR_answer(self):
    "port16ToHR on 16 byte port network-order 20480 should return port 80"
    self.assertEqual(port16ToHR(20480), 80)

  def test_port16ToHR_malformed(self):
    "port16ToHR on malformed non-port should raise exception"
    try:
      port16ToHR(20481) #this should raise an exception
      self.assertTrue(False)
    except:
      self.assertTrue(True)


  def test_getSelfIPs_answer(self):
    "getSelfIPs should find 127.0.0.1 when searching localhost ifdev"
    self.assertTrue("127.0.0.1" in getSelfIPs("lo"))


  #This is not a great test.  All we do is make sure there's no exception.  Since we're being lazy with our logging and using 'print', there's no easy assert.
  def test_outputColumns_nobreak(self):
    "Test that outputColumns doesn't throw exception"
    try:
      outputColumns("1", "2", "3", "4") #this should not raise an exception
      self.assertTrue(True)
    except:
      self.assertTrue(False)
