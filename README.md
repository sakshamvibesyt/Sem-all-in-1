# Sem All In One — deployment package

This ZIP contains the integration/hosting layer for one Render Docker Web Service.
At Docker build time it downloads four public source repositories at pinned commit
IDs and runs them as separate processes:

- About Bot (Python)
- Kittu Bot (Python)
- Zyra UserBot (Telethon)
- KanhaMusic (Go voice-chat engine)

**Important:** this is a deployment package, not a self-contained copy of all four
source repositories. The Docker build needs network access to GitHub and downloads
the pinned source revisions listed below.

## Upload and deploy

1. Extract this ZIP.
2. Upload the files and folders inside it to the root of your `Sem-all-in-1` GitHub repo.
3. In Render, create one **Web Service** connected to that repo, using Docker.
4. Add the required environment variables in Render.
5. Deploy, then check `https://YOUR-RENDER-URL/health`.

Do not upload real tokens, API hashes, database passwords, session strings, or
encryption keys to GitHub. Enter them only in Render Environment settings.

## Required environment variables

| Variable | Purpose |
|---|---|
| `OWNER_ID` | Telegram numeric owner ID |
| `ABOUT_BOT_TOKEN` | About Bot token |
| `ABOUT_MONGODB_URI` | About Bot MongoDB URI (optional if its local persistence is acceptable) |
| `KITTU_BOT_TOKEN` | Kittu Bot token |
| `KITTU_MONGO_URI` | Kittu MongoDB URI |
| `ZYRA_BOT_TOKEN` | Zyra control bot token |
| `ZYRA_API_ID` | Telegram API ID |
| `ZYRA_API_HASH` | Telegram API hash |
| `ZYRA_MONGO_URL` | Zyra MongoDB URI |
| `ZYRA_SESSION_KEY` | Fernet key used by Zyra to encrypt session data |
| `KANHA_TOKEN` | KanhaMusic bot token |
| `KANHA_API_ID` | Telegram API ID |
| `KANHA_API_HASH` | Telegram API hash |
| `KANHA_MONGO_DB_URI` | KanhaMusic MongoDB URI |
| `KANHA_STRING_SESSIONS` | Kanha assistant session string(s) |

Optional variables are listed in `.env.example`. Variables for each bot are
prefixed so the separate projects do not overwrite one another.

Generate a new Zyra Fernet key locally using:
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

Keep the key private and stable. Do not paste it into this chat or commit it.

## Process layout

- Render public health endpoint: port `PORT` (normally 10000)
- About Bot internal web endpoint: 10001
- Kittu health endpoint: 10002
- Zyra internal web endpoint: 10003
- KanhaMusic process: independently supervised

The supervisor restarts a child process if it exits. This is not a guarantee that
the bots will never lag or crash. `/health` reports process status, not successful
Telegram API calls or voice-chat playback.

## Kittu plugin scope

Some casino/betting, bomb, shop, economy, and game modules are excluded from this
combined image. The remaining moderation, utility, and community plugins are
loaded from the source repository.

## Source revisions

- About Bot: `dea5f0b6c6288e5a945ddea8a435c9b63926a3fe`
- Kittu Bot: `9a5d369e14b3c6b85cc6c9e48117d77c5503d58b`
- Zyra UserBot: `e118ecac8d86350bee439d6e2dd4cbbf7428464f`
- KanhaMusic: `06eb5785dbd68dfc40769ee8843ecc42039f29fb`

## First build warning

The Docker image has not been built or run in this environment. The first Render
deployment is a build test. KanhaMusic uses Go, CGO, native libraries and voice-chat
dependencies; it may exceed Render Free CPU/RAM limits. Render Free services can
sleep, so this arrangement does not provide guaranteed 24/7 operation.
