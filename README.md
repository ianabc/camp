camp
====

Another Raspberry Pi camera webserver.

![](img/example.png)

What it does
============

Hosts a website where you can view your webcam in real time.

Why I wrote it
==============

There are a *lot* of tutorials out there on how to turn your pi into a webcam
server. Most of them involve installing [motion](http://www.lavrsen.dk/foswiki/bin/view/Motion),
which works great in many use cases. However, I wanted something simpler. Namely,
I wanted:

 * Minimal configuration
 * Password protection
 * One-way streaming
 * Easily customizable webpage
 * Extensible server

camp does just this. Nothing else. This (hopefully) makes it the simplest
and fastest option out there.

Installation
============

Camp uses [tornado](http://www.tornadoweb.org/en/stable/) to create a
web server. It can interact with the [Pi camera](http://www.adafruit.com/products/1367)
with the aptly named [picamera](http://picamera.readthedocs.org/en/release-1.7/)
module, or it can use USB webcams with [opencv](http://opencv.org/)
and [Pillow](http://pillow.readthedocs.org/en/latest/installation.html). The
command below installs both sets of dependencies.

```
sudo apt-get install python-dev python-pip python-opencv libjpeg-dev
sudo pip install tornado Pillow picamera
```

Once the dependencies are installed on your pi, you can clone this repository and
run the server.

```
git clone https://github.com/patrickfuller/camp.git
python camp/server.py
```

Navigate to http://your.r.pi.ip:8000 and check out your webcam.

####USB Camera

Use with `python server.py --use-usb`.

####Password

![](img/login.png)

With the `--require-login` flag, camp will open a login page before allowing
webcam access.

The default password is "raspberry". In order to change it, run this in your
camp directory:

```
python -c "import hashlib; import getpass; print(hashlib.sha512(getpass.getpass().encode('utf-8')).hexdigest())" > password.txt
```

This will prompt you for a password, encrypt it, and save the result in
`password.txt`.

Note that this level of password protection is basic - it's fine for keeping the
occasional stranger out, but won't stand up to targeted hacking.

####Run on startup

It's nice to have your pi start camp whenever it turns on. Let's make that
happen. Type `sudo nano /etc/rc.local` to open this file for editing, and add
the line `nohup python /home/pi/camp/server.py &` before the last line. Note
that you may need to change the path (`/home/pi/camp/server.py`) to point to
the right file.

####Customization

The website consists of `index.html`, `login.html`, and `style.css`. These can be
edited to change the look of camp.

If you want to add in extra functionality, edit `client.js` and `server.py`.
The client should send a request to the server, which will then cause the
server to do something.

If you want to add in extra camera features, opencv comes with a lot of useful
computer vision algorithms. Check out its functionality before writing your
own.

#### SSL
It is pretty simple to add SSL to stop your password from being transmitted to
the application in the plain. This isn't perfect, but it's an improvement. A
simple way to do this is to use the [getssl](https://github.com/srvrco/getssl)
shell script to perform the registration and renewal steps for letsencrypt
certificates. In addition to the script, we need to ensure that the application
can serve up the response to the ACME challenge.

First of all, generate the configuration
```
$ cd getssl
$ ./getssl -c <your domain name here>
```
This writes files to `~/.getssl/` including a certificate config. The only thing
you should need to change is the ACME response location.
```
$ vi ~/.getssl/<your domain name here>/getssl.cfg
...
ACL=('/home/pi/Projects/hummingbirds2/.well-known/acme-challenge')
...
```
Make sure that your application is publicly routable on ports 80 and 443. Then
run the script
```
$ cd getssl
$ ./getssl <your domain name here>
```
The script should write a response into
.well-known/acme-challenge/SOMEWEIRDFILE, it'll go and grab the signed
certificate and intermediate certs and write them into ~/.getssl/<your domain
name here>.

