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
python camp/hummingbirds.py
```

Navigate to http://your.r.pi.ip:8080 and check out your webcam.

####USB Camera

Use with `python hummingbirds.py --use-usb`.

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


####Customization

The website consists of `index.html`, `login.html`, and `style.css`. These can be
edited to change the look of camp.

If you want to add in extra functionality, edit `client.js` and `hummingbirds.py`.
The client should send a request to the server, which will then cause the
server to do something.

If you want to add in extra camera features, opencv comes with a lot of useful
computer vision algorithms. Check out its functionality before writing your
own.

### Example Setup

**N.B. This is JUST an example, not in any way a best practice setup!**

This setup will use nginx to provide an SSL reverse proxy to the webcam service.
This will allow us to avoid the password being sent in clear text. It will also
cover setting up the program as a (systemd) service. 

You could just connect your pi to a public IP, but if (like me) you're behind a
domestic router, you will need to set up port forwarding for ports 80 and 443 so
that incoming traffic on those ports lands on nginx. Along the way, we will be
using letsencrypt to get valid certificates which also requires public access to
these ports.

Our starting point is raspbian-lite (2016-05), we assume that you've already
configured a network connection (e.g. put a working config in
wpa_supplicant.conf and told raspi-config to wait for network on boot).

#### VirtualEnvs
On top of the lite distribution we'll add virtualenv to keep our python
dependencies isolated.
```
$ apt-get install virtualenv virtualenv-wrapper git build-essential python3-dev
$ vi ~/.bash_profile
  ...
 +WORKON_HOME=$HOME/.virtualenvs
 +PROJECT_HOME=$HOME/Projects

$ mkdir $HOME/Projects
```
Log out then back in again to pick up all of the virtualenv tools, then clone
out this repository
```
$ mkproject -p /usr/bin/python3.4 hummingbirds
```

You should now be inside a working environment ready to install the project. To
do that, just clone this repository to that location
```
$ git clone https://github.com/ianabc/camp.git .
```

#### GetSSL and Letsencrupt
The [getssl](https://github.com/srvrco/getssl) project uses a bash script to
interact with the [letsencrypt](https://letsencrypt.org) project. We'll use it
to provide a valid certificate and key pair for nginx. We will use
birds.example.com as an example domain.
```
$ cd $HOME
$ apt-get install dnsutils
$ git clone https://github.com/srvrco/getssl
$ cd getssl
$ ./getssl -c birds.example.com
```
This will write config files for getssl (global) and the domain
birds.example.com under $HOME/.getssl. The global configuration is fine for our
needs, but we need to tweak the domain configuration options. The default
configuration uses the letsencrypt staging servers to allow you to debug the
process, these servers don't have the same restrictions and rate limits as the
production service. We'll assume you've done that (do it!) and everything is
ready for real certificates. 
```
$ cd .getssl/birds.example.com/
$ vi getssl.cfg
 ...
-#CA=https://acme-v01.api.letsencrypt.org
+CA=https://acme-v01.api.letsencrypt.org
 ...
-SANS=www.birs.example.com
+#SANS=www.birs.example.com
 ...
+ACL=/home/pi/Projects/hummingbirds/.well-known/acme-challenge
 ...
-#DOMAIN_CHAIN_LOCATION=""
+DOMAIN_CHAIN_LOCATION="/home/pi/.getssl/birds.example.com/birds.example.com_chain.crt"
 ...
```

During the certificate issuing process the script will write a file under the
$ACL location and the letsencrypt service will request it. We need a process to
serve that request, but we can do it with the camp application. Just make sure
that it is listening on port 80 that is accessible to inbound internet
connections (this might involve setting up port forwarding on your router).
```
$ workon hummingbirds
$ python hummingbirds.py --port 80
```

You should now be able to run the getssl script and have your response served up
via hummingbirds.py. Make sure the config file in
`~/.getssl/birds.example.com/getssl.cfg` is correct (particularly the ACL
value).
```
$ cd $HOME/getssl
$ ./getssl birds.example.com
```
You should end up with keys and certificates under `.getssl/birds.example.com`
including one with the filename `birds.example.com_chain.crt`. This file is the
certificate along with the correct chain information to allow browsers to
validate your side.


#### nginx
Now install nginx and create a configuration to act as a reverse proxy for the
site and websocket.
```
$ apt-get install nginx
$ cd /etc/nginx/sites-enabled
$ sudo vi default
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name birds.example.com;
    return      301 https://$server_name$request_uri;
}

server {

    listen 443 ssl;

    server_name birds.example.com
    add_header Strict-Transport-Security "max-age=31536000";

    ssl_certificate     /home/pi/.getssl/birds.example.com/birds.example.com_chain.crt;
    ssl_certificate_key /home/pi/.getssl/birds.example.com/birds.example.com.key;
    ssl_protocols       TLSv1 TLSv1.1 TLSv1.2;
    ssl_ciphers     HIGH:!aNULL:!MD5;


    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

}

$ sudo systemctl enable nginx
$ sudo systemctl start nginx
```

Now to make sure that the script is started at the appropriate time (after nginx
on boot), we will add a service to systemd
```
$ sudo vi /etc/systemd/system/hummingbirds.service
[Unit]
Description=Hummingbird webcam program
After=nginx.service

[Service]
Type=simple
ExecStart=/home/pi/Projects/hummingbirds/hummingbirds.py --require-login --resolution=medium

[Install]
WantedBy=multi-user.target

$ sudo systemctl daemon-reload
$ sudo systemctl enable hummingbirds
$ sudo systemctl start hummingbirds
```

One more bit of housekeeping, we should run cron so that we can update the
certifiate when it expires (and remember to reload the webserver). Since we
created the configuration as the user pi we should use /etc/crontab and run as
that user during the update.
```
$ vi /etc/crontab
...
35 3    * * *   pi      /home/pi/getssl/getssl -u -a -q
36 3    * * *   root    systemctl reload nginx
```

At this point, visiting http://birds.example.com should redirect you to
https://birds.example.com and then on to the login page. You should enter the
password you defined above then enjoy the view!

A final touch is to turn off the camera LED, I'm not sure how hummingbirds feel
about RED LEDs.
```
$ sudo vi /boot/config.txt
...
disable_camera_led=1
$ sudo reboot
```
