.PHONY: all build run

all: build run

build:
	@docker-compose build packetwatch

run:
	@docker-compose run packetwatch