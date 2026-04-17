import { showToast } from './toasts.js';

const recordButton = document.getElementById("record_button");
const recordStatus = document.getElementById("record_status");
const mainCnt = document.getElementById("mainContainer");

let mediaRecorder;
let chunks = [];
let isRecording = false;


const params = new URLSearchParams(window.location.search);
const room = params.get("room") || "101";

document.getElementById("room_number").textContent =
  `Welcome back, Room nr. ${room}`;


const socket = new WebSocket(`ws://${window.location.host}/ws?room=${room}`);

socket.onopen = () => {
  console.log("WS connected:", room);
};

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "status_update") {
    renderRequest(data.payload);
  }
};

socket.onclose = () => console.log("WS disconnected");
socket.onerror = (err) => console.error("WS error", err);


function updateStatus(text) {
  recordStatus.textContent = text;

  recordStatus.classList.remove("idle", "recording", "processing");

  if (text === "Idle") {
    recordStatus.classList.add("idle");
  } else if (text === "Recording...") {
    recordStatus.classList.add("recording");
  } else {
    recordStatus.classList.add("processing");
  }
}

function renderRequest(payload) {
  const existing = document.getElementById("request-something");
  if (existing) existing.remove();

  const wrapper = document.createElement("div");
  wrapper.id = "request-something";

  wrapper.innerHTML = `
  <div class="container requestHistory">
    <div class="container bg-accent gap-sm">

      <h2 class="text-3xl font-display text-center">
        CURRENT ORDER
      </h2>

      <div class="container bg-bright">
        <h3>REQUEST</h3>
        <p>${payload.text}</p>
      </div>

      <div class="container bg-bright">
        <h3>STATUS</h3>
        <p>${payload.status}</p>
      </div>

      <div class="container bg-bright">
        <h3>ETA</h3>
        <p>${payload.eta || "-"}</p>
      </div>

    </div>
  </div>
  `;

  mainCnt.appendChild(wrapper);
}

async function ensureRecorder() {
  if (mediaRecorder) return;

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

  mediaRecorder = new MediaRecorder(stream);

  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) chunks.push(event.data);
  };

  mediaRecorder.onstop = async () => {
    const blob = new Blob(chunks, { type: "audio/webm" });
    chunks = [];
    await sendAudio(blob);
  };
}

async function sendAudio(blob) {
  updateStatus("Transcribing...");

  const form = new FormData();
  form.append("files", blob, "recording.webm");
  form.append("room", room);

  try {
    const response = await fetch("/api/voice_to_text", {
      method: "POST",
      body: form,
    });

    if (!response.ok) throw new Error("Server error");

    const payload = await response.json();

    renderRequest(payload);

    updateStatus("Idle");

  } catch (err) {
    console.error(err);
    showToast({ message: 'Transcription failed', type: 'failure' });
  }
}

const voiceBox = document.getElementById("voice_box");

recordButton.addEventListener("click", async () => {
  try {
    await ensureRecorder();
  } catch (error) {
    console.error(error);
    return;
  }

  if (!isRecording) {
    isRecording = true;
    updateStatus("Recording...");
    mediaRecorder.start();
    voiceBox.classList.add("recording");
    return;
  }

  isRecording = false;
  updateStatus("Stopping...");
  mediaRecorder.stop();
  voiceBox.classList.remove("recording");
});

updateStatus("Idle");