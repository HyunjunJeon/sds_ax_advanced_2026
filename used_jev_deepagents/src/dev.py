"""LangGraph API와 공식 Agent Chat UI를 같이 띄운다."""

from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

from src.agent.config import PROJECT_ROOT, load_settings

UI_REPO = "https://github.com/langchain-ai/agent-chat-ui.git"
UI_DIR = PROJECT_ROOT / "frontend"
API_HOST = "127.0.0.1"
API_PORT = 2024
UI_PORT = 3000
ASSISTANT_ID = "agent"


def main(argv: list[str] | None = None) -> int:
    """필요하면 Agent Chat UI를 클론한 뒤 API와 UI를 같이 띄운다."""
    del argv
    settings = load_settings()
    _require_keys(settings)
    pnpm = _pnpm_cmd()
    _ensure_ui(pnpm)

    processes: list[subprocess.Popen[str]] = []

    def _stop(*_args: object) -> None:
        for proc in processes:
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
        for proc in processes:
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()

    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    try:
        langgraph = Path(sys.executable).parent / "langgraph"
        api = subprocess.Popen(
            [
                str(langgraph if langgraph.exists() else "langgraph"),
                "dev",
                "--no-browser",
                "--no-reload",
                "--allow-blocking",
                "--host",
                API_HOST,
                "--port",
                str(API_PORT),
            ],
            cwd=PROJECT_ROOT,
            env=os.environ.copy(),
        )
        processes.append(api)
        _wait_http(f"http://{API_HOST}:{API_PORT}/ok", timeout=90)
        ui_port = _free_port(UI_PORT)
        ui = subprocess.Popen(
            [*pnpm, "dev", "--port", str(ui_port)],
            cwd=UI_DIR,
            env={
                **os.environ,
                "PORT": str(ui_port),
                "NEXT_PUBLIC_API_URL": f"http://{API_HOST}:{API_PORT}",
                "NEXT_PUBLIC_ASSISTANT_ID": ASSISTANT_ID,
            },
        )
        processes.append(ui)
        print()
        print("LangGraph API : http://127.0.0.1:2024")
        print(f"Agent Chat UI : http://localhost:{ui_port}")
        print()
        print("UI Settings (pre-filled via .env)")
        print("  Deployment URL: http://127.0.0.1:2024")
        print("  Assistant ID:   agent     (Jev 판단)")
        print("                   baseline (LLM tool-call 판단)")
        print("                   compare  (둘 다 돌리고 표로 비교)")
        print()
        if getattr(settings, "langfuse_enabled", False):
            print(
                "Langfuse: "
                f"{getattr(settings, 'langfuse_base_url', '')}  "
                "dataset=jev-rag-gold  env="
                f"{getattr(settings, 'langfuse_environment', 'demo')}"
            )
            print()
        print("Ctrl+C to stop both processes.")
        while True:
            for proc in processes:
                code = proc.poll()
                if code is not None:
                    _stop()
                    return code or 1
            time.sleep(0.5)
    finally:
        _stop()


def _require_keys(settings: object) -> None:
    missing: list[str] = []
    if not getattr(settings, "chat_api_key", None):
        missing.append(getattr(settings, "chat_key_name", "ANTHROPIC_API_KEY"))
    if not getattr(settings, "typesafe_api_key", None):
        missing.append("TYPESAFE_API_KEY")
    if missing:
        raise SystemExit(
            "Missing required keys in .env: " + ", ".join(missing)
        )


def _ensure_node_path() -> None:
    """pnpm/npm을 위해 nvm/homebrew Node 바이너리를 PATH에 넣는다."""
    extras: list[Path] = [
        Path.home() / ".local" / "bin",
        Path("/opt/homebrew/bin"),
        Path("/usr/local/bin"),
    ]
    nvm = Path.home() / ".nvm" / "versions" / "node"
    if nvm.exists():
        extras.extend(sorted(nvm.glob("*/bin")))
    prefix = ":".join(str(path) for path in extras if path.exists())
    if prefix:
        os.environ["PATH"] = f"{prefix}:{os.environ.get('PATH', '')}"


def _pnpm_cmd() -> list[str]:
    _ensure_node_path()
    if shutil.which("pnpm"):
        return ["pnpm"]
    npx = shutil.which("npx")
    if npx:
        return [npx, "--yes", "pnpm@10.5.1"]
    raise SystemExit("pnpm or npx is required to start Agent Chat UI.")


def _ensure_ui(pnpm: list[str]) -> None:
    UI_DIR.mkdir(parents=True, exist_ok=True)
    if not (UI_DIR / "package.json").exists():
        clone_dir = UI_DIR / ".clone"
        if clone_dir.exists():
            shutil.rmtree(clone_dir)
        subprocess.run(
            ["git", "clone", "--depth", "1", UI_REPO, str(clone_dir)],
            check=True,
        )
        for item in clone_dir.iterdir():
            dest = UI_DIR / item.name
            if dest.exists() and dest.name in {".env.example", "README.md"}:
                continue
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            shutil.move(str(item), str(dest))
        shutil.rmtree(clone_dir)
        nested_git = UI_DIR / ".git"
        if nested_git.exists():
            shutil.rmtree(nested_git)
    env_path = UI_DIR / ".env"
    if not env_path.exists():
        env_path.write_text(
            "NEXT_PUBLIC_API_URL=http://127.0.0.1:2024\n"
            f"NEXT_PUBLIC_ASSISTANT_ID={ASSISTANT_ID}\n"
            "NEXT_PUBLIC_AUTH_SCHEME=\n",
            encoding="utf-8",
        )
    _patch_frontend()
    if not (UI_DIR / "node_modules").exists():
        subprocess.run([*pnpm, "install"], cwd=UI_DIR, check=True)


def _patch_frontend() -> None:
    """로컬 Next.js 16 + Tailwind 4를 깨는 Agent Chat UI 문제를 고친다."""
    config = UI_DIR / "tailwind.config.js"
    # 업스트림은 CJS인데 패키지가 type:module이라 Tailwind 유틸이 안 나온다.
    if config.exists() and "module.exports" in config.read_text(encoding="utf-8"):
        config.write_text(
            """import tailwindScrollbar from "tailwind-scrollbar";
import tailwindcssAnimate from "tailwindcss-animate";

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
    extend: {
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [tailwindcssAnimate, tailwindScrollbar],
};
""",
            encoding="utf-8",
        )
    css = UI_DIR / "src" / "app" / "globals.css"
    if css.exists():
        text = css.read_text(encoding="utf-8")
        if '@source "../**/*.{ts,tsx,js,jsx}"' not in text:
            text = text.replace(
                '@import "tailwindcss";\n',
                '@import "tailwindcss";\n\n@source "../**/*.{ts,tsx,js,jsx}";\n',
                1,
            )
            css.write_text(text, encoding="utf-8")
    logo = UI_DIR / "src" / "components" / "icons" / "langgraph.tsx"
    if logo.exists():
        text = logo.read_text(encoding="utf-8")
        if "clip-path=" in text:
            logo.write_text(text.replace("clip-path=", "clipPath="), encoding="utf-8")
    next_config = UI_DIR / "next.config.mjs"
    if next_config.exists():
        text = next_config.read_text(encoding="utf-8")
        if "agentRules" not in text:
            text = text.replace(
                "const nextConfig = {\n",
                "const nextConfig = {\n  agentRules: false,\n  devIndicators: false,\n",
                1,
            )
            next_config.write_text(text, encoding="utf-8")


def _free_port(start: int) -> int:
    """``start`` 이상에서 비어 있는 첫 TCP 포트를 고른다."""
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise SystemExit(f"No free UI port in {start}-{start + 19}")


def _wait_http(url: str, timeout: float) -> None:
    deadline = time.time() + timeout
    last_error = "timeout"
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=2.0)
            if 200 <= response.status_code < 500:
                return
            last_error = f"HTTP {response.status_code}"
        except httpx.RequestError as exc:
            last_error = str(exc)
        time.sleep(0.4)
    raise SystemExit(f"LangGraph API did not become ready: {last_error}")


if __name__ == "__main__":
    raise SystemExit(main())
