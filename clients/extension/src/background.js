let isRecording = false;
let isLoopback = false;
let connectionStatus = 'disconnected'; // 'disconnected', 'connected', 'error'

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_STATUS") {
    sendResponse({ isRecording, connectionStatus, isLoopback });
  } 
  
  else if (message.type === "TOGGLE_RECORDING") {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording(message.targetLanguage);
    }
  }

  else if (message.type === "SET_LOOPBACK") {
    isLoopback = message.value;
    broadcastStatus();
  }

  else if (message.type === "WS_STATUS") {
    connectionStatus = message.status;
    broadcastStatus();
  }

  else if (message.type === "AUDIO_PLAYING") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, { type: "DUCK_AUDIO" }).catch(() => {});
      }
    });
  }

  else if (message.type === "TRANSCRIPT") {
    console.log("Background received transcript:", message.data);
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        console.log("Forwarding transcript to tab:", tabs[0].id, "Text:", message.data.text);
        chrome.tabs.sendMessage(tabs[0].id, { type: "SHOW_TRANSCRIPT", data: message.data }).catch((e) => {
          console.error("Could not send to tab:", e);
        });
      } else {
        console.warn("No active tab found to send transcript.");
      }
    });
  }
});

async function startRecording(targetLanguage) {
  console.log("Starting recording...", targetLanguage);
  
  // 1. Create the offscreen document
  const existingContexts = await chrome.runtime.getContexts({});
  const offscreenDocument = existingContexts.find(
    (c) => c.contextType === "OFFSCREEN_DOCUMENT",
  );

  if (!offscreenDocument) {
    await chrome.offscreen.createDocument({
      url: "src/offscreen.html",
      reasons: ["USER_MEDIA"],
      justification: "Recording tab audio for translation",
    });
  }

  // 2. Get the current active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  // 3. Get the Stream ID
  const streamId = await chrome.tabCapture.getMediaStreamId({
    targetTabId: tab.id,
  });

  // 4. Send to offscreen
  chrome.runtime.sendMessage({
    type: "START_RECORDING",
    data: streamId,
    isLoopback: isLoopback,
    targetLanguage: targetLanguage || "hi-IN" // Default to Hindi
  });

  isRecording = true;
  chrome.action.setBadgeText({ text: "REC" });
  chrome.action.setBadgeBackgroundColor({ color: "#FF0000" });
  broadcastStatus();
}

function stopRecording() {
  console.log("Stopping recording...");
  chrome.runtime.sendMessage({ type: "STOP_RECORDING" });
  isRecording = false;
  connectionStatus = 'disconnected';
  chrome.action.setBadgeText({ text: "" });
  broadcastStatus();
}

function broadcastStatus() {
  chrome.runtime.sendMessage({
    type: "STATUS_UPDATE",
    isRecording,
    connectionStatus,
    isLoopback
  }).catch(() => {
    // Ignore error if popup is closed
  });
}
