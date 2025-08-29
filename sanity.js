// sanity.js
import express from "express";
import fs from "fs";
import { execSync } from "child_process";
import path from "path";
import url from "url";

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const PORT = 4000;
const AUDIO = path.join(__dirname, "sanity.mp3");

// 1) Generera 1s 880 Hz ton som *korrekt* 128 kbps CBR (LAME)
if (!fs.existsSync(AUDIO)) {
  const cmd = `ffmpeg -hide_banner -loglevel error \
    -f lavfi -t 1 -i "sine=frequency=880:sample_rate=44100" \
    -ar 44100 -ac 1 -c:a libmp3lame -b:a 128k -write_xing 0 \
    -y "${AUDIO}"`;
  execSync(cmd, { stdio: "inherit" });
  console.log("✓ Generated sanity.mp3 (128 kbps CBR, 44.1 kHz, mono)");
}

// 2) Liten server med HEAD + Range
const app = express();

app.get("/test", (_req, res) => {
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.end(`<!doctype html>
<html>
<head><meta charset="utf-8"><title>Audio Sanity</title></head>
<body style="font-family:system-ui;margin:40px">
  <h1>Audio Sanity Test</h1>
  <button id="play">▶️ Play</button>
  <pre id="log"></pre>
  <audio id="a" src="/audio/sanity.mp3" preload="auto"></audio>
  <script>
    const a = document.getElementById('a');
    const log = (m) => { const t = new Date().toISOString().split('T')[1].split('.')[0];
      document.getElementById('log').textContent += '['+t+'] '+m+'\\n'; console.log(m); };
    ['loadstart','loadedmetadata','canplay','playing','timeupdate','ended','error','stalled']
      .forEach(ev => a.addEventListener(ev, () => log('audio:'+ev)));
    document.getElementById('play').onclick = () => { a.currentTime = 0; a.play(); };

    // Verifiera HEAD
    fetch('/audio/sanity.mp3', { method: 'HEAD' }).then(r => {
      log('HEAD status ' + r.status + ' ' + r.statusText);
      log('Content-Type: ' + r.headers.get('content-type'));
      log('Accept-Ranges: ' + r.headers.get('accept-ranges'));
      log('Content-Length: ' + r.headers.get('content-length'));
    });
  </script>
</body></html>`);
});

// HEAD route (Chrome gör ofta HEAD före GET)
app.head("/audio/:name", (req, res) => {
  const file = path.join(__dirname, req.params.name);
  if (!fs.existsSync(file)) return res.sendStatus(404);
  const stat = fs.statSync(file);
  res.set({
    "Content-Type": "audio/mpeg",
    "Accept-Ranges": "bytes",
    "Content-Length": stat.size,
    "Cache-Control": "public, max-age=31536000, immutable",
  });
  res.end(); // Use .end() instead of .sendStatus(200)
});

// GET med Range-stöd
app.get("/audio/:name", (req, res) => {
  const file = path.join(__dirname, req.params.name);
  if (!fs.existsSync(file)) return res.sendStatus(404);
  const stat = fs.statSync(file);
  const total = stat.size;

  let start = 0, end = total - 1, status = 200;
  const range = req.headers.range;
  if (range) {
    const m = range.match(/bytes=(\\d+)-(\\d+)?/);
    if (m) {
      start = parseInt(m[1], 10);
      end = m[2] ? parseInt(m[2], 10) : end;
      status = 206;
      res.setHeader("Content-Range", `bytes ${start}-${end}/${total}`);
    }
  }

  res.status(status).set({
    "Content-Type": "audio/mpeg",
    "Accept-Ranges": "bytes",
    "Content-Length": end - start + 1,
    "Cache-Control": "public, max-age=31536000, immutable",
  });

  fs.createReadStream(file, { start, end }).pipe(res);
});

app.listen(PORT, () =>
  console.log(`✓ Sanity server on http://localhost:${PORT}/test`)
);