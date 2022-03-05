# Interview Questions

Hi!  My name is Dan.  I'm comin' at ya for a Level 5 position, so I've written you this lovely wall of text.  I hope you'll forgive going over 4 - 8 sentences for some of the questions... I'm sure you wouldn't want one-word answers from someone applying for a Level 5 position!  I want you to feel confident that I know what I'm banging on about.

## Level 1
**1. How would you prove the code is correct?**
> End-to-end testing and unit testing... and I include both!  Unit testing proves that individual functions do what they purport, and end-to-end testing proves that the software does what it should!  I won't walk you through my e2e tests right here, but you can find them by running `make e2e-black` or `make e2e-white`.

**2. How would you make this solution better?**
> I talk about this in TechnicalDiscussion.md, but let's list some out out:
> * JSON output option
> * More prometheus counters (observability)
> * a UI
> * Multiple containers to 'break out' the code, make it modular/scalable/etc (if scoping calls for it, of course.  This is my favorite way to upgrade the solution, but it's probably not viable for 'quick-and-dirty observability')
> * Finish unit tests!
> * Test on other architecture/kernels
> * bpfBuddy (the userspace-side) should become a plugin to be bundled with the xdp code instead of main.py
>   * main.py should become an xdp loader instead of being bundled with bpfBuddy
>   * main.py should be able to "concatenate" (not literally) multiple xdp programs to run on the same interface and load them simultaneously
>   * stackoverflows (like what might happen to the caller/blacklist/whitelist vars) should be detected!
> There's SO much more I would do without ever touching the core functionality of the program.  This could easily be a fully-fledged 12-factor app with tons of modularity without out-scoping the idea of a packet monitor!

**3. Is it possible for this program to miss a connection?**
> Well that depends how you define a connection.  I explicitly define a connection as 'a non-malformed IPv4/TCP packet with the SYN flag set and WITHOUT the ACK flag set'.  If you are making a UDP 'connection' (lol) or using IPv6, or writing your own custom protocol that fits within an ethhdr, or, like, you have a clever set of morse code based on ICMP to replace the TCP 3WH but still negotiate a TCP connection, then yeah, you're gonna dodge Packetwatch.

> However, if you want me to assume I performed a /proc/net/tcp level 1 challenge, then yes, we could miss a connection - any fresh connection that is opened and closed within the resolution time will be missed.  Along with the UDP/proprietary handshake situation, too!

**4. If you weren't following these requirements, how would you solve the problem of logging every new connection?**
> I'm not sure this question is relevant, as I performed a Level 5 challenge that does not have the problem of missing connections due ot time resolution.  Real-time BPF allows me to log every new connection that the /proc/net/tcp solution would miss, even if it appears and then disappears within an arbitrary resolution time.  That seems to me the correct way to solve the problem of logging every new connection.  The only other way to log 'missed' connections would be to expand my definition of a connection, and that's a real wormhole (for example, I could completely change strategy and use BPF to fire on `connect()` syscalls, but then I might miss malformed connection attempts... or I could simply expand to IPv6, etc).

> Assuming ou want me to answer as though I'd written a /proc/net/tcp solution: if I hadn't literally just learned about BPF for this challenge, I would have said 'tcpdump instead of /proc/net/tcp', but I now know that tcpdump and the pcap library is just BPF with more steps, so it just resolves to my 'Real-time BPF' answer above. :)


## Level 2
**1. Why did you choose `docker-compose and make` to write the build automation?**
> I wanted it to be easy for the reviewers to run.  In the real world, I would have built something with some CI capability and some CD capability - github actions, or (*shudder*) amazon's Code* suite.  But the thing is that I'm the only person working on the repo, so CI is just me doing my e2e tests and a 'git merge' whenever I feel saucy, and there are zero deploy targets for CD to be useful.  So, like, why have a github runner?  Part of building good things is knowing when NOT to use your exciting tools.

> Everyone has make (and make is super easy to read), and docker-compose is quick and easy for a reviewer to set up.  It builds Dockerfiles and handles their setup, run, lifecycle, and displaying their output.  It's the perfect technology for a one-off evaluator of a highly portable product.

**2. Is there anything else you would test if you had more time?**
> Well, I talk a bit about it in the README, but the unit tests aren't 100% coverage - I don't test bpfBuddy.  As I say in the readme, you guys DID say 'don't overscope', and... well, unit testing is a BIIIIIT out of scope for a glorified monitoring script.  I would add some granularity to the exception handling in the e2e tests - catching blanket exceptions on the 'blacklist' test doesn't sit well with me.  I would like to trigger some exceptions (unit tests again) in main.py and bpfbuddy better.

> I also do zero unit testing of the C code, which is a lot harder to do because the C code isn't object oriented.  Those would be the tests to hit, IMO.

> Oh!  And high traffic testing!

**3. What is the most important tool, script, or technique you have for solving problems in production?  Explain why this tool/script/technique is the most important.**
> Okay, you specifically asked for 4-8 sentence answers per question and then ask THIS doozy, so that's no fair!

> I read a book a long time ago called "Zen and the Art of Motorcycle Maintenance."  In it, the author waxes on a bit about troubleshooting, saying (and I paraphrase): "When we troubleshoot, we start with hunches - things we can guess from experiences, or from obvious clues.  Once we've tired out all of our hunches, then we have to haul The Scientific Method up from the basement - that big, clunky machine that takes forever to start and slowly, tediously grinds through the whole problem.  It's slow, but it will always find the answer."  Now, you'd expect me to say 'the scientific method' is the most important tool in my arsenal, but I'd actually say hunches (or more accurately, the clues that inform the hunches).  Come on - we're talking about a production situation - something that needs fixed fast.  You better believe I'm going to gather as many obvious clues as I can and look at those first!  The possibility of saving time based on some choice error messages and log files - especially ones I'm familiar enough with to sort wheat from chaff - that's the gold right there!

> Of course, that's not to say that the scientific method isn't an important tool - it's wildly important in a world where you don't already have experience with everything!  A huge part of troubleshooting mastery is knowing when your hunches are low-probability when to turn around and boot up the scientific method!  But all those 'rockstars' you look up to who can solve problems at the drop of a hat, who've been in one company for ten years and know everything?  Hunches - error messages, log files, and experience, every time.

> ...Oh, what's that, you were expecting something more concrete?  Well, if you put a gun to my head and made me choose, log files.  Good logs to me are greater than metrics, graphs, crash-cart pods, and Kali Linux combined.  Watching logs in peacetime gives you passive experience, helps you see patterns - and therefore anomalies.  And where there are anomalies, there's fire.


## Level 3
**1. If you had to deploy this program to hundreds of servers, what would be your preferred method?  Why?**
> Wow are you ready for a controversial answer?
> This program is VERY CLEARLY not a web app, so I'm assuming this is getting deployed to worker servers - internal development or production servers like databases, load balancers, etc.  Of the four methods I might consider:

> 1. CI/CD or a one-off script to be run remotely
> 2. Packing the payload into a machine image
> 3. Configuration management
> 4. Declarative orchestrator management (eg argoCD)

> My choice is that the deployment should be handled by declarative config management - puppet, for example.  That's right!  The oldest, least-glamorous, much-maligned, no-longer-fashionable deployment choice: the config manager!  Why?

> * The payload's running on baremetal servers or VMs and needs to run on each one, so a declarative orchestrator is right out - am I going to run minikube just to keep this docker image running on a single server?  That's a lot of overhead and overkill, plus those orchestrators are meant to work with cattle, not pets.  There is an exception - if your environment is a kubernetes cluster then yes, okay, a DaemonSet solves your problem in one fell swoop.  Barring that, though, declarative orchestrator management is just the wrong tool, so let's kick it out right now.
> * The payload is a pet, not cattle.  It needs to be running to do its job, and due to XDP's "one program per interface," there can be only one. It's a service that must stay up all the time, not a library call to be invoked.  That means if it crashes, it's gotta come back up.  Advantage config management:
>   * Config management's "every x minutes" check can make sure it's in running state.  
>   * Deploying using one-time scripts (like ansible or a script from a CD runner, or packing it into a machine image) can't do that, and you'd need to build some self-healing code and add that, too.
> * The payload has requirements of the host - even though it's a docker container.  Advantage config management:
>   * Config management code allows us to put the host dependencies right alongside the deployment 'script' as opposed to packing it somewhere, so it's all in one place. 
>   * Machine images would need to have the dependencies packed in, splitting up the declarative code so that when it's time to EOL the product, you have to remember all the different repos it exists in or risk leaving tech debt lying around!
>   * One-off scripts or CD runners would need to have imperative code to check for the dependencies written, which would differ from OS to OS.  I think xckd did a joke a while back about a 'universal installer script'... you sure you wanna support that?

> I wanna talk about CI/CD a second here - config management doesn't preclude using CI/CD, it's just that I wouldn't use the CD runner to reach out and deploy to the servers.  At best, the CD runner might hook into the config manager's repo and change a line of code to change the docker sha that the config management is enforcing, thus TRIGGERING the deployment... but config management should do the actual deployment.

**2.  What is the hardest technical problem or outage you've had to solve in your career?  Explain what made it so difficult?**
> Any DNS issue.  Seriously man, it's never repeatable, it's never loggable, and every single troubleshooting tool uses different libraries to resolve DNS.  No chance.

> Okay, but for real: at Taboola, there was a great undertaking to home-build an internal downtime detector.  The driving force is that we used roughly every single technology on the planet (I asked the VP what database tech they used in my interview, she replied that it was easier to go to the wikipedia article for 'list of databases' and pick the ones they didn't.  She wasn't lying).  Which meant when one thing went down, a million things went down.  Pager calls everywhere.  The first ten minutes of every outage was just figuring out what thing actually was the cause.  This downtime detector was meant to study patterns in the system - errors between services, inter-service dependencies, etc - and try to draw maps of what affected what.  It was also meant to try to study our downtimes and record the causes.

> We're talking machine learning, here, if you haven't already guessed!

> My part in it was to build the system that catalogued connections and hunted for anomalous connections.  It was well known, for instance, that database servers connected to consul servers, but at what frequency?  Furthermore, this system could be used to track malicious-entities who had breached our network - after all, why would a kubernetes server, with its own service discovery layer, need to talk to a consul server?

> I built a three-container system that kept tabs on every live server (!!!!) in our ecosystem and reported on their connections, then passed each connection through some k-means machine learning algorithms (that I wrote) to profile each server TYPE and hunt for anomalies.

> It worked GANGBUSTERS.  I didn't stick around to see them implement it, but I believe it's still in use.

> What made it difficult was the scope. I had to literally take an entire class on machine learning just for this one project... and it was a blast.  I haven't gotten to use my science degree like that for a long time.  I then had to make sure it ran on every OS, every server that we ran.  I had to plan for massive, production-level amounts of data without bogging the individuals down... and at an ad company, 'production level data' is not something you can test for in the dev environment.  I built out the entire monitoring suite, the logging suite, the observability layer - everything.  Not dissimilar to this project, although I had to develop it all the way to a working product to be proud of!

## Level 4
No questions

## Level 5
No questions