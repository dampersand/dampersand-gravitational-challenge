# dputnam-gravitational-challenge
# Packetwatch

## Synopsis
Packetwatch is a dockerized network interface monitor with additional rudimentary connection-blocking capabilities.  Packetwatch is built entirely in python, and utilizes bpf to do its work.

Packetwatch should be considered a proof-of-concept level project.  It is built to specifications as part of gravitational's platform/automation challenge, https://github.com/gravitational/careers/blob/main/challenges/platform/automation.md.  As a result, the project is encapsulated in 'ready to fire' status - meaning tests, builds, and deployment are baked in as-is, with no thought to external systems that might build/test/deploy the product.

Additionally, it should go without saying that packetwatch has an extremely narrow use case. :)

## Host Dependencies
Packetwatch is fully containerized, so dependencies are limited to tools required for the host to run docker.

### Host Architecture Tested
* Bare Metal Ubuntu 20.04.4 LTS (Focal) with 5.4.0-100-generic kernel, x86_64 CPU architecture
* AWS EC2 

### Package Dependencies
|Package|Reason|Version(s) tested|Other Notes|
|-------|------|------|------|
| make  | human interface for all actions | 4.2.1-1.2 |
| docker-ce | provides containerization platform | 5:20.10.12~3-0~ubuntu-focal | [Installation Instructions](https://docs.docker.com/engine/install/) |
| docker-compose | provides streamlined way to invoke build/deploy/test actions |1.29.2 | [Installation Instructions](https://docs.docker.com/compose/install/) |

### Other Dependencies
* The host user running any `make` commands should be part of the `docker` group:
```
sudo groupadd docker
sudo usermod -aG docker <user>
# you should restart your shell now to pick up the changes.
```