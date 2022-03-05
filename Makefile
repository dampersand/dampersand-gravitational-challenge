.PHONY: help build-app build-test build-all exec-app exec-test run run-log unit-test e2e-white e2e-black clean
.DEFAULT_GOAL:= help

help:       ## Print this help
	@echo 'Usage: make <target>'
	@echo 'Setup or run the Packetwatch tool'
	@echo
	@echo 'Targets:'
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

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

run:        ## Run packetwatch in the background
	@docker-compose run --rm --detach packetwatch

run-log:    ## Run packetwatch, attach and watch logs
	@docker-compose run --rm packetwatch

unit-test:  ## Unit-test packetwatch code.  Use "make e2e" instead for e2e tests.
	@docker-compose run --rm tester

e2e-black:  ## Run e2e tests without whitelisting self (test portscan detection)
	@docker-compose -f docker-compose.yml -f docker-compose.e2eblack.yml up

e2e-white:  ## Run e2e tests but whitelist self (test whitelist capability, but not portscan detection)
	@docker-compose -f docker-compose.yml -f docker-compose.e2ewhite.yml up

clean:      ## Remove all instances of packetwatch and tester from your machine (including images)
	@docker-compose down --rmi all
	@echo 'Just a friendly reminder, when is the last time you ran `docker prune` and `docker container prune`?'
