import { Orb } from "./orb";

const orb = new Orb();
const status = document.getElementById("status")!;
const log = document.getElementById("log")!;
const micBtn = document.getElementById("mic")! as HTMLButtonElement;
const term = document.getElementById("term")!;

let ws: WebSocket | null = null;

function connect() {
  ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  ws.binaryType = "arraybuffer";
  ws.onmessage = async (ev) => {
    if (typeof ev.data === "string") {
      const msg = JSON.parse(ev.data);
      if (msg.type === "log") {
        term.textContent += msg.msg + "\n";
        term.scrollTop = term.scrollHeight;
      } else if (msg.type === "status") {
        if (msg.level === "warn") {
          document.body.style.background = "#3a2200";
          status.style.color = "#ffaa00";
          log.innerHTML += `<div style="color:#ffaa00">⚠ ${msg.msg}</div>`;
        } else if (msg.level === "error") {
          document.body.style.background = "#3a0000";
          status.style.color = "#ff4444";
          log.innerHTML += `<div style="color:#ff4444">✖ ${msg.msg}</div>`;
        } else {
          document.body.style.background = "#04070f";
          status.style.color = "#9fd8ff";
        }
      } else if (msg.type === "text") {
        log.innerHTML += `<div><b>JARVIS:</b> ${msg.text}</div>`;
        status.textContent = msg.text;
      }
    } else {
      const ctx = new AudioContext();
      const blob = new Blob([ev.data], { type: "audio/mpeg" });
      const buf = await ctx.decodeAudioData(await blob.arrayBuffer());
      const src = ctx.createBufferSource();
      src.buffer = buf;
      orb.setSource(src, ctx);
      src.connect(ctx.destination);
      src.start();
    }
  };
  ws.onclose = () => setTimeout(connect, 2000);
}
connect();

const Recognition =
  (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

if (!Recognition) {
  status.textContent = "Speech recognition not supported — use Chrome.";
} else {
  const rec = new Recognition();
  rec.lang = "en-US";
  rec.onresult = (ev: any) => {
    const text = ev.results[0][0].transcript.trim();
    log.innerHTML += `<div><b>You:</b> ${text}</div>`;
    status.textContent = "JARVIS is thinking...";
    ws?.send(JSON.stringify({ text }));
  };
  micBtn.onclick = () => {
    status.textContent = "Listening...";
    rec.start();
  };
}
