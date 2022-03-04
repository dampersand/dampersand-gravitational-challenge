FROM ubuntu:22.04

LABEL repository="https://github.com/dampersand/dputnam-gravitational-challenge"
LABEL maintainer="danputnam1@gmail.com"

RUN apt-get update
RUN apt-get install -y kmod python3-pip bpfcc-tools

RUN pip install netifaces prometheus-client

RUN mkdir /app
WORKDIR /app
COPY src/main.py ./
RUN chmod +x main.py
