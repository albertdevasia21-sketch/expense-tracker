"""A tiny local stand-in for a text-to-video website, for testing the browser assistant.

It mimics the parts the assistant relies on: a contenteditable prompt box, a
Send button, a <video> that appears after a delay, and a Download button.
Modes (per prompt text): a prompt containing LIMIT shows a usage-limit message,
DUPLICATE returns the previous video again, BROKEN returns a truncated file.
"""
from __future__ import annotations

import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PAGE = """<!doctype html><meta charset="utf-8"><title>Mock video tool</title>
<body style="font-family:sans-serif">
<button aria-label="New chat" onclick="location.reload()">New chat</button>
<div id="log"></div>
<div id="box" role="textbox" contenteditable="true"
     style="border:1px solid #888;min-height:2em;width:600px"></div>
<button id="send" aria-label="Send message">Send</button>
<script>
let n = 0;
document.getElementById('send').onclick = async () => {
  const box = document.getElementById('box'), log = document.getElementById('log');
  const prompt = box.innerText; box.innerText = '';
  const r = await (await fetch('/generate', {method: 'POST', body: prompt})).json();
  setTimeout(() => {
    if (r.error) { log.insertAdjacentHTML('beforeend', '<p>' + r.error + '</p>'); return; }
    n++;
    log.insertAdjacentHTML('beforeend',
      '<div><video src="' + r.url + '" width="320" muted></video>' +
      '<a id="a' + n + '" href="' + r.url + '" download="generated_video.mp4"></a>' +
      '<button aria-label="Download video" onclick="document.getElementById(\\'a' + n + '\\').click()">' +
      'Download</button></div>');
  }, 1500);
};
</script>"""


def make_clips(folder: Path, count: int = 4) -> list[Path]:
    out = []
    for k in range(count):
        p = folder / f"gen{k}.mp4"
        if not p.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                            f"testsrc2=s=320x180:r=24,hue=h={k * 70}", "-t", "4", "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", str(p)], check=True)
        out.append(p)
    return out


def serve(folder: Path, port: int = 0):
    files = make_clips(folder)
    state = {"n": 0, "prompts": []}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/clip/"):
                name = self.path.split("/")[-1].split("?")[0]
                data = (folder / name.replace("broken_", "")).read_bytes()
                if name.startswith("broken_"):
                    data = data[: len(data) // 3]
                return self._send(200, data, "video/mp4")
            self._send(200, PAGE.encode(), "text/html")

        def do_POST(self):
            prompt = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
            state["prompts"].append(prompt)
            if "LIMIT" in prompt:
                body = '{"error": "You have reached your daily limit for video generation. Try again tomorrow."}'
            else:
                if "DUPLICATE" not in prompt:
                    state["n"] += 1
                f = files[(state["n"] - 1) % len(files)].name
                body = '{"url": "/clip/%s%s"}' % ("broken_" if "BROKEN" in prompt else "", f)
            self._send(200, body.encode(), "application/json")

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, state
