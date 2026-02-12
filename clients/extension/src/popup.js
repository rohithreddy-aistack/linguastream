const recordBtn = document.getElementById("record-btn");
const statusIndicator = document.getElementById("status-indicator");
const statusText = document.getElementById("status-text");
const loopbackToggle = document.getElementById("loopbackToggle");
const languageSelect = document.getElementById("language-select");

// Load saved state
chrome.storage.local.get(["isLoopback", "targetLanguage"], (result) => {
  if (result.isLoopback !== undefined) {
    loopbackToggle.checked = result.isLoopback;
  }
  if (result.targetLanguage) {
    languageSelect.value = result.targetLanguage;
  }
});

// Request current state on popup open
chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
  if (response) {
    updateUI(response.isRecording, response.connectionStatus, response.isLoopback);
  }
});

// Listen for status updates from background
chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "STATUS_UPDATE") {
    updateUI(message.isRecording, message.connectionStatus, message.isLoopback);
  }
});

recordBtn.addEventListener("click", () => {
  console.log("Record button clicked"); // DEBUG LOG
  const targetLanguage = languageSelect.value;
  chrome.storage.local.set({ targetLanguage: targetLanguage }); // Save selection
  
  chrome.runtime.sendMessage({ 
    type: "TOGGLE_RECORDING",
    targetLanguage: targetLanguage
  });
});

loopbackToggle.addEventListener("change", (e) => {
  const isLoopback = e.target.checked;
  chrome.storage.local.set({ isLoopback });
  chrome.runtime.sendMessage({ type: "SET_LOOPBACK", value: isLoopback });
});

function updateUI(isRecording, connectionStatus, isLoopback) {
  // Update Button
  if (isRecording) {
    recordBtn.textContent = "Stop Recording";
    recordBtn.classList.add('stop');
    languageSelect.disabled = true; // Lock language while recording
  } else {
    recordBtn.textContent = "Start Recording";
    recordBtn.classList.remove('stop');
    languageSelect.disabled = false;
  }

  // Update Loopback Toggle
  loopbackToggle.checked = isLoopback;
  loopbackToggle.disabled = isRecording;

  // Update Status Indicator
  statusIndicator.className = 'status-indicator';
  if (connectionStatus === 'connected') {
    statusIndicator.classList.add('connected');
    statusText.textContent = 'Connected';
  } else if (connectionStatus === 'error') {
    statusIndicator.classList.add('error');
    statusText.textContent = 'Connection Error';
  } else {
    statusText.textContent = 'Disconnected';
  }
}
