let overlay = null;
let hideTimeout = null;

function createOverlay() {
    let existing = document.getElementById('linguastream-overlay');
    if (existing) return existing;

    overlay = document.createElement('div');
    overlay.id = 'linguastream-overlay';
    overlay.classList.add('hidden');
    
    const textContainer = document.createElement('div');
    textContainer.className = 'linguastream-text';
    overlay.appendChild(textContainer);

    document.body.appendChild(overlay);
    console.log("LinguaStream Overlay Injected");
    
    // TEST: Show briefly on load to prove it works
    overlay.classList.remove('hidden');
    textContainer.innerText = "LinguaStream Ready";
    setTimeout(() => {
        overlay.classList.add('hidden');
    }, 3000);

    return overlay;
}

let duckTimeout = null;
const ORIGINAL_VOLUMES = new Map();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log("LinguaStream Content Script received message:", message.type, message.data);
    if (message.type === 'SHOW_TRANSCRIPT') {
        if (!overlay) {
            console.log("Overlay missing, creating now...");
            overlay = createOverlay();
        }
        const { text, is_final } = message.data;
        updateOverlay(text, is_final);
    } else if (message.type === 'DUCK_AUDIO') {
        duckAudio();
    }
});

function duckAudio() {
    const mediaElements = document.querySelectorAll('video, audio');
    mediaElements.forEach(el => {
        // Store original volume if not already ducked
        if (!ORIGINAL_VOLUMES.has(el)) {
            ORIGINAL_VOLUMES.set(el, el.volume);
        }
        el.volume = 0.2;
    });

    if (duckTimeout) clearTimeout(duckTimeout);
    duckTimeout = setTimeout(() => {
        mediaElements.forEach(el => {
            if (ORIGINAL_VOLUMES.has(el)) {
                el.volume = ORIGINAL_VOLUMES.get(el);
                ORIGINAL_VOLUMES.delete(el);
            }
        });
    }, 2000); // Reset volume after 2 seconds of no audio playing
}

function updateOverlay(text, isFinal) {
    if (!overlay) {
        overlay = createOverlay();
    }

    const textContainer = overlay.querySelector('.linguastream-text');
    if (!textContainer) return;

    overlay.classList.remove('hidden');
    
    // Create or update text segment
    textContainer.innerHTML = `<span class="${isFinal ? 'linguastream-final' : 'linguastream-partial'}">${text}</span>`;

    // Auto-hide after inactivity
    if (hideTimeout) clearTimeout(hideTimeout);
    hideTimeout = setTimeout(() => {
        overlay.classList.add('hidden');
    }, 5000);
}

// Initial creation attempt
if (document.readyState === 'complete') {
    createOverlay();
} else {
    window.addEventListener('load', createOverlay);
}
