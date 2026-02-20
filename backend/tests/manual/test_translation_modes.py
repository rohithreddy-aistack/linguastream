import os
import urllib.request
import urllib.parse
import json

api_key = ""
with open(".env", "r") as f:
    for line in f:
        if line.startswith("SARVAM_API_KEY="):
            api_key = line.strip().split("=", 1)[1].strip('"\'')

url = "https://api.sarvam.ai/translate"
headers = {
    "api-subscription-key": api_key,
    "Content-Type": "application/json"
}

def test_translation(mode):
    payload = {
        "input": "This application has an inbuilt compiler.",
        "source_language_code": "en-IN",
        "target_language_code": "te-IN",
        "speaker_gender": "Male",
        "mode": mode,
        "model": "mayura:v1"
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            data = response.read().decode('utf-8')
            res = json.loads(data)
            print(f"[{mode}] Translated: {res.get('translated_text')}")
    except urllib.error.HTTPError as e:
        print(f"[{mode}] Error {e.code}: {e.read().decode('utf-8')[:200]}")

test_translation("formal")
test_translation("casual")
test_translation("code-mixed")
test_translation("mixed")
