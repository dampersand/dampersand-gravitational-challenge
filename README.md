# dputnam-gravitational-challenge: Packetwatch

<!-- MarkdownTOC -->

- [Quick Start Guide](#quick-start-guide)
- [Synopsis](#synopsis)
- [Host Information](#host-information)
  - [Host Architecture Tested](#host-architecture-tested)
  - [Host Package Dependencies](#host-package-dependencies)
  - [Other Host Dependencies](#other-host-dependencies)
- [Features and Functionality](#features-and-functionality)
  - [Connection Monitoring](#connection-monitoring)
  - [New Connection Filtering](#new-connection-filtering)
  - [Whitelisting](#whitelisting)
  - [Prometheus](#prometheus)
- [Testing](#testing)
  - [Unit Tests](#unit-tests)
  - [End-to-End \(e2e\) Tests](#end-to-end-e2e-tests)
- [Usage](#usage)
  - [Arguments](#arguments)
  - [Actions \(make targets\)](#actions-make-targets)
  - [Examples](#examples)
    - [Monitor Localhost](#monitor-localhost)
    - [Monitor an external-facing interface but don't whitelist internal-originating traffic](#monitor-an-external-facing-interface-but-dont-whitelist-internal-originating-traffic)
    - [Change port scanning definition to "someone who scans 10 ports in 5 seconds"](#change-port-scanning-definition-to-someone-who-scans-10-ports-in-5-seconds)
    - [Run e2e tests that show port filtering in action](#run-e2e-tests-that-show-port-filtering-in-action)

<!-- /MarkdownTOC -->

# Quick Start Guide
Okay, I know this is where everyone goes first, so I've put it at the top..  Follow these steps to get up and running as fast as possible!

1. Be sure that your host is acceptable ([Host Information](#host-information))!  Or skip this part and just hope it is. :)
2. Clone this repo! 
```
git clone git@github.com:dampersand/dputnam-gravitational-challenge.git && cd dputnam-gravitational-challenge
```
3. Build Packetwatch: 
```
make build-app
```

To run Packetwatch in the foreground with default settings, simply run `make run-log`.  Let's see what that looks like by setting up a repeated TCP SYN attempt and then seeing what we see:
```
$ watch -n 2 'curl localhost:1337' &>/dev/null &
[1] 115496

$ make run-log
WARNING: The PW_IFDEV variable is not set. Defaulting to a blank string.
WARNING: The PW_PORTSCAN_TIME_THRESHOLD variable is not set. Defaulting to a blank string.
WARNING: The PW_PORTSCAN_PORT_THRESHOLD variable is not set. Defaulting to a blank string.
WARNING: The PW_PROMETHEUS_PORT variable is not set. Defaulting to a blank string.
WARNING: The PW_WHITELIST_SELF variable is not set. Defaulting to a blank string.
Creating dputnam-gravitational-challenge_packetwatch_run ... done
Welcome to Packetwatch!
We will be logging all incoming connections on lo
Any source IPs that hit 3 different ports within 60 second(s) will have their future connection attempts dropped!
We will whitelist any incoming connections originating from our own IPs on lo!
TIME               SOURCE IP        PORT   MESSAGE
04:54:59           127.0.0.1               Added to whitelist
04:55:01           127.0.0.1        1337
04:55:03           127.0.0.1        1337
04:55:05           127.0.0.1        1337
04:55:07           127.0.0.1        1337
04:55:09           127.0.0.1        1337
```

Great!  You're running Packetwatch!  Of course, the default settings are pretty useless.  All we are doing is monitoring the local address, and we're not even blocking any connections that come from localhost!  To make a little better use of Packetwatch, head on down to the [Usage](#usage) section to learn how to use all the settings and see some more advanced examples.


# Synopsis
Packetwatch is a dockerized network interface monitor with additional rudimentary connection-blocking capabilities.  Packetwatch is built entirely in python, and utilizes bpf loaded onto the interface with XDP to do its work - which makes it wildly lower overhead than doing the same tasks in userspace.

Packetwatch should be considered a proof-of-concept level project.  It is built to specifications as part of gravitational's platform/automation challenge, https://github.com/gravitational/careers/blob/main/challenges/platform/automation.md.  As a result, the project is encapsulated in 'ready to fire' status - meaning tests, builds, and deployment are baked in as-is, with no thought to external systems that might build/test/deploy the product.

Additionally, it should go without saying that Packetwatch has an extremely narrow use case. :)

# Host Information
Packetwatch is fully containerized and therefore portable, but that doesn't exactly mean it'll run on your grandmother's favorite toaster.  Here, you'll find the host architectures where Packetwatch has been tested, and any dependencies the hosts require.

## Host Architecture Tested
| Platform | OS | Kernel | Results |
|----------|----|--------|-------|
| Bare Metal (x86_64)| Ubuntu 20.04.4 | 5.4.0-100-generic | <span style="color:green">Flawless performance</span> |
| AWS EC2 | Ubuntu 20.04.1 | 5.11.0-1022-aws | <span style="color:orange">Generates warnings due to C macro redefinitions</span> |
| AWS EC2 | Debian 10 20210329-591 | 4.19.0-18-cloud-amd64 | <span style="color:green">Flawless performance</span> |
| AWS EC2 | CentOS 8 | .. | jk, rest in peace CentOS :( |

## Host Package Dependencies
|Package|Reason|Working version(s)|Other Notes|
|-------|------|------|------|
| make  | human interface for all actions | 4.2.1-1.2 |
| docker-ce | provides containerization platform | 5:20.10.12~3-0~ubuntu-focal | [Installation Instructions](https://docs.docker.com/engine/install/) |
| docker-compose | provides streamlined way to invoke build/deploy/test actions | 1.29.2 | [Installation Instructions](https://docs.docker.com/compose/install/) |
| linux-headers | Can't do much with BPF unless the headers are available. | 5.4.0-100-generic <br />5.11.0-1022-aws <br />4.19.0-18-cloud-amd64 | easiest installation method is to use $(uname -r) (for example, on deb systems apt-get install linux-headers-$(uname -r)) |

## Other Host Dependencies
The host user running any `make` commands should be part of the `docker` group:
```
sudo groupadd docker
sudo usermod -aG docker <user>
# you should restart your shell now to pick up the changes.
```

# Features and Functionality

## Connection Monitoring
Packetwatch monitors new connections bound for a specified interface (default: lo) and records/reports the source address and destination port.  A "new connection", in this case, is defined as any IPv4/TCP request that presents the SYN flag - but not the ACK flag (therefore Packetwatch will not report on syn-ack packets). Anything else (IPv6, UDP, etc) will be ignored.

## New Connection Filtering
Packetwatch detects IP addresses that are attempting to port-scan the monitored interface.  A portscanner is defined as any source IP address that attempts to connect to PW_PORTSCAN_PORT_THRESHOLD (default 3) different ports within a time period of PW_PORTSCAN_TIME_THRESHOLD (default 60) seconds (see [Arguments](#arguments)).  Any future new IPv4/TCP connections from that IP address will be summarily dropped.  Packetwatch will not interfere with any UDP, ICMP, IPv6, or IPv4/TCP traffic without the SYN flag alone - meaning malformed packets, other protocols, or related/established traffic will not be stopped.

Here, we see Packetwatch blacklisting a bad actor.  Shame shame, 192.168.1.101!

```
Welcome to Packetwatch!
We will be logging all incoming connections on enp0s31f6
Any source IPs that hit 3 different ports within 60 second(s) will have their future connection attempts dropped!
We will whitelist any incoming connections originating from our own IPs on enp0s31f6!
TIME               SOURCE IP        PORT   MESSAGE
05:42:14           192.168.1.9             Added to whitelist
05:42:22           192.168.1.101    80
05:42:23           192.168.1.101    80
05:42:24           192.168.1.101    80
05:42:24           192.168.1.101    80
05:42:25           192.168.1.101    80
05:42:25           192.168.1.101    81
05:42:25           192.168.1.101    81
05:42:26           192.168.1.101    81
05:42:26           192.168.1.101    81
05:42:27           192.168.1.101    81
05:42:27           192.168.1.101    82
05:42:27           192.168.1.101           Added to blacklist 
```

**Packetwatch will stop monitoring/reporting connections of known portscanners.**  Notice that 192.168.1.101 is hitting each port five times before moving on, but the final four hits on port 82 are not reported.

## Whitelisting
It's pretty common for computers to try to talk to themselves!  Packetwatch by default attempts to detect any IP address attached to the monitored interface and whitelists those IP addresses so they won't accidentally get filtered.

Here, we see Packetwatch graciously allowing traffic from 127.0.0.1 (our localhost address), even though its traffic qualifies it as a port scanner!

```
Welcome to Packetwatch!
We will be logging all incoming connections on lo
Any source IPs that hit 3 different ports within 60 second(s) will have their future connection attempts dropped!
We will whitelist any incoming connections originating from our own IPs on lo!
TIME               SOURCE IP        PORT   MESSAGE
05:44:31           127.0.0.1               Added to whitelist
05:44:58           127.0.0.1        80
05:44:58           127.0.0.1        81
05:44:58           127.0.0.1        82
05:44:58           127.0.0.1        83
05:44:58           127.0.0.1        84
```

## Prometheus
Packetwatch spits out Openmetrics-standard data on port 9090 (by default).  Right now, the only actual non-default datum is 'conn_count_total number of new connections', which is (fittingly) the number of new connections that Packetwatch has recorded since running.

```
# HELP conn_count_total number of new connections
# TYPE conn_count_total counter
conn_count_total 2.0
# HELP conn_count_created number of new connections
# TYPE conn_count_created gauge
conn_count_created 1.6464587720197325e+09
```

# Testing
Traditionally, tests are done by some CI runner, but as this is a proof-of-concept device meant to be airdropped onto anyone who is bored enough to be, say, reading a code challenge as part of a hiring process *cough*, unit testing and e2e testing have been included as part of the normal makefile-and-docker based workflow.

Packetwatch comes with a companion docker image simply called Tester.  Tester is actually based on Packetwatch using sneaky tricks and a multi-stage Dockerfile and can be built with `make build-test`.  It includes a couple extra useful tools but since it also includes all of Packetwatch, it can be used as a one-stop shop for debugging.

## Unit Tests
Tester can be used to perform unit tests by simply running `make unit-test`.  Unit tests are not currently complete, however - right now, unit testing will only test the `pwHelpers` section of the code.

To be human for a moment... this is partially because I remembered that the challenge advises me to 'avoid scope creep,' but I was having fun with the `green` package and didn't want to delete the unit tests from my submission... so as a compromise, you can have half of them. :)

## End-to-End (e2e) Tests
Tester can perform end-to-end tests to look for any aberrant behavior in Packetwatch.  There are two end-to-end test suites, entitled `e2e-black` and `e2e-white`.  E2e tests are typically done by setting up a dummy nginx service in Tester and setting Packetwatch to protect the local interface.

Both tests check packet-filtering negative behavior.  They:
- Check to make sure the nginx service is reachable over Packetwatch's monitored interface
- Check to make sure that Packetwatch doesn't flag IPs who establish new connections on ports slower than its threshold (default 60s)
- Check to make sure that Packetwatch doesn't flag IPs who establish a flurry of new connections on the same port, regardless of threshold

e2e-white tests the whitelisting behavior.  It:
- Checks to make sure that a whitelisted (local) IP address that launches a port-scan does not get its traffic blocked

e2e-black tests packet-filtering positive behavior.  It:
- Checks to make sure that an IP address that attempts to port-scan will have future connections blocked.

# Usage
The entire usage - with rudimentary examples - can be found in the Makefile.  Simply run `make help` or `make` in the repo for a quick reminder.

## Arguments
Packetwatch accepts arguments via environment variable.  Simply append or prepend them to your command string, eg:
```
$ PW_IFDEV=eth1 make run
```

| Argument | Default | Purpose |
|--------|-------|-------|
| PW_IFDEV | lo | The interface (e.g. eth0, enp3so2) to monitor |
| PW_PORTSCAN_TIME_THRESHOLD | 60 | Threshold (in seconds) under which connections from a single IP address may be a portscanner |
| PW_PORTSCAN_PORT_THRESHOLD | 3 | The number of ports someone can scan before they are considered a possible portscanner |
| PW_PROMETHEUS_PORT | 9090 | The port that prometheus will serve metrics upon |
| PW_WHITELIST_SELF | True | Whether or not to whitelist connections originating from the monitored interface.  Accepts 'True' or 'False' |

PW_PORTSCAN_TIME_THRESHOLD and PW_PORTSCAN_PORT_THRESHOLD are used together to determine if someone is a port scanner.  As mentioned above, a portscanner is defined as any source IP address that attempts to connect to PW_PORTSCAN_PORT_THRESHOLD different ports within a time period of PW_PORTSCAN_TIME_THRESHOLD seconds.

## Actions (make targets)
Packetwatch can be controlled via its makefile.  Simply run `make` commands and the magic happens.

| Command | Action |
|---------|--------|
| make help | Outputs usage |
| make build-app | Builds the Packetwatch docker image |
| make build-test| Builds the Tester docker image |
| make build-all | Builds both docker images |
| make exec-app | Negotiates an attached shell on a Packetwatch container.  Packetwatch will not be running.|
| make exec-test | Negotiates an attached shell on a Tester container.  Test suites will not be running.|
| make run | Starts a Packetwatch container in the background.  Use `docker logs` to view any output.|
| make run-log | Starts Packetwatch and attaches to the resultant container to see output in your shell |
| make unit-test | Starts a Tester container and runs unit tests |
| make e2e-black | Starts both Tester and Packetwatch and runs the `e2e-black` test suite |
| make e2e-white | Starts both Tester and Packetwatch and runs the `e2e-white` test suite |
| make stop | Stops any Packetwatch or Tester containers and removes them from the host |
| make clean | Stops any Packetwatch or Tester containers and removes them from the host.  Also removes the images, and criticizes your housekeeping. |

## Examples

### Monitor Localhost
Monitor localhost without blocking traffic originating from localhost with this command:

```
$ make run-log
WARNING: The PW_IFDEV variable is not set. Defaulting to a blank string.
WARNING: The PW_PORTSCAN_TIME_THRESHOLD variable is not set. Defaulting to a blank string.
WARNING: The PW_PORTSCAN_PORT_THRESHOLD variable is not set. Defaulting to a blank string.
WARNING: The PW_PROMETHEUS_PORT variable is not set. Defaulting to a blank string.
WARNING: The PW_WHITELIST_SELF variable is not set. Defaulting to a blank string.
Creating dputnam-gravitational-challenge_packetwatch_run ... done
Welcome to Packetwatch!
We will be logging all incoming connections on lo
Any source IPs that hit 3 different ports within 60 second(s) will have their future connection attempts dropped!
We will whitelist any incoming connections originating from our own IPs on lo!
TIME               SOURCE IP        PORT   MESSAGE
04:54:59           127.0.0.1               Added to whitelist
04:55:01           127.0.0.1        1337
04:55:03           127.0.0.1        1337
04:55:05           127.0.0.1        1337
04:55:07           127.0.0.1        1337
04:55:09           127.0.0.1        1337
```

### Monitor an external-facing interface but don't whitelist internal-originating traffic
Be careful that you don't inadvertently send traffic OUT your interface only to wind up BACK at the same interface, or you can get flagged as a port-scanner.  Good news is that this is pretty dang hard - most tools will figure out what's going on and use lo *even if you tell them not to, seriously what the heck guys*.

```
$ make run-log PW_IFDEV=enp0s31f6 PW_WHITELIST_SELF=False
WARNING: The PW_PORTSCAN_TIME_THRESHOLD variable is not set. Defaulting to a blank string.
WARNING: The PW_PORTSCAN_PORT_THRESHOLD variable is not set. Defaulting to a blank string.
WARNING: The PW_PROMETHEUS_PORT variable is not set. Defaulting to a blank string.
Creating dputnam-gravitational-challenge_packetwatch_run ... done
Welcome to Packetwatch!
We will be logging all incoming connections on enp0s31f6
Any source IPs that hit 3 different ports within 60 second(s) will have their future connection attempts dropped!
We will NOT whitelist any incoming connections originating from our own IPs on enp0s31f6, so play nice!
TIME               SOURCE IP        PORT   MESSAGE
06:31:09           192.168.1.101    80
06:31:09           192.168.1.101    80
06:31:14           192.168.1.101    443
06:31:15           192.168.1.101    443
```

### Change port scanning definition to "someone who scans 10 ports in 5 seconds"
Let's be a little more lax on what a port-scanner is.

A slow scanner:
```
$ make run-log PW_IFDEV=enp0s31f6 PW_PORTSCAN_TIME_THRESHOLD=5 PW_PORTSCAN_PORT_THRESHOLD=10
WARNING: The PW_PROMETHEUS_PORT variable is not set. Defaulting to a blank string.
WARNING: The PW_WHITELIST_SELF variable is not set. Defaulting to a blank string.
Creating dputnam-gravitational-challenge_packetwatch_run ... done
Welcome to Packetwatch!
We will be logging all incoming connections on enp0s31f6
Any source IPs that hit 10 different ports within 5 second(s) will have their future connection attempts dropped!
We will whitelist any incoming connections originating from our own IPs on enp0s31f6!
TIME               SOURCE IP        PORT   MESSAGE
06:42:31           192.168.1.9             Added to whitelist
06:42:34           192.168.1.101    80
06:42:36           192.168.1.101    81
06:42:38           192.168.1.101    82
06:42:40           192.168.1.101    83
06:42:42           192.168.1.101    84
06:42:44           192.168.1.101    85
06:42:46           192.168.1.101    86
06:42:48           192.168.1.101    87
06:42:50           192.168.1.101    88
06:42:51           192.168.1.101    89
06:42:52           192.168.1.101    90
```

Vs a fast scanner:
```
$ make run-log PW_IFDEV=enp0s31f6 PW_PORTSCAN_TIME_THRESHOLD=5 PW_PORTSCAN_PORT_THRESHOLD=10
WARNING: The PW_PROMETHEUS_PORT variable is not set. Defaulting to a blank string.
WARNING: The PW_WHITELIST_SELF variable is not set. Defaulting to a blank string.
Creating dputnam-gravitational-challenge_packetwatch_run ... done
Welcome to Packetwatch!
We will be logging all incoming connections on enp0s31f6
Any source IPs that hit 10 different ports within 5 second(s) will have their future connection attempts dropped!
We will whitelist any incoming connections originating from our own IPs on enp0s31f6!
TIME               SOURCE IP        PORT   MESSAGE
06:41:41           192.168.1.9             Added to whitelist
06:41:43           192.168.1.101    80
06:41:43           192.168.1.101    81
06:41:43           192.168.1.101    82
06:41:43           192.168.1.101    83
06:41:43           192.168.1.101    84
06:41:43           192.168.1.101    85
06:41:43           192.168.1.101    86
06:41:43           192.168.1.101    87
06:41:43           192.168.1.101    88
06:41:44           192.168.1.101    89
06:41:44           192.168.1.101           Added to blacklist
```

### Run e2e tests that show port filtering in action
I mean you're probably not here to test my code.  Or are you?

```
$ make e2e-black
WARNING: The PW_IFDEV variable is not set. Defaulting to a blank string.
WARNING: The PW_PORTSCAN_TIME_THRESHOLD variable is not set. Defaulting to a blank string.
WARNING: The PW_PORTSCAN_PORT_THRESHOLD variable is not set. Defaulting to a blank string.
WARNING: The PW_PROMETHEUS_PORT variable is not set. Defaulting to a blank string.
WARNING: The PW_WHITELIST_SELF variable is not set. Defaulting to a blank string.
Creating dputnam-gravitational-challenge_packetwatch_1 ... done
Creating dputnam-gravitational-challenge_tester_1      ... done
Attaching to dputnam-gravitational-challenge_tester_1, dputnam-gravitational-challenge_packetwatch_1
tester_1       | Packetwatch E2E testing suite
tester_1       | We will perform a series of tests against packetwatch over the local ifdev.
tester_1       | Please be sure no extraneous tcp traffic is flowing over the local ifdev during this time, as that is likely to interfere with the test.
tester_1       | Performing e2e testing assuming our IP is not whitelisted
tester_1       | Building nginx server for packetwatch to protect...
tester_1       | Starting nginx server on ports 8086, 8087, 8088
tester_1       |  * Starting nginx nginx
tester_1       |    ...done.
tester_1       | Waiting 5 seconds for race condition purposes
packetwatch_1  | Welcome to Packetwatch!
packetwatch_1  | We will be logging all incoming connections on lo
packetwatch_1  | Any source IPs that hit 3 different ports within 1 second(s) will have their future connection attempts dropped!
packetwatch_1  | We will NOT whitelist any incoming connections originating from our own IPs on lo, so play nice!
packetwatch_1  | TIME               SOURCE IP        PORT   MESSAGE
tester_1       | Checking to make sure nginx is up
tester_1       | Assumptions: None
tester_1       | Expected Behavior: nginx should return 200 and 'pong'
packetwatch_1  | 06:45:38           127.0.0.1        8086
tester_1       | SUCCESS
tester_1       |
tester_1       | Performing a slow portscan, then testing result.
tester_1       | Assumptions: PW_PORTSCAN_TIME_THRESHOLD is < 1s, or that whitelisting is on.
tester_1       | Expected Behavior: packetwatch should not blacklist this traffic, nginx should return 200 and 'pong'
packetwatch_1  | 06:45:38           127.0.0.1        8086
packetwatch_1  | 06:45:40           127.0.0.1        8087
packetwatch_1  | 06:45:41           127.0.0.1        8088
packetwatch_1  | 06:45:43           127.0.0.1        8086
tester_1       | SUCCESS
tester_1       |
tester_1       | Performing hammer test (multiple connections in quick succession on a single port)
tester_1       | Assumptions: PW_PORTSCAN_PORT_THRESHOLD is < 3
tester_1       | Expected Behavior: packetwatch should not blacklist this traffic, nginx should return 200 and 'pong'
packetwatch_1  | 06:45:43           127.0.0.1        8086
packetwatch_1  | 06:45:43           127.0.0.1        8086
packetwatch_1  | 06:45:43           127.0.0.1        8086
packetwatch_1  | 06:45:43           127.0.0.1        8086
tester_1       | SUCCESS
tester_1       |
tester_1       | Sleeping for a second so we don't accidentally irritate packetwatch
tester_1       | Performing fast portscan, then testing result.
tester_1       | Assumptions: PW_PORTSCAN_TIME_THRESHOLD is < 1s and PW_PORTSCAN_PORT_THRESHOLD is == 3 and we are not whitelisted
tester_1       | Expected Behavior: packetwatch should allow the first 3 scans, and then block subsequent connection attempts, resulting in exception
packetwatch_1  | 06:45:45           127.0.0.1        8086
packetwatch_1  | 06:45:45           127.0.0.1        8087
packetwatch_1  | 06:45:45           127.0.0.1        8088
packetwatch_1  | 06:45:45           127.0.0.1               Added to blacklist
tester_1       | SUCCESS
tester_1       | Thus ends our tests.  Press CTRL+C to exit.
```
