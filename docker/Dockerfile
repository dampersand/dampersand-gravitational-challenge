FROM ubuntu:22.04 as packetwatch
#FROM ubuntu:22.04
LABEL repository="https://github.com/dampersand/dputnam-gravitational-challenge"
LABEL maintainer="danputnam1@gmail.com"

RUN apt-get update
RUN apt-get install -y kmod python3-pip bpfcc-tools

RUN pip install netifaces prometheus-client

RUN mkdir /app
WORKDIR /app
COPY src/ ./
RUN chmod +x main.py

#entrypoints suck with docker-compose
CMD ["/usr/bin/python3", "main.py"]


####
#Test Image
#This image is basically packetwatch, but with some extra test utilities.
####

FROM packetwatch as tester

#Set up nginx so we have something to curl against
RUN apt-get install -y nginx
COPY nginx/default /etc/nginx/sites-available/default
COPY nginx/index.html /var/www/html/index.html

#Install testing software
RUN pip install green requests

#Run unit tests only by default
CMD ["/usr/local/bin/green"]
