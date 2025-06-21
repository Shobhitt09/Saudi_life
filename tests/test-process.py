import requests
import pytest

BASE_URL = "http://0.0.0.0:8000"
headers = {"Content-Type": "application/json"}

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
def test_valid_queries(query):
    payload = {
        "name": "Test User",
        "query": str(query),
        "audio": None
    }
    response = requests.post(f"{BASE_URL}/process/", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert not data.get("error"), f"Query failed: {query}, Error: {data.get('error')}"

def test_empty_query():
    payload = {
        "query": "",
        "audio": None
    }
    response = requests.post(f"{BASE_URL}/process/", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json().get("response").get("error") == "Query cannot be empty", "Empty query should return an error"

def test_audio_input():
    with open("tests/example.wav.base64", "r") as f:
        audio_data = f.read()

    payload = {
        "query": None,
        "audio": audio_data
    }
    response = requests.post(f"{BASE_URL}/process/", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert not data.get("error"), f"Audio query error: {data.get('error')}"
