let socket = null;
let mediaStream = null;
let audioContext = null; // 44.1k for capture
let playbackContext = null; // 16k for TTS playback
let processor = null;

chrome.runtime.onMessage.addListener(async (message) => {
  if (message.type === "START_RECORDING") {
    startCapture(message.data, message.isLoopback, message.targetLanguage);
  } else if (message.type === "STOP_RECORDING") {
    stopCapture();
  }
});

async function startCapture(streamId, isLoopback, targetLanguage) {
  const endpoint = isLoopback 
    ? "ws://127.0.0.1:8000/ws/loopback" 
    : `ws://127.0.0.1:8000/ws/stream?lang=${targetLanguage || 'hi-IN'}`;
  
  socket = new WebSocket(endpoint);
  socket.binaryType = "arraybuffer";

  socket.onopen = async () => {
    console.log(`Connected to Python Server (${isLoopback ? 'Loopback' : 'Stream'})`);
    chrome.runtime.sendMessage({ type: "WS_STATUS", status: "connected" });

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          mandatory: {
            chromeMediaSource: "tab",
            chromeMediaSourceId: streamId,
          },
        },
        video: false,
      });

      audioContext = new AudioContext({ sampleRate: 44100 });
      playbackContext = new AudioContext({ sampleRate: 16000 }); // Dedicated for TTS
      
      const source = audioContext.createMediaStreamSource(mediaStream);

      processor = audioContext.createScriptProcessor(4096, 1, 1);
      source.connect(processor);
      
      // Keep original audio playing
      processor.connect(audioContext.destination);

      let chunkCount = 0;
      processor.onaudioprocess = (e) => {
        if (socket.readyState === WebSocket.OPEN) {
          const inputData = e.inputBuffer.getChannelData(0);
          
          if (chunkCount % 100 === 0) {
            const maxVal = Math.max(...inputData);
            console.log(`Sending audio chunk ${chunkCount}, max amplitude: ${maxVal}`);
          }
          chunkCount++;

          const pcmData = convertFloat32ToInt16(inputData);
          socket.send(pcmData);
        }
      };

      socket.onmessage = (event) => {
        if (typeof event.data === "string") {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "transcript") {
              chrome.runtime.sendMessage({ type: "TRANSCRIPT", data: data });
            }
          } catch (e) {
            console.error("Error parsing socket message:", e);
          }
        } else if (event.data instanceof ArrayBuffer) {
          // Play any binary data received (TTS Chunks)
          playBuffer(event.data);
        }
      };
    } catch (err) {
      console.error("Error starting tab capture:", err);
      chrome.runtime.sendMessage({ type: "WS_STATUS", status: "error" });
    }
  };

  socket.onclose = () => {
    chrome.runtime.sendMessage({ type: "WS_STATUS", status: "disconnected" });
  };

  socket.onerror = (err) => {
    chrome.runtime.sendMessage({ type: "WS_STATUS", status: "error" });
  };
}

let nextStartTime = 0;

function playBuffer(arrayBuffer) {
  if (!playbackContext) return;
  
  // Notify background that audio is playing (for ducking)
  chrome.runtime.sendMessage({ type: "AUDIO_PLAYING" });
  
  const pcmData = new Int16Array(arrayBuffer);
  const float32Data = new Float32Array(pcmData.length);
  for (let i = 0; i < pcmData.length; i++) {
    float32Data[i] = pcmData[i] / 0x7fff;
  }

  const audioBuffer = playbackContext.createBuffer(1, float32Data.length, 16000);
  audioBuffer.getChannelData(0).set(float32Data);
  
  const source = playbackContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(playbackContext.destination);

  // Scheduling for gapless playback
  const currentTime = playbackContext.currentTime;
  if (nextStartTime < currentTime) {
    nextStartTime = currentTime;
  }
  
  source.start(nextStartTime);
  nextStartTime += audioBuffer.duration;
}

function stopCapture() {
  if (socket) {
    socket.close();
    socket = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  if (processor) {
    processor.disconnect();
    processor = null;
  }
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }
  if (playbackContext) {
    playbackContext.close();
    playbackContext = null;
  }
  nextStartTime = 0;
}

function convertFloat32ToInt16(buffer) {
  let l = buffer.length;
  let buf = new Int16Array(l);
  while (l--) {
    buf[l] = Math.min(1, Math.max(-1, buffer[l])) * 0x7fff;
  }
  return buf.buffer;
}
