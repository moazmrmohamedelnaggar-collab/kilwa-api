from flask import Flask, request, jsonify
import requests
import re
import time
import random
import string
import json

app = Flask(__name__)

# ============================================================
# 🔧 CONFIG
# ============================================================
SITE       = "fluxproweb.com"
BASE_URL   = f"https://{SITE}/ar/model/nano-banana-pro-ai/"
GEN_API    = "https://api2.tap4.ai"
MAIL_API   = "https://api.mail.gw"
ACTION_REG = "424401cbe4e8b1b79045e4ac3dcf3d788c2156dd"
ACTION_VER = "efbaa6169049c8cb5fd4fd1abe810d880738ab19"
ACTION_LOG = "1c7778f900ce2db3f2c455a90e709ef29ae30db3"
ROUTER     = "%5B%22%22%2C%7B%22children%22%3A%5B%5B%22locale%22%2C%22ar%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%22(with-footer)%22%2C%7B%22children%22%3A%5B%22(templates)%22%2C%7B%22children%22%3A%5B%22model%22%2C%7B%22children%22%3A%5B%22nano-banana-pro-ai%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D%7D%2Cnull%2Cnull%5D"

HEADERS = {
    "User-Agent":         "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
    "sec-ch-ua":          '"Not(A:Brand";v="8", "Chromium";v="144", "Brave";v="144"',
    "sec-ch-ua-mobile":   "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-gpc":            "1",
    "accept-language":    "ar-EG,ar;q=0.5",
    "origin":             f"https://{SITE}",
    "referer":            BASE_URL,
}

# ratio map
RATIO_MAP = {
    "1:1":  (1, 1),
    "16:9": (16, 9),
    "9:16": (9, 16),
    "4:3":  (4, 3),
    "3:4":  (3, 4),
    "21:9": (21, 9),
}

# ============================================================
# 🔑 AUTH FUNCTIONS
# ============================================================
def get_account():
    r       = requests.get(f"{MAIL_API}/domains", timeout=10)
    domains = [d["domain"] for d in r.json().get("hydra:member", [])]
    for domain in domains:
        try:
            username   = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            email      = f"{username}@{domain}"
            password   = "Pass" + ''.join(random.choices(string.digits, k=8))
            r2 = requests.post(f"{MAIL_API}/accounts", json={"address": email, "password": password}, timeout=10)
            if r2.status_code not in (200, 201): continue
            r3 = requests.post(f"{MAIL_API}/token",    json={"address": email, "password": password}, timeout=10)
            if r3.status_code != 200: continue
            mail_token = r3.json()["token"]
            if try_register(email, password):
                return email, mail_token, password
        except:
            continue
    raise Exception("فشل إنشاء حساب")

def try_register(email, password):
    nickname = ''.join(random.choices(string.ascii_letters, k=8))
    hdrs     = {**HEADERS, "Accept": "text/x-component", "Content-Type": "text/plain;charset=UTF-8",
                "next-action": ACTION_REG, "next-router-state-tree": ROUTER}
    r        = requests.post(BASE_URL, data=json.dumps([{"email": email, "userName": nickname, "password": password}]),
                             headers=hdrs, timeout=15)
    m = re.search(r'1:\{"code":(\d+)', r.text)
    return m and int(m.group(1)) == 200

def wait_otp(mail_token):
    hdrs = {"Authorization": f"Bearer {mail_token}"}
    for _ in range(30):
        time.sleep(5)
        r    = requests.get(f"{MAIL_API}/messages", headers=hdrs)
        msgs = r.json().get("hydra:member", [])
        if msgs:
            r2   = requests.get(f"{MAIL_API}/messages/{msgs[0]['id']}", headers=hdrs)
            msg  = r2.json()
            text = msg.get("text", "") or ""
            html = msg.get("html", "") or ""
            if isinstance(text, list): text = " ".join(text)
            if isinstance(html, list): html = " ".join(html)
            m = re.search(r'\b(\d{6})\b', text + html)
            if m: return m.group(1)
    raise Exception("OTP لم يصل")

def verify_otp(email, otp):
    hdrs = {**HEADERS, "Accept": "text/x-component", "Content-Type": "text/plain;charset=UTF-8",
            "next-action": ACTION_VER, "next-router-state-tree": ROUTER}
    requests.post(BASE_URL, data=json.dumps([{"email": email, "emailCode": otp}]),
                  headers=hdrs, timeout=15)

def login(email, password):
    hdrs = {**HEADERS, "Accept": "text/x-component", "Content-Type": "text/plain;charset=UTF-8",
            "next-action": ACTION_LOG, "next-router-state-tree": ROUTER}
    r = requests.post(BASE_URL, data=json.dumps([{"email": email, "password": password}]),
                      headers=hdrs, timeout=15)
    for pattern in [r'"access_token":"([^"]+)"', r'Authorization=Bearer%20([^;%]+)']:
        m = re.search(pattern, r.text + r.headers.get("set-cookie", ""))
        if m: return m.group(1)
    raise Exception("فشل تسجيل الدخول")

# ============================================================
# 🎨 GENERATE FUNCTION
# ============================================================
def generate(prompt, model="nb", ratio="1:1", res="1K", image_urls=None):
    email, mail_token, password = get_account()
    otp   = wait_otp(mail_token)
    verify_otp(email, otp)
    token = login(email, password)

    w, h = RATIO_MAP.get(ratio, (1, 1))

    hdrs = {
        **HEADERS,
        "Content-Type":     "application/json",
        "authorization":    f"Bearer {token}",
        "credentials":      "include",
        "content-language": "en",
        "sec-fetch-site":   "cross-site",
        "sec-fetch-mode":   "cors",
        "sec-fetch-dest":   "empty",
        "referer":          f"https://{SITE}/",
    }

    if model == "nbp":
        # 🍌✦ Nano Banana Pro
        payload = {
            "site":         SITE,
            "imageType":    "nano-banana-pro-image",
            "platformType": 39,
            "modelName":    "gemini-3-pro-image-preview",
            "isPublic":     1,
            "prompt":       prompt,
            "outputPrompt": prompt,
            "resolution":   res,
            "width": w, "height": h, "ratio": ratio,
            "supportRatio": True,
            "nsfwFilter":   True,
        }
    else:
        # 🍌 Nano Banana
        payload = {
            "site":         SITE,
            "platformType": 44,
            "modelName":    "gemini-25-flash-image",
            "isTranslate":  True,
            "isPublic":     1,
            "prompt":       prompt,
            "outputPrompt": prompt,
            "width": w, "height": h, "ratio": ratio,
            "supportRatio": True,
            "nsfwFilter":   True,
        }

    if image_urls:
        payload["imageUrlList"] = image_urls

    r   = requests.post(f"{GEN_API}/image/generator4login/async", data=json.dumps(payload), headers=hdrs)
    key = r.json()["data"]["key"]

    for _ in range(60):
        time.sleep(4)
        r2   = requests.get(f"{GEN_API}/image/getResult/{key}?site={SITE}", headers=hdrs)
        item = r2.json().get("data", {})
        if item.get("status") in ("success", "finish", "done", "completed"):
            vo  = item.get("imageResponseVo", {})
            url = vo.get("url") or (vo.get("images", [{}])[0].get("url"))
            if url: return url
    raise Exception("انتهت المهلة")

# ============================================================
# 🌐 API ENDPOINTS
# ============================================================

# ── GET ─────────────────────────────────────────────────────
# /generate?text=...&model=nb&ratio=1:1&res=1K
# /generate?text=...&links=https://...&ratio=1:1
@app.route("/generate", methods=["GET"])
def api_get():
    prompt     = request.args.get("text", "").strip()
    model      = request.args.get("model", "nb").strip()       # nb | nbp
    ratio      = request.args.get("ratio", "1:1").strip()
    res        = request.args.get("res",   "1K").upper().strip()
    links      = request.args.get("links", "").strip()

    if not prompt:
        return jsonify({"success": False, "error": "text مطلوب"}), 400

    image_urls = [links] if links else None

    try:
        url = generate(prompt, model=model, ratio=ratio, res=res, image_urls=image_urls)
        mode = "edit" if image_urls else "generate"
        return jsonify({
            "success": True,
            "mode":    mode,
            "url":     url,
            "dev":     "@K_I_L_W_A",
            "ch":      "https://t.me/BOTATKILWA",
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── POST ─────────────────────────────────────────────────────
# { "text": "...", "model": "nb", "ratio": "1:1", "res": "2K", "links": "..." }
@app.route("/generate", methods=["POST"])
def api_post():
    data   = request.get_json(force=True, silent=True) or {}
    prompt = data.get("text", "").strip()
    model  = data.get("model", "nb").strip()
    ratio  = data.get("ratio", "1:1").strip()
    res    = data.get("res",   "1K").upper().strip()
    links  = data.get("links", "").strip()

    if not prompt:
        return jsonify({"success": False, "error": "text مطلوب"}), 400

    image_urls = [links] if links else None

    try:
        url = generate(prompt, model=model, ratio=ratio, res=res, image_urls=image_urls)
        mode = "edit" if image_urls else "generate"
        return jsonify({
            "success": True,
            "mode":    mode,
            "url":     url,
            "dev":     "@K_I_L_W_A",
            "ch":      "https://t.me/BOTATKILWA",
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── HOME ─────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "name":    "KILWA API",
        "version": "1.0",
        "endpoints": {
            "GET":  "/generate?text=...&model=nb&ratio=1:1&res=1K&links=",
            "POST": "/generate  { text, model, ratio, res, links }",
        },
        "models": {
            "nb":  "Model 1",
            "nbp": "Model 2",
        },
        "ratio": ["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"],
        "res":   ["1K", "2K", "4K"],
    })


# ============================================================
# 🚀 RUN
# ============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
