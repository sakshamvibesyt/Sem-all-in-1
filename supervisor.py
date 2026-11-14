#!/usr/bin/env python3
"""Run four separate Telegram services inside one Render Web Service."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

ROOT = Path("/opt/bots")
STOP = threading.Event()
CHILDREN: list["Child"] = []


@dataclass
class Child:
    name: str
    command: list[str]
    cwd: Path
    required: tuple[str, ...]
    env_map: dict[str, str]
    port: int
    process: Optional[subprocess.Popen] = None
    missing: list[str] = field(default_factory=list)
    restarts: int = 0
    next_start: float = 0.0
    last_exit: Optional[int] = None

    def child_env(self) -> dict[str, str]:
        env = os.environ.copy()
        for source, target in self.env_map.items():
            value = os.environ.get(source, "")
            if value:
                env[target] = value
        env["PORT"] = str(self.port)
        env["PYTHONUNBUFFERED"] = "1"
        return env

    def validate(self) -> bool:
        self.missing = [
            key for key in self.required
            if not os.environ.get(key, "").strip()
        ]
        return not self.missing

    def start(self) -> None:
        if not self.validate():
            print(
                f"[supervisor] {self.name}: waiting for environment variables: "
                f"{', '.join(self.missing)}",
                flush=True,
            )
            return
        print(f"[supervisor] starting {self.name}", flush=True)
        self.process = subprocess.Popen(
            self.command,
            cwd=str(self.cwd),
            env=self.child_env(),
            stdin=subprocess.DEVNULL,
            stdout=None,
            stderr=None,
            start_new_session=True,
        )

    def stop(self) -> None:
        if not self.process or self.process.poll() is not None:
            return
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
            self.process.wait(timeout=15)
        except Exception:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except Exception:
                pass


def build_children() -> list[Child]:
    return [
        Child(
            "about-bot",
            ["/opt/venvs/about/bin/python", "bot.py"],
            ROOT / "about",
            ("ABOUT_BOT_TOKEN", "OWNER_ID"),
            {
                "ABOUT_BOT_TOKEN": "BOT_TOKEN",
                "ABOUT_MONGODB_URI": "MONGODB_URI",
                "ABOUT_MONGODB_DB": "MONGODB_DB",
                "ABOUT_OPENAI_API_KEY": "OPENAI_API_KEY",
                "ABOUT_TMDB_API_KEY": "TMDB_API_KEY",
            },
            10001,
        ),
        Child(
            "kittu-bot",
            ["/opt/venvs/kittu/bin/python", "run.py"],
            ROOT / "kittu",
            ("KITTU_BOT_TOKEN", "OWNER_ID", "KITTU_MONGO_URI"),
            {
                "KITTU_BOT_TOKEN": "BOT_TOKEN",
                "KITTU_MONGO_URI": "MONGO_URI",
                "KITTU_DATABASE_NAME": "DATABASE_NAME",
                "KITTU_WAIFU_DB_NAME": "WAIFU_DB_NAME",
                "KITTU_LOGGER_ID": "LOGGER_ID",
                "KITTU_GROQ_API_KEY": "GROQ_API_KEY",
                "KITTU_MISTRAL_API_KEY": "MISTRAL_API_KEY",
                "KITTU_OPENAI_API_KEY": "OPENAI_API_KEY",
                "KITTU_NVIDIA_API_KEY": "NVIDIA_API_KEY",
                "KITTU_YUKI_API_KEY": "YUKI_API_KEY",
            },
            10002,
        ),
        Child(
            "zyra-userbot",
            ["/opt/venvs/zyra/bin/python", "main.py"],
            ROOT / "zyra",
            (
                "ZYRA_BOT_TOKEN",
                "ZYRA_API_ID",
                "ZYRA_API_HASH",
                "ZYRA_MONGO_URL",
                "ZYRA_SESSION_KEY",
            ),
            {
                "ZYRA_BOT_TOKEN": "BOT_TOKEN",
                "ZYRA_API_ID": "API_ID",
                "ZYRA_API_HASH": "API_HASH",
                "ZYRA_MONGO_URL": "MONGO_URL",
                "ZYRA_SESSION_KEY": "SESSION_KEY",
                "ZYRA_DB_NAME": "DB_NAME",
                "ZYRA_LOGGER_GROUP_ID": "LOGGER_GROUP_ID",
                "ZYRA_MAX_USERS": "MAX_USERS",
                "ZYRA_OWNER_URL": "OWNER_URL",
                "ZYRA_SUPPORT_URL": "SUPPORT_URL",
            },
            10003,
        ),
        Child(
            "kanha-music",
            [str(ROOT / "kanha" / "app")],
            ROOT / "kanha",
            (
                "KANHA_TOKEN",
                "KANHA_API_ID",
                "KANHA_API_HASH",
                "KANHA_MONGO_DB_URI",
                "KANHA_STRING_SESSIONS",
                "OWNER_ID",
            ),
            {
                "KANHA_TOKEN": "TOKEN",
                "KANHA_API_ID": "API_ID",
                "KANHA_API_HASH": "API_HASH",
                "KANHA_MONGO_DB_URI": "MONGO_DB_URI",
                "KANHA_STRING_SESSIONS": "STRING_SESSIONS",
                "KANHA_DB_NAME": "DB_NAME",
                "KANHA_LOGGER_ID": "LOGGER_ID",
                "KANHA_OWNER_USERNAME": "OWNER_USERNAME",
                "KANHA_SESSION_TYPE": "SESSION_TYPE",
                "KANHA_MEOW_API_KEY": "MEOW_API_KEY",
            },
            10004,
        ),
    ]


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health"):
            self.send_error(404)
            return

        statuses = []
        ready = True
        for child in CHILDREN:
            running = bool(child.process and child.process.poll() is None)
            configured = not child.missing
            if not running or not configured:
                ready = False
            statuses.append({
                "name": child.name,
                "status": (
                    "running" if running
                    else "needs_environment" if not configured
                    else "restarting"
                ),
                "restarts": child.restarts,
                "exit_code": child.last_exit,
                "missing_env": child.missing,
            })

        body = json.dumps({
            "service": "Sem All In One",
            "ready": ready,
            "bots": statuses,
        }).encode()
        self.send_response(200 if ready else 503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[health] " + fmt % args, flush=True)


def start_health_server() -> ThreadingHTTPServer:
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"[supervisor] health endpoint listening on port {port}", flush=True)
    return server


def monitor() -> None:
    while not STOP.is_set():
        now = time.monotonic()
        for child in CHILDREN:
            if not child.validate():
                continue
            if child.process is None:
                if now >= child.next_start:
                    child.start()
                continue

            code = child.process.poll()
            if code is not None:
                child.last_exit = code
                child.process = None
                child.restarts += 1
                delay = min(60, 2 ** min(child.restarts, 6))
                child.next_start = now + delay
                print(
                    f"[supervisor] {child.name} exited ({code}); "
                    f"restart scheduled in {delay}s",
                    flush=True,
                )
        STOP.wait(2)


def shutdown(*_args) -> None:
    if STOP.is_set():
        return
    STOP.set()
    print("[supervisor] stopping child services", flush=True)
    for child in reversed(CHILDREN):
        child.stop()


def main() -> None:
    global CHILDREN
    CHILDREN = build_children()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    server = start_health_server()
    try:
        monitor()
    finally:
        shutdown()
        server.shutdown()


if __name__ == "__main__":
    main()
