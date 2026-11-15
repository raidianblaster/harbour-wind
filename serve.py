#!/usr/bin/env python3
"""Serve Harbour Wind locally and relay live HKO readings.

HKO's regional-weather CSVs send no CORS header, so the page cannot fetch them
directly. This server hosts index.html and exposes three same-origin feeds:

  /hko/wind  latest_10min_wind.csv         (10-min mean dir, speed, gust)
  /hko/temp  latest_1min_temperature.csv   (air temperature)
  /hko/rh    latest_1min_humidity.csv      (relative humidity)

Upstream responses are cached for 60 s; if HKO is unreachable the last good
copy is served. Standard library only.

    python3 serve.py [port]      # default 8000, bound to 127.0.0.1
"""
import functools
import http.server
import os
import sys
import threading
import time
import urllib.request

BASE = "https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/"
FEEDS = {
    "wind": "latest_10min_wind.csv",
    "temp": "latest_1min_temperature.csv",
    "rh": "latest_1min_humidity.csv",
}
TTL = 60
_cache = {}
_lock = threading.Lock()


def fetch(key):
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < TTL:
            return hit[1]
    try:
        req = urllib.request.Request(BASE + FEEDS[key], headers={"User-Agent": "harbour-wind/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read()
    except Exception:
        if hit:  # serve stale rather than nothing
            return hit[1]
        raise
    with _lock:
        _cache[key] = (time.time(), body)
    return body


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if not path.startswith("/hko/"):
            return super().do_GET()
        key = path[len("/hko/"):]
        if key not in FEEDS:
            return self.send_error(404, "unknown feed")
        try:
            body = fetch(key)
        except Exception as e:
            return self.send_error(502, f"HKO fetch failed: {type(e).__name__}")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        if "/hko/" not in str(args[0] if args else ""):  # keep the 2-min polls quiet
            super().log_message(fmt, *args)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    root = os.path.dirname(os.path.abspath(__file__))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=root))
    print(f"Harbour Wind on http://localhost:{port}  (live HKO relay at /hko/*)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
