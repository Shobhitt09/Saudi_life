import requests
import pytest
import json
import time
import os

BASE_URL = "http://0.0.0.0:8000"
headers = {"Content-Type": "application/json"}

# Load sample audio base64 content
audio_path = "test/example.wav.base64"
audio_data = None
if os.path.exists(audio_path):
    with open(audio_path, "r") as f:
        audio_data = f.read()

queries = [
    # Hindi
    "सऊदी अरब में यात्रा के लिए वीज़ा कैसे प्राप्त करें?",
    "क्या सऊदी अरब में महिलाओं के लिए कोई विशेष ड्रेस कोड है?",
    "रियाद में सबसे अच्छे भारतीय रेस्तरां कौन से हैं?",
    # Malayalam
    "സൗദി അറേബ്യയിലേക്ക് യാത്ര ചെയ്യാൻ വീസ എങ്ങനെ ലഭിക്കും?",
    "സൗദിയിൽ സ്ത്രീകൾക്ക് പ്രത്യേകമായ വസ്ത്രധാരണമുണ്ടോ?",
    "റിയാദിലെ മികച്ച ഇന്ത്യൻ റസ്റ്റോറന്റുകൾ ഏവയാണ്?",
    # English
    "How to obtain a visa for traveling to Saudi Arabia?",
    "Is there a specific dress code for women in Saudi Arabia?",
    "What are the best Indian restaurants in Riyadh?"
]

def test_health_check():
    response = requests.get(f"{BASE_URL}/health/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert data.get("message") == "Service is running"

@pytest.mark.parametrize("query", queries)
def test_query_only(query):
    payload = {"name": "Test User", "query": query, "audio": None}
    response = requests.post(f"{BASE_URL}/process/", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert not data.get("error"), f"Query failed: {query}, Error: {data.get('error')}"

@pytest.mark.skipif(audio_data is None, reason="No audio file available")
def test_audio_only():
    payload = {"query": None, "audio": audio_data}
    response = requests.post(f"{BASE_URL}/process/", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert not data.get("error"), f"Audio input failed: {data.get('error')}"

def test_empty_input():
    payload = {"query": "", "audio": None}
    response = requests.post(f"{BASE_URL}/process/", json=payload, headers=headers)
    assert response.status_code == 200
    err = response.json().get("response", {}).get("error")
    assert err == "Query cannot be empty", f"Expected error for empty query, got: {err}"