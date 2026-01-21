let isRecording = false;

chrome.action.onClicked.addListener(async (tab) => {
  if (isRecording) {
    console.log("Stopping recording...");
    chrome.runtime.sendMessage({ type: "STOP_RECORDING" });
    isRecording = false;
    chrome.action.setBadgeText({ text: "" });
    return;
  }

  console.log("Starting recording...");

  // 1. Create the offscreen document (if it doesn't exist)
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

  // 2. Get the Stream ID for the *target* tab (the one the user clicked)
  const streamId = await chrome.tabCapture.getMediaStreamId({
    targetTabId: tab.id,
  });

  // 3. Send the Stream ID to the offscreen document to start processing
  chrome.runtime.sendMessage({
    type: "START_RECORDING",
    data: streamId,
  });

  isRecording = true;
  chrome.action.setBadgeText({ text: "REC" });
  chrome.action.setBadgeBackgroundColor({ color: "#FF0000" });
});
