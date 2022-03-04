.PHONY: all build run help
.DEFAULT_GOAL:= help

all: build run

help:   ## Print this help
	@echo 'Usage: make <target>'
	@echo 'Setup or run the Packetwatch tool'
	@echo
	@echo 'Targets:'
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

build:  		## Build packetwatch
	@docker-compose build packetwatch

exec:   		## Step into the packetwatch container
	@docker-compose run packetwatch /bin/bash

run:    		## Run packetwatch without attaching
	@docker-compose up

run-log:		## Run packetwatch, but attach and watch logs
	@docker-compose run packetwatch
