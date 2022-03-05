# Technical Discussion of Packetwatch
Why did I do the things that I did?  Let's find out.

## Overall Notes

### On architectural design
The architecture of this project is monolithic.  The original design I had in my head was to break the project into three to four containers:

* `etcd` for storing connection info
* `rabbitMQ` for inter-container communication
* An `xdp-controller` container, whose job was to load a static BPF program into an interface and then:
  * Emit connection information straight to etcd
  * Subscribe to `rabbitMQ` and listen for alerts that say things like 'whitelist this IP' 'blacklist this IP' 'remove this IP from a list'
* An `enforcer` container, whose job was to read the connection info in `etcd` and then:
  * Remove old calls from `etcd`
  * Decide who to blacklist and put them in a special key in `etcd`
  * Alert `xdp-controller` via `rabbitMQ` to look at the blacklist and pass new IPs to the BPF program

Additionally, `enforcer` would host a simple `flask` webserver to accept RESTful calls that amount to 'un/whitelist this IP' or 'un/blacklist this IP', then edit `etcd` and alert `xdp-controller` via `rabbitMQ` accordingly.

It's worth noting that I toyed with the idea of having `xdp-controller` host a `flask` server itself to make those API calls and remove rabbitmq in its entirety... but I felt that multithreading for an API really defeated the purpose of using XDP/BPF (that purpose to eliminate overhead in packet filtering)

The architecture I've just discussed is extremely modern.  It is modular - several of the components can be removed and therefore worked on by different teams, or completely rewritten without affecting others.  It is unix-y - each component does one specific job (mangling `etcd`, translating via `xdp`, etc) pretty well.  It is extensible - additional containers with additional functionality can be added.  It is scalable, to a degree - multiple interfaces can be served just by increasing the number of `xdp-controllers`, and enforcers can each run different rulesets.

So why did I go with monolithic?

Two reasons: 
* `It should take 6-10 hours to complete the challenge, be mindful of your own time and try and avoid scope creep.`
* Sometimes you just want a very slim tool to do one job and you never plan to upgrade it (ie, `curl` doesn't need to become `postman`).

The four containers above merged into a single container "Packetwatch" in this project.  This feels spaghetti-like... it's hard to separate, say, `bpfBuddy` from `main.py`, but the whole project is quite small, so it's no big deal.  You can see each of the etcd keys in bpfBuddy - callers, whitelist, blacklist - they're all there.

Also, the kernel doesn't lend itself well to modern architecture design.  I mean, the fact that you can only run one program into XDP per interface... yikes!  So we'd have to build some sort of program concatenator-and-loader to have multiple?  That's dragging 90s design into the future.


### On build choices

In the real world, I would not have chosen docker-compose.

Presumably, a container that I build is going to land on container orchestration.  Builds, then, should be done by an automated runner and the artifact pushed into a registry, thus allowing the deployment target to decide how the artifact is deployed.  docker-compose muddies the waters between 'how to build' and 'how to run' a container, and it's heavily opinionated (for instance, leaving the container artifact lying around is a by-product of docker-compose up, with no way to fix it).  Logging levels (like all those warnings) are not easily suppressed.

I also would not have built my test framework into a container.  Or, at least, would have divorced it into a different Dockerfile and maybe different repo.  Builds would be done by a CI runner, eliminating the need for these docker-compose.e2e* files that clutter up the repo.

### On environment variable passthrough

Don't judge me too harshly for deciding to put defaults in the container!

In the real world, the container would need to be workable from any deployment strategy - kubernetes, docker-compose, calling fred in the middle of the night to run his bash script, whatever.  That means we can't rely on defaults sitting in docker-compose or somewhere like that.  They need to be in the container!

But passthrough from make (the human interface layer) all the way to the backend sucks.


### On kernel header passthrough

One of the sketchier things I dealt with was deciding how to get the kernel headers and debugfs into the container.  Detecting and installing headers at runtime meant I could probably work on many different architectures, but also meant runs would take longer to start.  In the end, I settled on mounting the kernel header and debugfs location.  I figure it won't work with heavily disparate operating systems - I'd love to see if this works on Arch or CentOS - but it's okay on Debian, so it's okay by me.


### On weaknesses

You can totally break this software.  The 'callers' queue (which would have been etcd) has a maximum size, and the only pruning is 'is this thing old'.  Hit me with 10k different IP addresses over a long time threshold and we'll totally overflow the stack.  The blacklist has a maximum stack size, too.

It's rare, but I noticed a failure on `docker build` sometimes.  Literally removing the image and rerunning the build fixed the issue.  I chalk it up to my ancient lab machine and its faulty RAM, I was unable to replicate it more than the one time.

I have no idea what the RAM overhead for this project is!  I bet if you ran it on a rPi, it'd choke.

Is there a kernel that doesn't pass a ctx frame as network-ordered bytes?  Yeah, Packetwatch will choke on that.

The `bpfBuddy` code and the `main.py` code are meant to work with one another.  With more time, I might have built `bpfBuddy` as a plugin instead, so that `main.py` could become a simple XDP loader but `bpfBuddy` could decide what Packetwatch actually did.

I fervently believe that all output logs for a 12-factor app should be in JSON.  Not plaintext.  It gives me pain to see this in plaintext.


### On object orientation in C

Nooooooo thank you. :)  I stopped writing C++ a long time ago.  It's an amazing language, but I still have nightmares about void* casting.  This tiny script is small enough that I don't feel bad writing it in function-orientation.  After all, it's supposed to be a single inline script injected into the kernel!


### On testing

I really enjoy testing.  I think it's one of the more important parts of proper CI/CD, and it's something a lot of developers ignore.  Proper automated testing reduces the need for manual QA departments, which in turn gets you closer and closer to something like 'one commit one deploy one love' mentality, where gates to production are all but taken down in favor of fast disaster recovery, observability, and canary/rollback.  Life is better when the feedback loop between `git commit` and `oh my god I can see it on the website` is five minutes.

I never got the chance to play with `green`, so I took this as an opportunity to do so.  
