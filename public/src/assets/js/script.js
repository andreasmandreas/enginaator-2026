const recordButton = document.getElementById("record_button");
const recordStatus = document.getElementById("record_status");
const languageSelect = document.getElementById("language_select");
const transcriptEl = document.getElementById("transcript");

let mediaRecorder;
let chunks = [];
let isRecording = false;

function updateStatus(text) {
  recordStatus.textContent = text;
}

async function ensureRecorder() {
  if (mediaRecorder) return;
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) {
      chunks.push(event.data);
    }
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
  form.append("audio", blob, "recording.webm");
  const language = languageSelect.value;
  if (language) {
    form.append("language", language);
  }

  const response = await fetch("/api/whisper", {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    updateStatus("Transcription failed");
    transcriptEl.textContent = "";
    return;
  }

  const payload = await response.json();
  const text = (payload.text || "").trim();
  transcriptEl.textContent = text || "(No speech detected)";
  updateStatus("Idle");
}

recordButton.addEventListener("click", async () => {
  try {
    await ensureRecorder();
  } catch (error) {
    updateStatus("Mic permission denied");
    return;
  }

  if (!isRecording) {
    isRecording = true;
    updateStatus("Recording...");
    mediaRecorder.start();
    return;
  }

  isRecording = false;
  updateStatus("Stopping...");
  mediaRecorder.stop();
});

updateStatus("Idle");
