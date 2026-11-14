# Fetch pinned source revisions so upstream changes do not silently alter builds.
FROM alpine/git:latest AS sources
RUN git clone https://github.com/sakshamvibesyt/telegram-about-bot.git /src/about \
 && cd /src/about && git checkout dea5f0b6c6288e5a945ddea8a435c9b63926a3fe \
 && git clone https://github.com/sakshamvibesyt/Sem_KITTUBOT.git /src/kittu \
 && cd /src/kittu && git checkout 9a5d369e14b3c6b85cc6c9e48117d77c5503d58b \
 && git clone https://github.com/sakshamvibesyt/Zyra_userbot.git /src/zyra \
 && cd /src/zyra && git checkout e118ecac8d86350bee439d6e2dd4cbbf7428464f \
 && git clone https://github.com/sakshamvibesyt/KanhaMusic.git /src/kanha \
 && cd /src/kanha && git checkout 06eb5785dbd68dfc40769ee8843ecc42039f29fb

FROM golang:1.26.2-bookworm AS kanha-build
RUN apt-get update && apt-get install -y --no-install-recommends \
      unzip curl zlib1g-dev build-essential \
 && rm -rf /var/lib/apt/lists/*
COPY --from=sources /src/kanha /build
WORKDIR /build
RUN rm -f .env sample.env \
 && chmod +x install.sh \
 && ./install.sh -n -t --quiet --skip-summary \
 && CGO_ENABLED=1 go build -v -trimpath -ldflags="-w -s" -o app ./cmd/app/

FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LD_LIBRARY_PATH=/opt/bots/kanha \
    TDJSON_PATH=/opt/bots/kanha/libtdjson.so.1.8.66
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg curl unzip ca-certificates libssl3 zlib1g libstdc++6 \
 && rm -rf /var/lib/apt/lists/* \
 && curl -fL https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux \
      -o /usr/local/bin/yt-dlp \
 && chmod 0755 /usr/local/bin/yt-dlp \
 && curl -fsSL https://deno.land/install.sh -o /tmp/deno-install.sh \
 && DENO_INSTALL=/usr/local sh /tmp/deno-install.sh -y --no-modify-path \
 && chmod 0755 /usr/local/bin/deno \
 && rm -f /tmp/deno-install.sh

WORKDIR /opt/app
COPY --from=sources /src/about /opt/bots/about
COPY --from=sources /src/kittu /opt/bots/kittu
COPY --from=sources /src/zyra /opt/bots/zyra
COPY --from=kanha-build /build /opt/bots/kanha
COPY main.py supervisor.py /opt/app/

# Exclude casino/betting and bomb/shop/game modules from the combined Kittu image.
RUN rm -f \
      /opt/bots/kittu/KITTUBOT/plugins/casino.py \
      /opt/bots/kittu/KITTUBOT/plugins/bomb.py \
      /opt/bots/kittu/KITTUBOT/plugins/shop.py \
      /opt/bots/kittu/KITTUBOT/plugins/games.py \
      /opt/bots/kittu/KITTUBOT/plugins/economy.py \
      /opt/bots/kittu/KITTUBOT/plugins/uno.py \
 && python -m venv /opt/venvs/about \
 && /opt/venvs/about/bin/pip install --upgrade pip \
 && /opt/venvs/about/bin/pip install -r /opt/bots/about/requirements.txt \
 && python -m venv /opt/venvs/kittu \
 && /opt/venvs/kittu/bin/pip install --upgrade pip \
 && /opt/venvs/kittu/bin/pip install -r /opt/bots/kittu/requirements.txt \
 && python -m venv /opt/venvs/zyra \
 && /opt/venvs/zyra/bin/pip install --upgrade pip \
 && /opt/venvs/zyra/bin/pip install -r /opt/bots/zyra/requirements.txt \
 && chmod 0755 /opt/bots/kanha/app

EXPOSE 10000
CMD ["python", "/opt/app/main.py"]
