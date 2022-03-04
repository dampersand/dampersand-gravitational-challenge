import unittest
from pwHelpers import *

class TestHelpers(unittest.TestCase):

  def test_ip32ToHR_answer(self):
    "ip32ToHR on localhost 32 byte network-order should return localhost string"
    self.assertEqual(ip32ToHR(16777343), "127.0.0.1")

  def test_ip32ToHR_malformed(self):
    "ip32ToHR on malformed non-IP address should raise exception"
    self.assertRaises(ip32ToHR(1677734))

  def test_ipHRTo32_answer(self):
    "ipHRTo32 on localhost string should return localhost 32 byte network-order"
    self.assertEqual(ip32ToHR("127.0.0.1"), 16777343)

