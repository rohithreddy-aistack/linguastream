let socket = null;
let mediaStream = null;
let audioContext = null;
let processor = null;

chrome.runtime.onMessage.addListener(async (message) => {
  if (message.type === "START_RECORDING") {
    startCapture(message.data);
  } else if (message.type === "STOP_RECORDING") {
    stopCapture();
  }
});

async function startCapture(streamId) {
  // 1. Connect to Python Backend
  socket = new WebSocket("ws://127.0.0.1:8000/ws/stream");

  socket.onopen = async () => {
    console.log("Connected to Python Server");

    try {
      // 2. Capture the Media Stream using the ID passed from background.js
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          mandatory: {
            chromeMediaSource: "tab",
            chromeMediaSourceId: streamId,
          },
        },
        video: false,
      });

      // 3. Process Audio (Web Audio API)
      audioContext = new AudioContext({ sampleRate: 44100 });
      const source = audioContext.createMediaStreamSource(mediaStream);

      // We use a ScriptProcessor to access raw audio buffers
      // Buffer size 4096 = ~92ms of audio
      processor = audioContext.createScriptProcessor(4096, 1, 1);

      source.connect(processor);
      processor.connect(audioContext.destination); // Play audio to speakers too

      processor.onaudioprocess = (e) => {
        if (socket.readyState === WebSocket.OPEN) {
          const inputData = e.inputBuffer.getChannelData(0); // Float32 Array (-1.0 to 1.0)

          // Convert Float32 to Int16 (PCM) for Python
          const pcmData = convertFloat32ToInt16(inputData);
          socket.send(pcmData);
        }
      };
    } catch (err) {
      console.error("Error starting tab capture:", err);
    }
  };
}

function stopCapture() {
  if (socket) socket.close();
  if (mediaStream) mediaStream.getTracks().forEach((t) => t.stop());
  if (processor) processor.disconnect();
  if (audioContext) audioContext.close();
}

// Helper: Convert raw Float32 audio to Int16
function convertFloat32ToInt16(buffer) {
  let l = buffer.length;
  let buf = new Int16Array(l);
  while (l--) {
    buf[l] = Math.min(1, Math.max(-1, buffer[l])) * 0x7fff;
  }
  return buf.buffer;
}
