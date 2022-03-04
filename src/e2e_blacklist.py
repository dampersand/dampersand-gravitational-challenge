import subprocess

class e2eTests(unittest.TestCase):

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



#turn nginx on.  Yes, it is a race condition, I know, I know.
subprocess.call('service nginx start', shell=True)
sleep(5)

tester=e2eTests()
tester.test_nginx_up()
tester.test_packetwatch_allow()
tester.test_packetwatch_singleport_allow()
tester.test_packetwatch_deny()
