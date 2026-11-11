# Web Notes audio server

Web Notes is a static page, and a page cannot download the sound of a YouTube video. This small server does it instead:
the page asks for `GET /audio?v=<video id>` and gets back the first five minutes as a mono MP3, which it then turns into notes.

Without this server the page still works: in Chrome and Edge on a computer it plays the video and listens to the tab.
With it, YouTube links work in every browser, phones included.

## Run it

It is one Python file plus `yt-dlp`, `ffmpeg` and `deno`; the Dockerfile installs all three.

```sh
docker build -t web-notes-audio server
docker run -p 8080:8080 web-notes-audio
```

Any host that runs a container will do (Fly.io, Render, Cloud Run, a VPS). It must be reachable over **https**, because the
page is.

| Setting        | Default                   | Meaning                                                        |
| -------------- | ------------------------- | -------------------------------------------------------------- |
| `PORT`         | `8080`                    | Port to listen on                                              |
| `ALLOW_ORIGIN` | `https://notes.gnupad.com` | Sites allowed to use the server, comma-separated; `*` for any  |
| `MAX_JOBS`     | `2`                       | Videos fetched at once; further requests get "busy, try again" |

## Connect the page

In `index.html`, set the address (no trailing slash):

```js
const YT_SERVER = 'https://your-server.example.com';
```

The YouTube button then reads "Write notes" instead of "Listen". If a fetch fails, the page says why and falls back to listening.

## Things to know

- **YouTube often refuses servers.** Requests from data-centre addresses are frequently answered with "Sign in to confirm
  you're not a bot". If that happens, try another host or region; a home or small-VPS address tends to fare better.
- **Keep yt-dlp current.** YouTube changes often. The image installs the latest release when built, so rebuild it when
  fetches start failing.
- **Terms of service.** Downloading audio this way is against YouTube's terms. The server only answers pages on
  `ALLOW_ORIGIN`, takes video ids only, refuses live streams and videos over 30 minutes, and keeps nothing on disk.
