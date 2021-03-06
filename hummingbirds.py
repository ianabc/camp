#!/home/pi/.virtualenvs/hummingbirds/bin/python
"""
Creates an HTTP server with basic auth and websocket communication.
"""
import argparse
import base64
import hashlib
import os
import time
import threading
import webbrowser
import io

import tornado.web
import tornado.httpserver
import tornado.websocket
from tornado.ioloop import PeriodicCallback

# Hashed password for comparison and a cookie for login cache
ROOT = os.path.normpath(os.path.dirname(__file__))
with open(os.path.join(ROOT, "password.txt")) as in_file:
    PASSWORD = in_file.read().strip()
COOKIE_NAME = "camp"


class IndexHandler(tornado.web.RequestHandler):

    def get(self):
        if args.require_login and not self.get_secure_cookie(COOKIE_NAME):
            self.redirect("/login")
        else:
            self.render("index.html", port=args.port)

class LogoutHandler(tornado.web.RequestHandler):
    def get(self):
        self.clear_cookie(COOKIE_NAME)
        self.redirect(self.get_argument("next", "/"))

class LoginHandler(tornado.web.RequestHandler):

    def get(self):
        self.render("login.html")

    def post(self):
        password = self.get_argument("password", "")
        if hashlib.sha512(password.encode('utf-8')).hexdigest() == PASSWORD:
            self.set_secure_cookie(COOKIE_NAME, str(time.time()))
            self.redirect("/")
        else:
            time.sleep(1)
            self.redirect(u"/login?error")

class WebSocket(tornado.websocket.WebSocketHandler):

    def check_origin(self, origin):
        return True

    def on_message(self, message):
        """Evaluates the function pointed to by json-rpc."""

        # Start an infinite loop when this is called
        if message == "read_camera":
            self.camera_loop = PeriodicCallback(self.loop, 10)
            self.camera_loop.start()

        # Extensibility for other methods
        else:
            print("Unsupported function: " + message)

    def loop(self):
        """Sends camera images in an infinite loop."""
        bio = io.BytesIO()

        if args.use_usb:
            _, frame = camera.read()
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            img.save(bio, "JPEG")
        else:
            camera.capture(bio, "jpeg", use_video_port=True)

        try:
            self.write_message(base64.b64encode(bio.getvalue()))
        except tornado.websocket.WebSocketClosedError:
            self.camera_loop.stop()


parser = argparse.ArgumentParser(description="Starts a webserver that "
                                 "connects to a webcam.")
parser.add_argument("--port", type=int, default=8080, help="The "
                    "port on which to serve the website.")
parser.add_argument("--resolution", type=str, default="low", help="The "
                    "video resolution. Can be high, medium, or low.")
parser.add_argument("--require-login", action="store_true", help="Require "
                    "a password to log in to webserver.")
parser.add_argument("--use-usb", action="store_true", help="Use a USB "
                    "webcam instead of the standard Pi camera.")
args = parser.parse_args()

if args.use_usb:
    import cv2
    from PIL import Image
    camera = cv2.VideoCapture(0)
else:
    import picamera
    camera = picamera.PiCamera()
    camera.hflip = True
    camera.vflip = True
    camera.zoom = ( 0.0, 0.0, 1.0, 1.0)
    camera.led = False
    #camera.start_preview()

resolutions = {"high": (1280, 720), "medium": (640, 480), "low": (320, 240)}
if args.resolution in resolutions:
    if args.use_usb:
        w, h = resolutions[args.resolution]
        camera.set(3, w)
        camera.set(4, h)
    else:
        camera.resolution = resolutions[args.resolution]
else:
    raise Exception("%s not in resolution options." % args.resolution)


if __name__ == "__main__":

    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), ".well-known/acme-challenge")
    }

    handlers = [(r"/", IndexHandler),
                (r"/login", LoginHandler),
                (r"/logout", LogoutHandler),
                (r"/websocket", WebSocket),
                (r"/.well-known/acme-challenge/(.*)", 
                    tornado.web.StaticFileHandler, 
                    dict(path=settings['static_path'])),
                (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': ROOT})]

    print("Listening on port: {}".format(args.port))
    application = tornado.web.Application(handlers, cookie_secret=PASSWORD)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(args.port)
    tornado.ioloop.IOLoop.instance().start()
