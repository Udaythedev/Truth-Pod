import requests
import json
import base64
import os
import time

BASE = os.environ.get("TRUTHPOD_BASE", "http://127.0.0.1:8000")

def jprint(label, obj):
    print(f"\n{label}")
    try:
        print(json.dumps(obj, indent=2))
    except Exception:
        print(str(obj))

def main():
    out = {}
    # Health
    out['health'] = requests.get(f"{BASE}/api/health").json()
    jprint("GET /api/health", out['health'])

    # Register device
    reg_payload = {"device_mac": "AA:BB:CC:00:11:22", "device_name": "DemoPod", "device_type": "ESP32"}
    out['register'] = requests.post(f"{BASE}/api/iot/device/register", json=reg_payload).json()
    jprint("POST /api/iot/device/register", out['register'])
    token = out['register']['api_token']
    H = {"Authorization": f"Bearer {token}"}

    # Status
    out['status'] = requests.get(f"{BASE}/api/iot/device/status", headers=H).json()
    jprint("GET /api/iot/device/status", out['status'])

    # Heartbeat
    out['heartbeat'] = requests.post(f"{BASE}/api/iot/device/heartbeat", headers=H, json={"firmware_version": "0.1.0"}).json()
    jprint("POST /api/iot/device/heartbeat", out['heartbeat'])

    # Trending
    out['trending'] = requests.get(f"{BASE}/api/iot/trending", headers=H, params={"region": "in", "limit": 3}).json()
    jprint("GET /api/iot/trending", out['trending'])
    news_id = (out['trending'].get('data') or [{"news_id":"1"}])[0]['news_id']

    # Search
    out['search'] = requests.get(f"{BASE}/api/iot/search", headers=H, params={"query":"battery","limit":5}).json()
    jprint("GET /api/iot/search?query=battery", out['search'])

    # News TTS (JSON)
    tts = requests.get(f"{BASE}/api/iot/news/{news_id}/tts", headers=H).json()
    # mask large base64
    if 'audio_base64' in tts:
        tts['audio_base64'] = '<base64>'
    out['news_tts'] = tts
    jprint(f"GET /api/iot/news/{news_id}/tts", out['news_tts'])

    # News TTS raw
    rraw = requests.get(f"{BASE}/api/iot/news/{news_id}/tts/raw", headers=H)
    out['news_tts_raw'] = {"status_code": rraw.status_code, "content_type": rraw.headers.get('content-type')}
    jprint(f"GET /api/iot/news/{news_id}/tts/raw", out['news_tts_raw'])

    # Presigned URL (may return local path)
    out['news_tts_url'] = requests.get(f"{BASE}/api/iot/news/{news_id}/tts/url", headers=H).json()
    jprint(f"GET /api/iot/news/{news_id}/tts/url", out['news_tts_url'])

    # Background TTS request + status
    out['news_tts_request'] = requests.post(f"{BASE}/api/iot/news/{news_id}/tts/request", headers=H).json()
    jprint(f"POST /api/iot/news/{news_id}/tts/request", out['news_tts_request'])
    out['news_tts_status'] = requests.get(f"{BASE}/api/iot/news/{news_id}/tts/status", headers=H).json()
    jprint(f"GET /api/iot/news/{news_id}/tts/status", out['news_tts_status'])

    # TTS cache list
    out['tts_cache'] = requests.get(f"{BASE}/api/iot/tts/cache", headers=H).json()
    jprint("GET /api/iot/tts/cache", out['tts_cache'])

    # Preferences set/get
    out['prefs_set'] = requests.post(f"{BASE}/api/iot/preferences/1", headers=H, json={"language":"en","region":"in","categories":["technology","sports"]}).json()
    jprint("POST /api/iot/preferences/1", out['prefs_set'])
    out['prefs_get'] = requests.get(f"{BASE}/api/iot/preferences/1", headers=H).json()
    jprint("GET /api/iot/preferences/1", out['prefs_get'])

    # Interaction + analytics
    out['log_add'] = requests.post(f"{BASE}/api/iot/log/interaction", headers=H, json={"action_type":"search","query":"battery","results_count":3,"response_time_ms":120}).json()
    jprint("POST /api/iot/log/interaction", out['log_add'])
    out['analytics_summary'] = requests.get(f"{BASE}/api/iot/analytics/summary", headers=H).json()
    jprint("GET /api/iot/analytics/summary", out['analytics_summary'])
    out['analytics_list'] = requests.get(f"{BASE}/api/iot/analytics/interactions", headers=H, params={"limit":10,"offset":0}).json()
    jprint("GET /api/iot/analytics/interactions", out['analytics_list'])

    # Voice TTS JSON
    vtts = requests.post(f"{BASE}/api/iot/voice/tts", headers=H, json={"text":"Hello TruthPod"}).json()
    if 'audio_base64' in vtts:
        vtts['audio_base64'] = '<base64>'
    out['voice_tts'] = vtts
    jprint("POST /api/iot/voice/tts", out['voice_tts'])

    # Voice transcribe (send small JSON base64)
    ab = base64.b64encode(b"hello-audio").decode('ascii')
    out['voice_transcribe'] = requests.post(f"{BASE}/api/iot/voice/transcribe", headers=H, json={"audio_base64": ab}).json()
    jprint("POST /api/iot/voice/transcribe", out['voice_transcribe'])

    # Firmware upload + latest
    fw_b64 = base64.b64encode(b"TRUTHPOD_FW").decode('ascii')
    out['fw_upload'] = requests.post(f"{BASE}/api/iot/firmware/upload", headers=H, json={"version":"0.1.2","device_type":"ESP32","firmware_base64": fw_b64}).json()
    jprint("POST /api/iot/firmware/upload", out['fw_upload'])
    out['fw_latest'] = requests.get(f"{BASE}/api/iot/firmware/latest", headers=H, params={"device_type":"ESP32"}).json()
    jprint("GET /api/iot/firmware/latest", out['fw_latest'])

    # Face enroll/recognize (use dummy base64 bytes)
    dummy_b64 = base64.b64encode(b"not-an-image-but-ok").decode('ascii')
    out['face_enroll'] = requests.post(f"{BASE}/api/iot/face/enroll", headers=H, json={"user_name":"Alice","image_base64": dummy_b64}).json()
    jprint("POST /api/iot/face/enroll", out['face_enroll'])
    out['face_users'] = requests.get(f"{BASE}/api/iot/face/users", headers=H).json()
    jprint("GET /api/iot/face/users", out['face_users'])
    out['face_recognize'] = requests.post(f"{BASE}/api/iot/face/recognize", headers=H, json={"image_base64": dummy_b64}).json()
    jprint("POST /api/iot/face/recognize", out['face_recognize'])

    # Token rotate and verify old token rejected
    out['token_rotate'] = requests.post(f"{BASE}/api/iot/device/token/rotate", headers=H).json()
    jprint("POST /api/iot/device/token/rotate", out['token_rotate'])
    old = requests.get(f"{BASE}/api/iot/trending", headers={"Authorization": f"Bearer {token}"})
    jprint("GET /api/iot/trending (old token)", {"status_code": old.status_code, "json": (old.json() if old.headers.get('content-type','').startswith('application/json') else None)})
    newH = {"Authorization": f"Bearer {out['token_rotate']['api_token']}"}
    out['trending_new_token'] = requests.get(f"{BASE}/api/iot/trending", headers=newH).json()
    jprint("GET /api/iot/trending (new token)", out['trending_new_token'])

if __name__ == "__main__":
    # small wait to allow server to be ready if launched just now
    try:
        time.sleep(0.5)
    except Exception:
        pass
    main()
