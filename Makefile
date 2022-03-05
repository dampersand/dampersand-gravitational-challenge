.PHONY: help build-app build-test build-all exec-app exec-test run run-log unit-test e2e-white e2e-black stop clean
.DEFAULT_GOAL:= help

#Options
#?# PW_IFDEV
#?# 	network interface name that packetwatch will monitor (ex: eth0, eth2) (default: lo)
#?# PW_PORTSCAN_TIME_THRESHOLD	
#?# 	time threshold (seconds) for scanning (default: 60)
#?# PW_PORTSCAN_PORT_THRESHOLD
#?# 	number of ports threshold for scanning (default: 3)
#?# 	If you scan PW_PORTSCAN_PORT_THRESHOLD ports within PW_PORTSCAN_TIME_THRESHOLD, you are flagged as a port-scanner
#?# PW_PROMETHEUS_PORT	
#?# 	port to serve prometheus metrics (default: 9090)
#?# PW_WHITELIST_SELF
#?# 	prevent IPs attached to the monitored interface from being labeled as scanners (default: True)

help:       ## Print this help
	@echo 'Usage: make <target> [OPTION=value]'
	@echo 'Setup or run the Packetwatch tool'
	@echo
	@echo 'Targets:'
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'
	@echo
	@echo 'Options:'
	@fgrep -h "#?#" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/#?#//'
	@echo
	@echo 'Example Usages:'
	@echo 'run packetwatch in the background on eth0.  Do not blacklist connections from IP addresses associated with eth0'
	@echo '  make run PW_IFDEV=eth0 '
	@echo
	@echo 'run packetwatch in the foreground on eth0.  Blacklist connections regardless of their association with eth0.  Anyone who scans 3 (default) separate ports in 10 seconds is a scanner.'
	@echo '  make run-log PW_IFDEV=eth0 PW_WHITELIST_SELF=False PW_PORTSCAN_TIME_THRESHOLD=10'

build-app:  ## Build packetwatch
	@docker-compose build packetwatch

build-test: ## Build tester image
	@docker-compose build tester

build-all: build-app build-test
build-all:  ## Build both images
	@echo

exec-app:   ## Step into the packetwatch container for debug
	@docker-compose run --rm packetwatch /bin/bash

exec-test:  ## Step into the tester container for debug
	@docker-compose run --rm tester /bin/bash

run:        ## Run packetwatch in the background.
	@docker-compose run --rm --detach packetwatch

run-log:    ## Run packetwatch, attach and watch logs
	@docker-compose run --rm packetwatch

unit-test:  ## Unit-test packetwatch code.  Use "make e2e" instead for e2e tests.
	@docker-compose run --rm tester

e2e-black:  ## Run e2e tests without whitelisting self (test portscan detection)
	@docker-compose -f docker-compose.yml -f docker-compose.e2eblack.yml up

e2e-white:  ## Run e2e tests but whitelist self (test whitelist capability, but not portscan detection)
	@docker-compose -f docker-compose.yml -f docker-compose.e2ewhite.yml up

stop:				## Stop any instances of packetwatch or tester.
	@docker-compose down

clean:      ## Remove all instances of packetwatch and tester from your machine (including images)
	@docker-compose down --rmi all
	@echo 'Just a friendly reminder, when is the last time you ran `docker prune` and `docker container prune`?'
