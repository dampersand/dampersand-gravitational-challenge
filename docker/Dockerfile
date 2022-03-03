FROM ubuntu:22.04

LABEL repository="https://github.com/dampersand/dputnam-gravitational-challenge"
LABEL maintainer="danputnam1@gmail.com"

RUN apt-get update
RUN apt-get install -y kmod python3-pip bpfcc-tools

#TODO - do I need bpftrace?

#fyi - this pip package is... unruly.  Doesn't appear to work on Debian, or on python:3.10.  We're gonna take the concession to ubuntu here.
#RUN pip install bcc

RUN mkdir /app
WORKDIR /app
COPY src/main.py ./
RUN chmod +x main.py
