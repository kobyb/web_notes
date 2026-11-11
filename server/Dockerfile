FROM python:3.12-slim
# ffmpeg converts the sound; deno is the JavaScript runtime yt-dlp needs to read YouTube's player.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno
# Unpinned on purpose: YouTube changes often, and rebuilding the image picks up the yt-dlp release that keeps up with it.
RUN pip install --no-cache-dir -U "yt-dlp[default]"
WORKDIR /app
COPY app.py .
# Runs as an unprivileged user, so anything that wants a home or cache folder gets /tmp.
ENV PORT=8080 HOME=/tmp DENO_DIR=/tmp/deno
EXPOSE 8080
USER nobody
CMD ["python", "app.py"]
