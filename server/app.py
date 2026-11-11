#!/usr/bin/env python3
"""Fetches the sound of a YouTube video for Web Notes.

GET /audio?v=<video id>  ->  the first five minutes as a small mono MP3, with the video's title in the X-Title header.

Settings (environment variables):
  PORT          port to listen on (default 8080)
  ALLOW_ORIGIN  comma-separated sites allowed to use this server (default https://notes.gnupad.com); * allows any
  MAX_JOBS      videos fetched at the same time (default 2); further requests are told to try again
"""
import os
import re
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

ORIGINS = [o.strip().rstrip('/') for o in os.environ.get('ALLOW_ORIGIN', 'https://notes.gnupad.com').split(',')]
SECONDS = 300            # how much of the video Web Notes writes down
MAX_VIDEO = 30 * 60      # longer videos are refused rather than downloaded whole
jobs = threading.BoundedSemaphore(int(os.environ.get('MAX_JOBS', 2)))


class Refused(Exception):
    """A problem worth telling the user about."""


def download(video, folder):
    """Saves the video's audio track into folder. Returns (path, title)."""
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError, match_filter_func
    options = {
        'format': 'bestaudio/best', 'outtmpl': os.path.join(folder, 'in.%(ext)s'), 'noplaylist': True,
        'quiet': True, 'no_warnings': True, 'socket_timeout': 20, 'retries': 2, 'cachedir': False,
        'match_filter': match_filter_func(f'!is_live & duration <= {MAX_VIDEO}'),
    }
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info('https://www.youtube.com/watch?v=' + video, download=True)
    except DownloadError as e:
        raise Refused('YouTube would not hand over that video: ' + str(e).removeprefix('ERROR: ')[:150])
    files = os.listdir(folder)
    if not files:
        raise Refused(f'That video is live or longer than {MAX_VIDEO // 60} minutes.')
    return os.path.join(folder, files[0]), (info or {}).get('title') or ''


def to_mp3(path, folder):
    """The first SECONDS of an audio file as mono MP3 bytes: small, and every browser can decode it."""
    out = os.path.join(folder, 'out.mp3')
    done = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-t', str(SECONDS), '-vn', '-ac', '1', '-ar', '22050',
                           '-b:a', '64k', out], capture_output=True, timeout=120)
    if done.returncode:
        raise Refused('The sound of that video could not be converted.')
    with open(out, 'rb') as f:
        return f.read()


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, kind='text/plain; charset=utf-8', title=None):
        origin = self.headers.get('Origin', '')
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Vary', 'Origin')
        if '*' in ORIGINS or origin in ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin or '*')
            self.send_header('Access-Control-Expose-Headers', 'X-Title')
        if title is not None:
            self.send_header('X-Title', quote(title[:200]))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == '/':
            return self.reply(200, b'Web Notes audio server\n')
        if url.path != '/audio':
            return self.reply(404, b'Not found\n')
        # Only pages on the allowed sites may use this; it is not a public downloader. (A check on good manners, not a lock.)
        if '*' not in ORIGINS and self.headers.get('Origin') not in ORIGINS:
            return self.reply(403, b'This server only answers the Web Notes page.\n')
        video = parse_qs(url.query).get('v', [''])[0]
        if not re.fullmatch(r'[\w-]{11}', video):          # an id, never a full address: the server fetches from YouTube only
            return self.reply(400, b'That is not a YouTube video id.\n')
        if not jobs.acquire(blocking=False):
            return self.reply(429, b'The server is busy. Try again in a minute.\n')
        try:
            with tempfile.TemporaryDirectory() as folder:
                path, title = download(video, folder)
                self.reply(200, to_mp3(path, folder), 'audio/mpeg', title)
        except Refused as e:
            self.reply(502, (str(e) + '\n').encode())
        except Exception as e:                              # never leave the browser waiting on a crash
            self.log_error('%r', e)
            self.reply(502, b'The video could not be fetched.\n')
        finally:
            jobs.release()


if __name__ == '__main__':
    ThreadingHTTPServer(('', int(os.environ.get('PORT', 8080))), Handler).serve_forever()
