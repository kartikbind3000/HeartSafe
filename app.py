"""
HeartSafe Dating App v3 - Complete Rewrite
Fixes:
- patch_bot_avatars / haversine merge bug fixed
- Real users prioritized over bots in discover feed
- Bot DiceBear avatars
- Multi-image upload (up to 10)
- Chat image sharing
- Google Sheets sync to fixed spreadsheet ID
- Google Maps integration
"""

from flask import Flask, render_template, request, jsonify, session, redirect, send_from_directory
import sqlite3, os, json, base64, uuid, hashlib, datetime, threading, time, math
import urllib.request, urllib.parse, urllib.error, ssl, subprocess, tempfile

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DB_PATH       = os.path.join(BASE_DIR, 'heartsafe_v3.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Config ─────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyBqJD2DtB3xejohja21B0KAALCsvIA0Wuk"
GEMINI_URL     = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

GOOGLE_SA_EMAIL    = "socialmedia@carbon-airlock-467402-t2.iam.gserviceaccount.com"
GOOGLE_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCYBVKIzXiD5fdk
awqYi9xaLVhk2j96Fe/UZYG2GRwqy4DHBg5ZKbPDg5imzBg/Zew1dLfFZ0CT+1Fz
Y5hXAn9Kt7tXblA6BHXxGJH+C8NS58+RltRz529N+QuABAxm5fzREHKMsxK1pJi5
OT92/9Zwc2SXt4BAhrzZrVA+XsziRjxTtqF9R6ayjZ6cOnWtd2APp8ucgHrhNpDg
6UcRergOY0pjoB7F5p0XpJ9G+936qpdkrG1WWquNpWToSBeELasdIb4N4BlLuI3Y
Nd3Jm24UyaoT0oU+lK/ma/X8TCQvWG9S516MkChYK6vhql+210h/8mKbm4f+B5kC
zBJ1B50JAgMBAAECgf8qrlPd1NJhNc+fge4XpizXpKOMrTnlLQOIvncMiUA/Q6OE
PU8J+Yte+TOCoQqtwg/vcjWmVrbq1USpAO1kgG78q1kN0wrzPw1eA2f5y5OrUyoT
1iUP5Yp6edGgv4I74ZZ5nASNPDmkhfHbDxeicXHjYIJ9lieL9khPVTmSSUt8u4yt
8EQMmKH3cpQ/S7Bz+bbofx4YdJ9moTMuHA1Y25SvSRW5mfUZHI9cmZPyFwElF42V
A5flAD7WHhA37HNRHNrO274fvme/54jKFV2bI0p1woAjWpXzVN3MZz+pEGTIp2OS
th2I1bGqhBgB2EDtpKh0fmU+u9YFqpRhzf18VFECgYEAxiPu63Rtnc7wbupzKOWT
F8o6YfXzmUCSzJArEoOOgDI7npmYjnIo/9Ggt9EVgwKBg45kv73pd6w+RqdCcsKl
1/xE14etqcChDL5omX9tPpPkV5YVhTLqJWw0MKvKt/NKN/I1+arWFkkK9EYIUlat
/hoNYVeIQaL9yrBfc1CCcbkCgYEAxGmzbRAFdqJTkA7Ub/UplbVQ07rFF5CagN/k
HKq81jTIxSES71acjOVHWNQiMSxaPJ9Hf55W4aY7ZhLECkyomt42NWP2rB3NCDOm
bQUow9uKMXawLpmKPzfPbAtGBCaEB2BV5gJnyCZr7IGVjC44HtysGq7plLFm8G5w
o3OFbdECgYA0oVbVNBfp0w4KaDwuoMxxhUX8v1f1XTGhJKpMQKWZZ75uYl4jeC9r
xELskJ0mL4Q3bZtVUxywrQ/dtI/x68IhnOCsX13BuWkN+YXPQAnElYQRv8v3lY6c
YiF6zCcMtZMBSVUM/FPhl4VRXUjYli2hUUo8kQOga6r+K9suxjPgAQKBgQCLdJFU
6n82kGLMcfsb0vJHvYk6C+5MoPtSbaVFRWT2olu6u5T6IoDc+R4DT/tG9rrLODxH
vGDrrl+WRdSzi2JbM1NB7UwDQNWG8UVFOtiK16HzJNZK//FMmY/Iouh/oek0Y44Z
1bNiRQVz0z4fXeGy5/O6rl5imOMB6yhGpYsjQQKBgQCizsqb7Hy72h9gWjqfF9PK
Poa3IIGl8yzUSwKj7dWcaJ6enPQsp05YxM1nhNpMxEMM/bTSUoBBxYTDeaLQUT06
VZW3QkZUdcE8mKBTznWlYtbv62T1IwzTdHjc50JYxc2VcqmTAZhuPOwCYqoSuW8O
iuLRRIwJ+deF/kzwy3a5gQ==
-----END PRIVATE KEY-----"""

# Fixed spreadsheet ID — all data syncs here
SPREADSHEET_ID = "1gLz5ZUMbPWxAa3jWxIg-Ls9DNTXVtGIei5jw8HmNnaw"

_gs_token     = None
_gs_token_exp = 0

# ── 50 AI Bot Profiles ─────────────────────────────────────────────────────────
BOT_PROFILES = [
    {"name":"Priya Sharma","age":24,"gender":"female","bio":"Love chai and sunsets ☕ Software engineer by day, dancer by night.","interests":"Dancing,Travel,Tech,Music","city":"Mumbai","persona":"You are Priya, a cheerful 24yo software engineer from Mumbai who loves Bollywood, chai, travel. Respond warmly in 1-3 sentences."},
    {"name":"Ananya Patel","age":22,"gender":"female","bio":"Art student with big dreams 🎨 I paint, I dream, I live fully.","interests":"Art,Coffee,Books,Yoga","city":"Delhi","persona":"You are Ananya, a creative 22yo art student from Delhi who loves deep conversations. 1-3 sentences."},
    {"name":"Sneha Reddy","age":26,"gender":"female","bio":"Doctor saving lives 💉 When not in hospital, I'm hiking or cooking.","interests":"Medicine,Hiking,Cooking,Fitness","city":"Hyderabad","persona":"You are Sneha, a dedicated 26yo doctor from Hyderabad. Warm, intelligent. 1-3 sentences."},
    {"name":"Kavya Nair","age":23,"gender":"female","bio":"Marine biologist 🌊 The ocean is my home.","interests":"Ocean,Travel,Science,Photography","city":"Kochi","persona":"You are Kavya, a passionate marine biologist from Kerala. 1-3 sentences."},
    {"name":"Riya Gupta","age":25,"gender":"female","bio":"Startup founder ✨ Building something amazing.","interests":"Entrepreneurship,Tech,Fitness,Travel","city":"Bangalore","persona":"You are Riya, an ambitious startup founder from Bangalore. Driven, witty. 1-3 sentences."},
    {"name":"Meera Joshi","age":27,"gender":"female","bio":"Classical musician 🎵 Raga mornings, jazz nights.","interests":"Music,Classical Dance,Poetry,Travel","city":"Pune","persona":"You are Meera, a talented classical musician from Pune. Artistic, introspective. 1-3 sentences."},
    {"name":"Aisha Khan","age":24,"gender":"female","bio":"Journalist chasing stories 📰 Truth-seeker, book-lover.","interests":"Journalism,Reading,Travel,Photography","city":"Lucknow","persona":"You are Aisha, a curious journalist from Lucknow. Witty, opinionated. 1-3 sentences."},
    {"name":"Divya Menon","age":28,"gender":"female","bio":"Architect designing dreams 🏛️ Beauty in structures.","interests":"Architecture,Design,Travel,Art","city":"Chennai","persona":"You are Divya, a creative architect from Chennai. 1-3 sentences."},
    {"name":"Pooja Iyer","age":21,"gender":"female","bio":"College student & foodie 🍕 Trying every restaurant!","interests":"Food,Travel,Bollywood,Friends","city":"Ahmedabad","persona":"You are Pooja, a bubbly 21yo foodie from Ahmedabad. Fun, energetic. 1-3 sentences."},
    {"name":"Nisha Verma","age":29,"gender":"female","bio":"Yoga instructor 🧘 Peace is a practice.","interests":"Yoga,Meditation,Nature,Cooking","city":"Rishikesh","persona":"You are Nisha, a serene yoga instructor. Values mindfulness. 1-3 sentences."},
    {"name":"Sakshi Tiwari","age":25,"gender":"female","bio":"Wildlife photographer 📸 Last month in Ranthambore.","interests":"Photography,Wildlife,Travel,Nature","city":"Jaipur","persona":"You are Sakshi, an adventurous wildlife photographer. 1-3 sentences."},
    {"name":"Tanvi Desai","age":23,"gender":"female","bio":"Fashion designer 👗 Creating wearable art.","interests":"Fashion,Art,Travel,Music","city":"Surat","persona":"You are Tanvi, a stylish fashion designer. Creative, trendy. 1-3 sentences."},
    {"name":"Kritika Sharma","age":26,"gender":"female","bio":"Data scientist 🔢 By night: stargazer.","interests":"Data Science,Astronomy,Books,Hiking","city":"Gurgaon","persona":"You are Kritika, a sharp data scientist and amateur astronomer. 1-3 sentences."},
    {"name":"Lavanya Krishnan","age":24,"gender":"female","bio":"Bharatanatyam dancer 💃 Dancing is breathing.","interests":"Dance,Music,Travel,Cooking","city":"Mysore","persona":"You are Lavanya, a graceful classical dancer from Mysore. 1-3 sentences."},
    {"name":"Aditi Bhatt","age":27,"gender":"female","bio":"Neuroscientist 🧠 Weekend trekker.","interests":"Neuroscience,Trekking,Books,Coffee","city":"Ahmedabad","persona":"You are Aditi, an intellectually curious neuroscientist. 1-3 sentences."},
    {"name":"Shruti Pillai","age":22,"gender":"female","bio":"Content creator 🎬 Making videos that move people.","interests":"YouTube,Travel,Fashion,Coffee","city":"Bangalore","persona":"You are Shruti, a creative content creator. Expressive, fun. 1-3 sentences."},
    {"name":"Radhika Nair","age":28,"gender":"female","bio":"Chef & entrepreneur 🍳 My kitchen is my kingdom.","interests":"Cooking,Travel,Art,Entrepreneurship","city":"Kochi","persona":"You are Radhika, a passionate chef who believes food is love. 1-3 sentences."},
    {"name":"Swati Kulkarni","age":25,"gender":"female","bio":"Environmental activist 🌿 Fighting for a greener tomorrow.","interests":"Environment,Yoga,Books,Travel","city":"Nagpur","persona":"You are Swati, a dedicated environmental activist. Passionate, idealistic. 1-3 sentences."},
    {"name":"Pallavi Sinha","age":26,"gender":"female","bio":"IAS aspirant 📚 Studying hard, dreaming bigger.","interests":"Current Affairs,Books,History,Travel","city":"Patna","persona":"You are Pallavi, a determined IAS aspirant. Ambitious, well-read. 1-3 sentences."},
    {"name":"Simran Arora","age":23,"gender":"female","bio":"Punjabi girl with big heart ❤️ Love bhangra and real talk.","interests":"Dance,Food,Punjabi Music,Travel","city":"Chandigarh","persona":"You are Simran, a warm-hearted Punjabi girl from Chandigarh. Fun and loving. 1-3 sentences."},
    {"name":"Aman Kapoor","age":27,"gender":"male","bio":"Architect & travel junkie ✈️ 20 countries. Need a co-pilot.","interests":"Travel,Architecture,Photography,Music","city":"Delhi","persona":"You are Aman, a well-traveled architect from Delhi. Adventurous, sophisticated. 1-3 sentences."},
    {"name":"Rohit Sharma","age":26,"gender":"male","bio":"Startup co-founder 🚀 Building EdTech for rural India.","interests":"Tech,Social Impact,Travel,Cricket","city":"Bangalore","persona":"You are Rohit, a passionate entrepreneur building EdTech. 1-3 sentences."},
    {"name":"Vikram Singh","age":28,"gender":"male","bio":"Army officer 🎖️ Serving the nation, valuing loyalty.","interests":"Fitness,Travel,Reading,Mountains","city":"Dehradun","persona":"You are Vikram, a disciplined army officer who values honor. 1-3 sentences."},
    {"name":"Arjun Mehta","age":25,"gender":"male","bio":"Music producer 🎹 Made Bollywood beats. Looking for my muse.","interests":"Music,Bollywood,Travel,Photography","city":"Mumbai","persona":"You are Arjun, a creative music producer. Charismatic, artistic. 1-3 sentences."},
    {"name":"Karan Malhotra","age":29,"gender":"male","bio":"Cardiologist ❤️ Healing hearts professionally.","interests":"Medicine,Fitness,Travel,Books","city":"Delhi","persona":"You are Karan, a caring cardiologist who values deep connections. 1-3 sentences."},
    {"name":"Dev Nair","age":24,"gender":"male","bio":"Marine engineer ⚓ Sailed 3 oceans. World is my home.","interests":"Travel,Ocean,Adventure,Photography","city":"Mumbai","persona":"You are Dev, a worldly marine engineer with amazing sea stories. 1-3 sentences."},
    {"name":"Nikhil Joshi","age":26,"gender":"male","bio":"Chef & restaurant owner 🍽️ Michelin-star trained.","interests":"Cooking,Travel,Art,Wine","city":"Pune","persona":"You are Nikhil, a talented chef passionate about culinary arts. 1-3 sentences."},
    {"name":"Samir Patel","age":27,"gender":"male","bio":"Astrophysicist 🔭 Looking for intelligent life — starting here.","interests":"Astronomy,Physics,Travel,Books","city":"Ahmedabad","persona":"You are Samir, a brilliant astrophysicist with great humor. 1-3 sentences."},
    {"name":"Rajiv Kumar","age":25,"gender":"male","bio":"Social entrepreneur 🌍 NGOs in 5 states.","interests":"Social Work,Travel,Reading,Fitness","city":"Lucknow","persona":"You are Rajiv, a compassionate social entrepreneur. 1-3 sentences."},
    {"name":"Aditya Rao","age":28,"gender":"male","bio":"Filmmaker 🎥 3 national awards. Reality is my canvas.","interests":"Cinema,Travel,Photography,Books","city":"Hyderabad","persona":"You are Aditya, a creative filmmaker who sees stories everywhere. 1-3 sentences."},
    {"name":"Shivam Mishra","age":23,"gender":"male","bio":"IIT-IIM grad 📊 Consulting by day, guitarist by night.","interests":"Music,Fitness,Travel,Finance","city":"Mumbai","persona":"You are Shivam, blending analytical thinking with creativity and music. 1-3 sentences."},
    {"name":"Pranav Iyer","age":26,"gender":"male","bio":"Environmental scientist 🌱 Planting trees and good convos.","interests":"Environment,Trekking,Yoga,Books","city":"Chennai","persona":"You are Pranav, an environmentally conscious scientist. 1-3 sentences."},
    {"name":"Kartik Desai","age":27,"gender":"male","bio":"Investment banker 💰 Work hard, travel harder.","interests":"Finance,Travel,Fitness,Wine","city":"Mumbai","persona":"You are Kartik, an ambitious investment banker. 1-3 sentences."},
    {"name":"Varun Reddy","age":24,"gender":"male","bio":"Ethical hacker 🔒 Making the internet safer.","interests":"Cybersecurity,Gaming,Tech,Coffee","city":"Hyderabad","persona":"You are Varun, a sharp cybersecurity expert who is surprisingly romantic. 1-3 sentences."},
    {"name":"Mihir Bhatt","age":28,"gender":"male","bio":"Yoga teacher 🧘 Inner peace is the greatest adventure.","interests":"Yoga,Philosophy,Travel,Vegetarian Food","city":"Vadodara","persona":"You are Mihir, a calm yoga teacher who loves philosophical conversations. 1-3 sentences."},
    {"name":"Kunal Verma","age":25,"gender":"male","bio":"Stand-up comedian 😂 Making people laugh for a living.","interests":"Comedy,Travel,Movies,Food","city":"Delhi","persona":"You are Kunal, a hilarious stand-up comedian who is warm and witty. 1-3 sentences."},
    {"name":"Ankit Srivastava","age":26,"gender":"male","bio":"Mountaineer ⛰️ 4 peaks summited. Love heights.","interests":"Mountaineering,Photography,Travel,Fitness","city":"Dehradun","persona":"You are Ankit, a fearless mountaineer who lives for adventure. 1-3 sentences."},
    {"name":"Rahul Tiwari","age":27,"gender":"male","bio":"Kathak dancer 💫 Art transcends everything.","interests":"Dance,Classical Music,Travel,Spirituality","city":"Banaras","persona":"You are Rahul, a graceful Kathak dancer who is spiritual and artistic. 1-3 sentences."},
    {"name":"Siddharth Nair","age":29,"gender":"male","bio":"Neurosurgeon 🧠 Saving brains. Dog dad of 2.","interests":"Medicine,Dogs,Travel,Books","city":"Kochi","persona":"You are Siddharth, a brilliant neurosurgeon who is down-to-earth. 1-3 sentences."},
    {"name":"Tarun Kapoor","age":24,"gender":"male","bio":"Sports journalist ⚽ Covered World Cup 2022.","interests":"Football,Travel,Writing,Fitness","city":"Delhi","persona":"You are Tarun, an energetic sports journalist who loves a good story. 1-3 sentences."},
    {"name":"Maya Rodriguez","age":25,"gender":"female","bio":"International student & food blogger 🌮 Fell in love with India.","interests":"Food,Travel,Photography,Languages","city":"Mumbai","persona":"You are Maya, a warm Spanish student who loves Indian culture. 1-3 sentences."},
    {"name":"Zara Ahmed","age":26,"gender":"female","bio":"Fashion photographer 📷 Beauty is everywhere.","interests":"Photography,Fashion,Travel,Art","city":"Delhi","persona":"You are Zara, a stylish fashion photographer who sees art in everything. 1-3 sentences."},
    {"name":"Leila Bashir","age":24,"gender":"female","bio":"Software dev & gamer 🎮 Pro at code and Valorant.","interests":"Gaming,Tech,Anime,Coffee","city":"Bangalore","persona":"You are Leila, a geeky software developer who loves gaming. 1-3 sentences."},
    {"name":"Prachi Dubey","age":27,"gender":"female","bio":"Theatre actress 🎭 Every stage is a new world.","interests":"Theatre,Dance,Books,Travel","city":"Bhopal","persona":"You are Prachi, a passionate theatre actress who is expressive. 1-3 sentences."},
    {"name":"Rashmi Bose","age":25,"gender":"female","bio":"Bengali girl with global dreams ✨ Lover of Tagore and biryani.","interests":"Literature,Music,Travel,Cooking","city":"Kolkata","persona":"You are Rashmi, an intellectually deep Bengali who loves literature. 1-3 sentences."},
    {"name":"Isha Choudhary","age":23,"gender":"female","bio":"Political science student 🗳️ Debate me!","interests":"Politics,Books,Badminton,Travel","city":"Jaipur","persona":"You are Isha, a sharp political science student who loves debates. 1-3 sentences."},
    {"name":"Natasha Khanna","age":28,"gender":"female","bio":"Luxury travel blogger 🌟 45 countries visited.","interests":"Travel,Luxury,Photography,Food","city":"Gurgaon","persona":"You are Natasha, a sophisticated travel blogger with incredible stories. 1-3 sentences."},
    {"name":"Deepika Suresh","age":26,"gender":"female","bio":"Agricultural scientist 🌾 Growing food, feeding dreams.","interests":"Agriculture,Nature,Cooking,Travel","city":"Coimbatore","persona":"You are Deepika, a grounded agricultural scientist. 1-3 sentences."},
    {"name":"Mansi Agarwal","age":24,"gender":"female","bio":"Startup marketer & meme queen 😄 Digital native.","interests":"Marketing,Social Media,Comedy,Travel","city":"Noida","persona":"You are Mansi, a fun digital marketer who is witty and internet-savvy. 1-3 sentences."},
    {"name":"Rhea Kapoor","age":27,"gender":"female","bio":"Psychologist 🧩 Empathy is my superpower.","interests":"Psychology,Books,Yoga,Art","city":"Pune","persona":"You are Rhea, a warm psychologist who is empathetic and insightful. 1-3 sentences."},
]

# ── Google Auth ────────────────────────────────────────────────────────────────
def _b64url(data):
    if isinstance(data, str): data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def get_google_token():
    global _gs_token, _gs_token_exp
    now = time.time()
    if _gs_token and now < _gs_token_exp - 60:
        return _gs_token
    try:
        header  = _b64url(json.dumps({"alg":"RS256","typ":"JWT"}))
        iat     = int(now)
        payload = _b64url(json.dumps({
            "iss": GOOGLE_SA_EMAIL,
            "scope": "https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": iat, "exp": iat + 3600
        }))
        signing_input = f"{header}.{payload}"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write(GOOGLE_PRIVATE_KEY)
            key_file = f.name
        result = subprocess.run(
            ['openssl', 'dgst', '-sha256', '-sign', key_file],
            input=signing_input.encode(), capture_output=True)
        os.unlink(key_file)
        if result.returncode != 0: return None
        jwt_token = f"{signing_input}.{_b64url(result.stdout)}"
        data = urllib.parse.urlencode({
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': jwt_token
        }).encode()
        ctx = ssl.create_default_context()
        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data,
                                     headers={'Content-Type':'application/x-www-form-urlencoded'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            r = json.loads(resp.read())
            _gs_token     = r.get('access_token')
            _gs_token_exp = now + r.get('expires_in', 3600)
            return _gs_token
    except Exception as e:
        print(f"[GAuth] {e}")
        return None

def sheets_ensure_headers():
    """Write column headers to each sheet if row 1 is empty"""
    headers_map = {
        "Users":            ["ID","Username","Email","Name","Age","Gender","City","Bio","Interests","Goal","CreatedAt"],
        "Matches":          ["MatchID","User1","User2","CreatedAt"],
        "Messages":         ["MsgID","MatchID","SenderID","Content","Type","CreatedAt"],
        "SOS_Alerts":       ["SOS_ID","UserID","Name","Lat","Lon","Message","SentTo","Time"],
        "Live_Locations":   ["UserID","Lat","Lon","Accuracy","Time"],
        "Safety_Contacts":  ["ID","UserID","Name","Relation","Phone","Time"],
        "Nearby_Requests":  ["ID","SenderID","ReceiverID","Message","Time"],
    }
    token = get_google_token()
    if not token:
        print("[Sheets] Could not get token for header init")
        return
    ctx = ssl.create_default_context()
    for sheet, hdrs in headers_map.items():
        try:
            # Check if headers already set
            url = (f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}"
                   f"/values/{urllib.parse.quote(sheet)}!A1?majorDimension=ROWS")
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
            with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                existing = json.loads(resp.read()).get('values', [])
                if existing and existing[0]:
                    continue  # Headers already in place
        except Exception:
            pass  # Sheet may not exist or be empty — try to write anyway
        try:
            url  = (f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}"
                    f"/values/{urllib.parse.quote(sheet)}!A1?valueInputOption=RAW")
            body = json.dumps({"values": [hdrs]}).encode()
            req  = urllib.request.Request(url, data=body, method='PUT',
                                          headers={'Authorization': f'Bearer {token}',
                                                   'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, context=ctx, timeout=8):
                pass
            print(f"[Sheets] Headers written to sheet: {sheet}")
        except Exception as e:
            print(f"[Sheets] Header write error for {sheet}: {e}")

def sheets_append(sheet_name, values):
    """Append one row to the fixed spreadsheet (blocking)"""
    token = get_google_token()
    if not token: return
    try:
        url  = (f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}"
                f"/values/{urllib.parse.quote(sheet_name)}:append"
                f"?valueInputOption=RAW&insertDataOption=INSERT_ROWS")
        body = json.dumps({"values": [values]}).encode()
        ctx  = ssl.create_default_context()
        req  = urllib.request.Request(url, data=body,
                                      headers={'Authorization': f'Bearer {token}',
                                               'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, context=ctx, timeout=10):
            pass
    except Exception as e:
        print(f"[Sheets] append error on {sheet_name}: {e}")

def sheets_append_bg(sheet_name, values):
    """Non-blocking wrapper"""
    threading.Thread(target=sheets_append, args=(sheet_name, values), daemon=True).start()

# ── Telegram ───────────────────────────────────────────────────────────────────
def tg_send(bot_token, chat_id, text, parse_mode="HTML"):
    try:
        url  = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = json.dumps({"chat_id":chat_id,"text":text,"parse_mode":parse_mode}).encode()
        ctx  = ssl.create_default_context()
        req  = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[TG] {e}"); return None

def tg_location(bot_token, chat_id, lat, lon):
    try:
        url  = f"https://api.telegram.org/bot{bot_token}/sendLocation"
        data = json.dumps({"chat_id":chat_id,"latitude":lat,"longitude":lon}).encode()
        ctx  = ssl.create_default_context()
        req  = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[TG loc] {e}"); return None

# ── Gemini AI ──────────────────────────────────────────────────────────────────
def gemini_chat(persona, history, user_msg):
    try:
        parts = [{"text": f"System: {persona}\nBe warm and flirty but respectful. Max 2 sentences."}]
        for h in history[-6:]:
            parts.append({"text": f"{'User' if h['role']=='user' else 'You'}: {h['content']}"})
        parts.append({"text": f"User: {user_msg}\nYou:"})
        body = json.dumps({"contents":[{"parts":parts}],
                           "generationConfig":{"maxOutputTokens":120,"temperature":0.9}}).encode()
        ctx  = ssl.create_default_context()
        req  = urllib.request.Request(GEMINI_URL, data=body, headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = json.loads(resp.read())
            text = data['candidates'][0]['content']['parts'][0]['text']
            return text.strip().lstrip('You:').strip()
    except Exception as e:
        print(f"[Gemini] {e}")
        return "Hey! 😊 Tell me more about yourself!"

# ── Database ───────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            name TEXT NOT NULL, age INTEGER, gender TEXT, bio TEXT,
            interests TEXT, location_city TEXT, profile_photo TEXT,
            photos TEXT DEFAULT '[]', online INTEGER DEFAULT 0,
            last_seen TEXT, created_at TEXT DEFAULT (datetime('now')),
            latitude REAL, longitude REAL, looking_for TEXT,
            height TEXT, education TEXT, job TEXT, relationship_goal TEXT,
            telegram_bot_token TEXT, telegram_chat_id TEXT,
            sos_message TEXT DEFAULT '🆘 EMERGENCY! I need help!',
            live_location_active INTEGER DEFAULT 0,
            is_bot INTEGER DEFAULT 0, bot_persona TEXT,
            verified INTEGER DEFAULT 0, premium INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS telegram_channels (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
            label TEXT NOT NULL, bot_token TEXT NOT NULL,
            chat_id TEXT NOT NULL, active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS safety_contacts (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
            name TEXT NOT NULL, relation TEXT,
            telegram_bot_token TEXT, telegram_chat_id TEXT,
            phone TEXT, created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sos_alerts (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
            latitude REAL, longitude REAL, message TEXT,
            sent_to TEXT, created_at TEXT DEFAULT (datetime('now')),
            resolved INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS swipes (
            id TEXT PRIMARY KEY, swiper_id TEXT NOT NULL,
            swiped_id TEXT NOT NULL, direction TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(swiper_id, swiped_id)
        );
        CREATE TABLE IF NOT EXISTS matches (
            id TEXT PRIMARY KEY, user1_id TEXT NOT NULL,
            user2_id TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user1_id, user2_id)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY, match_id TEXT NOT NULL,
            sender_id TEXT NOT NULL, content TEXT,
            message_type TEXT DEFAULT 'text', media_url TEXT,
            created_at TEXT DEFAULT (datetime('now')), read_at TEXT
        );
        CREATE TABLE IF NOT EXISTS bot_chat_history (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
            bot_id TEXT NOT NULL, role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS live_sessions (
            id TEXT PRIMARY KEY, host_id TEXT NOT NULL, title TEXT,
            viewers TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            ended_at TEXT, active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS stories (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
            media_url TEXT NOT NULL, media_type TEXT DEFAULT 'image',
            caption TEXT, views TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')), expires_at TEXT
        );
        CREATE TABLE IF NOT EXISTS nearby_requests (
            id TEXT PRIMARY KEY, sender_id TEXT NOT NULL,
            receiver_id TEXT NOT NULL, message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(sender_id, receiver_id)
        );
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY, reporter_id TEXT NOT NULL,
            reported_id TEXT NOT NULL, reason TEXT NOT NULL,
            details TEXT, created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS blocks (
            id TEXT PRIMARY KEY, blocker_id TEXT NOT NULL,
            blocked_id TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(blocker_id, blocked_id)
        );
        CREATE TABLE IF NOT EXISTS location_shares (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL UNIQUE,
            latitude REAL, longitude REAL, accuracy REAL,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        """)
    print("[DB] Initialized")

# ── Bot Seeding ────────────────────────────────────────────────────────────────
def _dicebear_url(name, gender):
    seed  = name.replace(' ', '')
    style = 'adventurer' if gender == 'female' else 'big-smile'
    return (f"https://api.dicebear.com/7.x/{style}/svg"
            f"?seed={seed}&backgroundColor=b6e3f4,c0aede,d1d4f9,ffd5dc&radius=50")

def patch_bot_avatars(conn):
    """Give DiceBear avatars to any bots missing a profile photo (uses open conn)."""
    bots = conn.execute(
        "SELECT id,name,gender FROM users WHERE is_bot=1 AND (profile_photo IS NULL OR profile_photo='')"
    ).fetchall()
    for bot in bots:
        conn.execute("UPDATE users SET profile_photo=? WHERE id=?",
                     (_dicebear_url(bot['name'], bot['gender']), bot['id']))
    if bots:
        print(f"[Bots] Patched avatars for {len(bots)} bots")

def seed_bots():
    import random
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM users WHERE is_bot=1").fetchone()[0]
        if count < 40:
            print(f"[Bots] Seeding {len(BOT_PROFILES)} bot profiles...")
            base_lat, base_lon = 28.6139, 77.2090
            for i, bot in enumerate(BOT_PROFILES):
                bot_id = f"bot_{i:03d}"
                if conn.execute("SELECT id FROM users WHERE id=?", (bot_id,)).fetchone():
                    continue
                angle = random.uniform(0, 2 * math.pi)
                dist  = random.uniform(0.01, 0.5)
                lat   = base_lat + dist * math.cos(angle)
                lon   = base_lon + dist * math.sin(angle)
                conn.execute("""INSERT OR IGNORE INTO users
                    (id,username,email,password_hash,name,age,gender,bio,interests,
                     location_city,online,is_bot,bot_persona,latitude,longitude,
                     relationship_goal,looking_for,verified,profile_photo)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    bot_id,
                    f"bot_{bot['name'].lower().replace(' ','_')}_{i}",
                    f"bot_{i}@heartsafe.ai",
                    "bot_no_login",
                    bot['name'], bot['age'], bot['gender'],
                    bot['bio'], bot['interests'], bot['city'],
                    1, 1, bot['persona'], lat, lon,
                    'relationship',
                    'male' if bot['gender'] == 'female' else 'female',
                    1,
                    _dicebear_url(bot['name'], bot['gender'])
                ))
            print("[Bots] Seeded successfully")
        # Always patch any missing avatars
        patch_bot_avatars(conn)

# ── Utilities ──────────────────────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R    = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a    = (math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))

def hp(pw):     return hashlib.sha256(pw.encode()).hexdigest()
def cpw(pw, h): return hp(pw) == h
def uid():      return str(uuid.uuid4())
def now_str():  return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

ALLOWED_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

def save_upload(file_obj):
    ext = os.path.splitext(file_obj.filename)[1].lower()
    if ext not in ALLOWED_EXT: return None
    fname = f"{uid()}{ext}"
    file_obj.save(os.path.join(UPLOAD_FOLDER, fname))
    return f"/static/uploads/{fname}"

def require_login(f):
    from functools import wraps
    @wraps(f)
    def dec(*a, **kw):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*a, **kw)
    return dec

# ── Page Routes ────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session: return redirect('/app')
    return render_template('index.html')

@app.route('/app')
def main_app():
    if 'user_id' not in session: return redirect('/')
    return render_template('app.html')

@app.route('/static/uploads/<filename>')
def uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ── Auth ───────────────────────────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    d = request.json
    user_id = uid()
    try:
        with get_db() as conn:
            conn.execute("""INSERT INTO users
                (id,username,email,password_hash,name,age,gender,bio,interests,looking_for,relationship_goal)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (user_id, d['username'], d['email'], hp(d['password']),
                 d['name'], d.get('age', 18), d.get('gender', 'female'),
                 d.get('bio', ''), d.get('interests', ''),
                 d.get('looking_for', 'male'), d.get('goal', 'relationship')))
        session['user_id'] = user_id
        sheets_append_bg('Users', [user_id, d['username'], d['email'], d['name'],
                                    str(d.get('age', 18)), d.get('gender', ''),
                                    '', '', '', d.get('goal', ''), now_str()])
        return jsonify({'success': True, 'user_id': user_id})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or email already exists'}), 400

@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    with get_db() as conn:
        u = conn.execute(
            "SELECT * FROM users WHERE (email=? OR username=?) AND is_bot=0",
            (d['identifier'], d['identifier'])).fetchone()
    if u and cpw(d['password'], u['password_hash']):
        session['user_id'] = u['id']
        with get_db() as conn:
            conn.execute("UPDATE users SET online=1,last_seen=datetime('now') WHERE id=?", (u['id'],))
        return jsonify({'success': True, 'user': dict(u)})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
@require_login
def logout():
    with get_db() as conn:
        conn.execute("UPDATE users SET online=0,last_seen=datetime('now') WHERE id=?", (session['user_id'],))
    session.clear()
    return jsonify({'success': True})

@app.route('/api/me')
@require_login
def me():
    with get_db() as conn:
        u = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    if not u: return jsonify({'error': 'Not found'}), 404
    d = dict(u)
    d.pop('password_hash', None)
    d.pop('bot_persona', None)
    try:    d['photos'] = json.loads(d.get('photos') or '[]')
    except: d['photos'] = []
    return jsonify(d)

@app.route('/api/profile', methods=['PUT'])
@require_login
def update_profile():
    d = request.json
    allowed = ['name','age','bio','interests','location_city','looking_for','height','education',
               'job','relationship_goal','telegram_bot_token','telegram_chat_id','sos_message']
    upd = {k: v for k, v in d.items() if k in allowed}
    if not upd: return jsonify({'error': 'No valid fields'}), 400
    sql = ', '.join(f"{k}=?" for k in upd)
    with get_db() as conn:
        conn.execute(f"UPDATE users SET {sql} WHERE id=?", list(upd.values()) + [session['user_id']])
    return jsonify({'success': True})

# ── Photos ─────────────────────────────────────────────────────────────────────
@app.route('/api/upload-photo', methods=['POST'])
@require_login
def upload_photo():
    if 'photo' not in request.files: return jsonify({'error': 'No file'}), 400
    url = save_upload(request.files['photo'])
    if not url: return jsonify({'error': 'Invalid file type'}), 400
    pt = request.form.get('type', 'gallery')
    with get_db() as conn:
        if pt == 'profile':
            conn.execute("UPDATE users SET profile_photo=? WHERE id=?", (url, session['user_id']))
        else:
            row    = conn.execute("SELECT photos FROM users WHERE id=?", (session['user_id'],)).fetchone()
            photos = json.loads(row['photos'] or '[]')
            photos.append(url)
            conn.execute("UPDATE users SET photos=? WHERE id=?", (json.dumps(photos), session['user_id']))
    return jsonify({'url': url})

@app.route('/api/upload-photos', methods=['POST'])
@require_login
def upload_multiple_photos():
    files = request.files.getlist('photos')
    if not files: return jsonify({'error': 'No files'}), 400
    urls = []
    with get_db() as conn:
        row    = conn.execute("SELECT photos FROM users WHERE id=?", (session['user_id'],)).fetchone()
        photos = json.loads(row['photos'] or '[]')
        for f in files[:10]:
            url = save_upload(f)
            if url:
                photos.append(url)
                urls.append(url)
        conn.execute("UPDATE users SET photos=? WHERE id=?", (json.dumps(photos), session['user_id']))
    return jsonify({'urls': urls, 'success': True})

@app.route('/api/delete-photo', methods=['POST'])
@require_login
def delete_photo():
    url = request.json.get('url')
    if not url: return jsonify({'error': 'No url'}), 400
    with get_db() as conn:
        row    = conn.execute("SELECT photos FROM users WHERE id=?", (session['user_id'],)).fetchone()
        photos = [p for p in json.loads(row['photos'] or '[]') if p != url]
        conn.execute("UPDATE users SET photos=? WHERE id=?", (json.dumps(photos), session['user_id']))
    return jsonify({'success': True})

# ── Discover (real users first) ────────────────────────────────────────────────
@app.route('/api/discover')
@require_login
def discover():
    uid_me = session['user_id']
    with get_db() as conn:
        swiped  = [r['swiped_id'] for r in conn.execute("SELECT swiped_id FROM swipes WHERE swiper_id=?", (uid_me,)).fetchall()]
        blocked = [r['blocked_id'] for r in conn.execute("SELECT blocked_id FROM blocks WHERE blocker_id=?", (uid_me,)).fetchall()]
        excl    = swiped + blocked + [uid_me]
        ph      = ','.join('?' * len(excl))
        cols    = "id,name,age,gender,bio,interests,profile_photo,photos,location_city,height,education,job,relationship_goal,online,last_seen,verified,is_bot"
        # Real users: online first, then most recently active
        real = conn.execute(
            f"SELECT {cols} FROM users WHERE id NOT IN ({ph}) AND is_bot=0 ORDER BY online DESC, last_seen DESC LIMIT 20",
            excl).fetchall()
        # Bots: random order for variety
        bots = conn.execute(
            f"SELECT {cols} FROM users WHERE id NOT IN ({ph}) AND is_bot=1 ORDER BY RANDOM() LIMIT 10",
            excl).fetchall()

    def to_d(u):
        d = dict(u)
        try:    d['photos'] = json.loads(d.get('photos') or '[]')
        except: d['photos'] = []
        return d

    # Merge: every 3rd real user followed by 1 bot
    result, bi = [], 0
    bots = [to_d(b) for b in bots]
    for i, u in enumerate(real):
        result.append(to_d(u))
        if (i + 1) % 3 == 0 and bi < len(bots):
            result.append(bots[bi]); bi += 1
    while bi < len(bots):
        result.append(bots[bi]); bi += 1
    return jsonify(result)

# ── Swipe ──────────────────────────────────────────────────────────────────────
@app.route('/api/swipe', methods=['POST'])
@require_login
def swipe():
    d         = request.json
    uid_me    = session['user_id']
    tid       = d['target_id']
    direction = d['direction']
    with get_db() as conn:
        try:
            conn.execute("INSERT INTO swipes (id,swiper_id,swiped_id,direction) VALUES (?,?,?,?)",
                         (uid(), uid_me, tid, direction))
        except sqlite3.IntegrityError:
            pass
        matched  = False
        match_id = None
        if direction == 'like':
            target = conn.execute("SELECT is_bot FROM users WHERE id=?", (tid,)).fetchone()
            is_bot = target and target['is_bot']
            if is_bot:
                ex = conn.execute(
                    "SELECT id FROM matches WHERE (user1_id=? AND user2_id=?) OR (user1_id=? AND user2_id=?)",
                    (uid_me, tid, tid, uid_me)).fetchone()
                if not ex:
                    match_id = uid()
                    u1, u2 = sorted([uid_me, tid])
                    conn.execute("INSERT INTO matches (id,user1_id,user2_id) VALUES (?,?,?)", (match_id, u1, u2))
                    matched = True
            else:
                mutual = conn.execute(
                    "SELECT id FROM swipes WHERE swiper_id=? AND swiped_id=? AND direction='like'",
                    (tid, uid_me)).fetchone()
                if mutual:
                    ex = conn.execute(
                        "SELECT id FROM matches WHERE (user1_id=? AND user2_id=?) OR (user1_id=? AND user2_id=?)",
                        (uid_me, tid, tid, uid_me)).fetchone()
                    if not ex:
                        match_id = uid()
                        u1, u2 = sorted([uid_me, tid])
                        conn.execute("INSERT INTO matches (id,user1_id,user2_id) VALUES (?,?,?)", (match_id, u1, u2))
                        matched = True
    if matched:
        sheets_append_bg('Matches', [match_id, uid_me, tid, now_str()])
    return jsonify({'matched': matched, 'match_id': match_id})

# ── Matches ────────────────────────────────────────────────────────────────────
@app.route('/api/matches')
@require_login
def get_matches():
    uid_me = session['user_id']
    with get_db() as conn:
        rows = conn.execute("""SELECT m.id as match_id, m.created_at,
            CASE WHEN m.user1_id=? THEN m.user2_id ELSE m.user1_id END as other_id
            FROM matches m WHERE m.user1_id=? OR m.user2_id=?""",
            (uid_me, uid_me, uid_me)).fetchall()
        result = []
        for m in rows:
            other = conn.execute(
                "SELECT id,name,profile_photo,online,last_seen,is_bot FROM users WHERE id=?",
                (m['other_id'],)).fetchone()
            lm = conn.execute(
                "SELECT content,created_at,sender_id,message_type FROM messages WHERE match_id=? ORDER BY created_at DESC LIMIT 1",
                (m['match_id'],)).fetchone()
            if other:
                result.append({'match_id': m['match_id'], 'matched_at': m['created_at'],
                                'user': dict(other), 'last_message': dict(lm) if lm else None})
    return jsonify(result)

# ── Messages ───────────────────────────────────────────────────────────────────
@app.route('/api/messages/<match_id>')
@require_login
def get_messages(match_id):
    uid_me = session['user_id']
    with get_db() as conn:
        m = conn.execute("SELECT * FROM matches WHERE id=? AND (user1_id=? OR user2_id=?)",
                         (match_id, uid_me, uid_me)).fetchone()
        if not m: return jsonify({'error': 'Not authorized'}), 403
        msgs = conn.execute("SELECT * FROM messages WHERE match_id=? ORDER BY created_at ASC", (match_id,)).fetchall()
        conn.execute("UPDATE messages SET read_at=datetime('now') WHERE match_id=? AND sender_id!=? AND read_at IS NULL",
                     (match_id, uid_me))
    return jsonify([dict(x) for x in msgs])

@app.route('/api/messages', methods=['POST'])
@require_login
def send_message():
    d        = request.json
    uid_me   = session['user_id']
    match_id = d['match_id']
    content  = d.get('content', '')
    msg_type = d.get('type', 'text')
    with get_db() as conn:
        m = conn.execute("SELECT * FROM matches WHERE id=? AND (user1_id=? OR user2_id=?)",
                         (match_id, uid_me, uid_me)).fetchone()
        if not m: return jsonify({'error': 'Not authorized'}), 403
        msg_id = uid()
        conn.execute("INSERT INTO messages (id,match_id,sender_id,content,message_type) VALUES (?,?,?,?,?)",
                     (msg_id, match_id, uid_me, content, msg_type))
        other_id = m['user2_id'] if m['user1_id'] == uid_me else m['user1_id']
        bot = conn.execute("SELECT is_bot,bot_persona,name FROM users WHERE id=? AND is_bot=1",
                           (other_id,)).fetchone()
    if bot and msg_type == 'text':
        with get_db() as conn:
            hist = conn.execute(
                "SELECT role,content FROM bot_chat_history WHERE user_id=? AND bot_id=? ORDER BY created_at DESC LIMIT 10",
                (uid_me, other_id)).fetchall()
            conn.execute("INSERT INTO bot_chat_history (id,user_id,bot_id,role,content) VALUES (?,?,?,?,?)",
                         (uid(), uid_me, other_id, 'user', content))
        history = [{'role': h['role'], 'content': h['content']} for h in reversed(list(hist))]
        def bot_reply():
            time.sleep(1.5)
            reply = gemini_chat(bot['bot_persona'], history, content)
            with get_db() as conn:
                conn.execute("INSERT INTO messages (id,match_id,sender_id,content) VALUES (?,?,?,?)",
                             (uid(), match_id, other_id, reply))
                conn.execute("INSERT INTO bot_chat_history (id,user_id,bot_id,role,content) VALUES (?,?,?,?,?)",
                             (uid(), uid_me, other_id, 'assistant', reply))
        threading.Thread(target=bot_reply, daemon=True).start()
    sheets_append_bg('Messages', [msg_id, match_id, uid_me, content[:200], msg_type, now_str()])
    return jsonify({'success': True, 'message_id': msg_id})

# ── Telegram Channels ──────────────────────────────────────────────────────────
@app.route('/api/telegram-channels', methods=['GET'])
@require_login
def get_tg_channels():
    with get_db() as conn:
        chs = conn.execute("SELECT * FROM telegram_channels WHERE user_id=?", (session['user_id'],)).fetchall()
    return jsonify([dict(c) for c in chs])

@app.route('/api/telegram-channels', methods=['POST'])
@require_login
def add_tg_channel():
    d = request.json
    with get_db() as conn:
        conn.execute("INSERT INTO telegram_channels (id,user_id,label,bot_token,chat_id) VALUES (?,?,?,?,?)",
                     (uid(), session['user_id'], d['label'], d['bot_token'], d['chat_id']))
    return jsonify({'success': True})

@app.route('/api/telegram-channels/<ch_id>', methods=['DELETE'])
@require_login
def del_tg_channel(ch_id):
    with get_db() as conn:
        conn.execute("DELETE FROM telegram_channels WHERE id=? AND user_id=?", (ch_id, session['user_id']))
    return jsonify({'success': True})

@app.route('/api/telegram-channels/<ch_id>/test', methods=['POST'])
@require_login
def test_tg_channel(ch_id):
    with get_db() as conn:
        ch = conn.execute("SELECT * FROM telegram_channels WHERE id=? AND user_id=?",
                          (ch_id, session['user_id'])).fetchone()
    if not ch: return jsonify({'error': 'Not found'}), 404
    r = tg_send(ch['bot_token'], ch['chat_id'], "✅ HeartSafe — Channel connected! You'll receive SOS & live location alerts here.")
    if r and r.get('ok'): return jsonify({'success': True})
    return jsonify({'error': 'Failed. Check token and chat ID.'}), 400

@app.route('/api/telegram/test', methods=['POST'])
@require_login
def test_primary_tg():
    d = request.json
    r = tg_send(d['bot_token'], d['chat_id'], "✅ HeartSafe Primary Channel connected!")
    if r and r.get('ok'): return jsonify({'success': True})
    return jsonify({'error': 'Failed'}), 400

# ── Safety Contacts ────────────────────────────────────────────────────────────
@app.route('/api/safety-contacts', methods=['GET'])
@require_login
def get_contacts():
    with get_db() as conn:
        cs = conn.execute("SELECT * FROM safety_contacts WHERE user_id=?", (session['user_id'],)).fetchall()
    return jsonify([dict(c) for c in cs])

@app.route('/api/safety-contacts', methods=['POST'])
@require_login
def add_contact():
    d = request.json
    cid = uid()
    with get_db() as conn:
        conn.execute("INSERT INTO safety_contacts (id,user_id,name,relation,telegram_bot_token,telegram_chat_id,phone) VALUES (?,?,?,?,?,?,?)",
                     (cid, session['user_id'], d['name'], d.get('relation', ''),
                      d.get('telegram_bot_token', ''), d.get('telegram_chat_id', ''), d.get('phone', '')))
    sheets_append_bg('Safety_Contacts', [cid, session['user_id'], d['name'], d.get('relation', ''), d.get('phone', ''), now_str()])
    return jsonify({'success': True, 'id': cid})

@app.route('/api/safety-contacts/<cid>', methods=['DELETE'])
@require_login
def del_contact(cid):
    with get_db() as conn:
        conn.execute("DELETE FROM safety_contacts WHERE id=? AND user_id=?", (cid, session['user_id']))
    return jsonify({'success': True})

# ── SOS ────────────────────────────────────────────────────────────────────────
@app.route('/api/sos', methods=['POST'])
@require_login
def sos():
    d      = request.json
    uid_me = session['user_id']
    lat    = d.get('latitude')
    lon    = d.get('longitude')
    with get_db() as conn:
        user     = dict(conn.execute("SELECT * FROM users WHERE id=?", (uid_me,)).fetchone())
        contacts = conn.execute("SELECT * FROM safety_contacts WHERE user_id=?", (uid_me,)).fetchall()
        channels = conn.execute("SELECT * FROM telegram_channels WHERE user_id=? AND active=1", (uid_me,)).fetchall()
    msg  = user.get('sos_message') or '🆘 EMERGENCY! I need help!'
    maps = f"https://maps.google.com/?q={lat},{lon}" if lat and lon else "Location unavailable"
    full_msg = (f"🆘 <b>EMERGENCY SOS ALERT</b> 🆘\n\n"
                f"<b>Person:</b> {user['name']}\n"
                f"<b>Alert:</b> {msg}\n"
                f"📍 <b>Location:</b> {maps}\n"
                f"📐 <b>Coordinates:</b> {lat}, {lon}\n"
                f"🕐 <b>Time:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"⚠️ Please respond immediately or call emergency services: 112")
    sent = []
    if user.get('telegram_bot_token') and user.get('telegram_chat_id'):
        threading.Thread(target=tg_send, args=(user['telegram_bot_token'], user['telegram_chat_id'], full_msg), daemon=True).start()
        if lat and lon:
            threading.Thread(target=tg_location, args=(user['telegram_bot_token'], user['telegram_chat_id'], lat, lon), daemon=True).start()
        sent.append('Primary Channel')
    for ch in channels:
        ch = dict(ch)
        threading.Thread(target=tg_send, args=(ch['bot_token'], ch['chat_id'], full_msg), daemon=True).start()
        if lat and lon:
            threading.Thread(target=tg_location, args=(ch['bot_token'], ch['chat_id'], lat, lon), daemon=True).start()
        sent.append(ch['label'])
    for c in contacts:
        c = dict(c)
        if c.get('telegram_bot_token') and c.get('telegram_chat_id'):
            threading.Thread(target=tg_send, args=(c['telegram_bot_token'], c['telegram_chat_id'], full_msg), daemon=True).start()
            if lat and lon:
                threading.Thread(target=tg_location, args=(c['telegram_bot_token'], c['telegram_chat_id'], lat, lon), daemon=True).start()
            sent.append(c['name'])
    sos_id = uid()
    with get_db() as conn:
        conn.execute("INSERT INTO sos_alerts (id,user_id,latitude,longitude,message,sent_to) VALUES (?,?,?,?,?,?)",
                     (sos_id, uid_me, lat, lon, msg, json.dumps(sent)))
    sheets_append_bg('SOS_Alerts', [sos_id, uid_me, user['name'], str(lat), str(lon), msg, ','.join(sent), now_str()])
    return jsonify({'success': True, 'sent_to': sent, 'sos_id': sos_id})

# ── Live Location ──────────────────────────────────────────────────────────────
@app.route('/api/location/update', methods=['POST'])
@require_login
def update_location():
    d      = request.json
    uid_me = session['user_id']
    lat, lon, acc = d.get('latitude'), d.get('longitude'), d.get('accuracy')
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO location_shares (id,user_id,latitude,longitude,accuracy,updated_at) VALUES (?,?,?,?,?,datetime('now'))",
                     (uid(), uid_me, lat, lon, acc))
        conn.execute("UPDATE users SET latitude=?,longitude=?,live_location_active=1 WHERE id=?", (lat, lon, uid_me))
    return jsonify({'success': True})

@app.route('/api/location/broadcast', methods=['POST'])
@require_login
def broadcast_location():
    d      = request.json
    uid_me = session['user_id']
    lat, lon = d.get('latitude'), d.get('longitude')
    with get_db() as conn:
        user     = dict(conn.execute("SELECT * FROM users WHERE id=?", (uid_me,)).fetchone())
        contacts = conn.execute("SELECT * FROM safety_contacts WHERE user_id=?", (uid_me,)).fetchall()
        channels = conn.execute("SELECT * FROM telegram_channels WHERE user_id=? AND active=1", (uid_me,)).fetchall()
    maps = f"https://maps.google.com/?q={lat},{lon}"
    msg  = (f"📍 <b>LIVE LOCATION UPDATE</b>\n"
            f"<b>{user['name']}</b> is sharing live location\n"
            f"🗺 <a href=\"{maps}\">Open in Google Maps</a>\n"
            f"📐 {lat:.6f}, {lon:.6f}\n"
            f"🕐 {datetime.datetime.now().strftime('%H:%M:%S')}")
    sent = []
    if user.get('telegram_bot_token') and user.get('telegram_chat_id'):
        threading.Thread(target=tg_send, args=(user['telegram_bot_token'], user['telegram_chat_id'], msg), daemon=True).start()
        threading.Thread(target=tg_location, args=(user['telegram_bot_token'], user['telegram_chat_id'], lat, lon), daemon=True).start()
        sent.append('Primary')
    for ch in channels:
        ch = dict(ch)
        threading.Thread(target=tg_send, args=(ch['bot_token'], ch['chat_id'], msg), daemon=True).start()
        threading.Thread(target=tg_location, args=(ch['bot_token'], ch['chat_id'], lat, lon), daemon=True).start()
        sent.append(ch['label'])
    for c in contacts:
        c = dict(c)
        if c.get('telegram_bot_token') and c.get('telegram_chat_id'):
            threading.Thread(target=tg_send, args=(c['telegram_bot_token'], c['telegram_chat_id'], msg), daemon=True).start()
            threading.Thread(target=tg_location, args=(c['telegram_bot_token'], c['telegram_chat_id'], lat, lon), daemon=True).start()
            sent.append(c['name'])
    sheets_append_bg('Live_Locations', [uid_me, str(lat), str(lon), str(d.get('accuracy', '')), now_str()])
    return jsonify({'success': True, 'sent_to': sent})

@app.route('/api/location/stop', methods=['POST'])
@require_login
def stop_location():
    with get_db() as conn:
        conn.execute("UPDATE users SET live_location_active=0 WHERE id=?", (session['user_id'],))
    return jsonify({'success': True})

# ── Nearby ─────────────────────────────────────────────────────────────────────
@app.route('/api/nearby')
@require_login
def nearby():
    uid_me = session['user_id']
    radius = float(request.args.get('radius', 50))
    with get_db() as conn:
        me_row = conn.execute("SELECT latitude,longitude FROM users WHERE id=?", (uid_me,)).fetchone()
        if not me_row or not me_row['latitude']:
            return jsonify([])
        all_users = conn.execute("""SELECT id,name,age,gender,profile_photo,latitude,longitude,
            online,location_city,bio,is_bot,verified FROM users
            WHERE id!=? AND latitude IS NOT NULL AND longitude IS NOT NULL""", (uid_me,)).fetchall()
        blocked = {r['blocked_id'] for r in conn.execute("SELECT blocked_id FROM blocks WHERE blocker_id=?", (uid_me,)).fetchall()}
    result = []
    for u in all_users:
        if u['id'] in blocked: continue
        dist = haversine(me_row['latitude'], me_row['longitude'], u['latitude'], u['longitude'])
        if dist <= radius:
            row = dict(u)
            row['distance_km'] = round(dist, 1)
            result.append(row)
    result.sort(key=lambda x: x['distance_km'])
    return jsonify(result[:50])

@app.route('/api/nearby/request', methods=['POST'])
@require_login
def nearby_request():
    d      = request.json
    uid_me = session['user_id']
    try:
        rid = uid()
        with get_db() as conn:
            conn.execute("INSERT INTO nearby_requests (id,sender_id,receiver_id,message) VALUES (?,?,?,?)",
                         (rid, uid_me, d['receiver_id'], d.get('message', 'Hi! I noticed you are nearby.')))
        sheets_append_bg('Nearby_Requests', [rid, uid_me, d['receiver_id'], d.get('message', ''), now_str()])
        return jsonify({'success': True, 'id': rid})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Request already sent'}), 400

@app.route('/api/nearby/requests')
@require_login
def get_nearby_requests():
    uid_me = session['user_id']
    with get_db() as conn:
        reqs = conn.execute("""SELECT nr.*,u.name,u.profile_photo,u.age,u.location_city
            FROM nearby_requests nr JOIN users u ON nr.sender_id=u.id
            WHERE nr.receiver_id=? AND nr.status='pending'""", (uid_me,)).fetchall()
    return jsonify([dict(r) for r in reqs])

@app.route('/api/nearby/requests/<rid>/respond', methods=['POST'])
@require_login
def respond_nearby(rid):
    d      = request.json
    accept = d.get('accept', False)
    with get_db() as conn:
        req = conn.execute("SELECT * FROM nearby_requests WHERE id=? AND receiver_id=?",
                           (rid, session['user_id'])).fetchone()
        if not req: return jsonify({'error': 'Not found'}), 404
        conn.execute("UPDATE nearby_requests SET status=? WHERE id=?",
                     ('accepted' if accept else 'rejected', rid))
        match_id = None
        if accept:
            u1, u2 = sorted([req['sender_id'], req['receiver_id']])
            ex = conn.execute("SELECT id FROM matches WHERE user1_id=? AND user2_id=?", (u1, u2)).fetchone()
            if not ex:
                match_id = uid()
                conn.execute("INSERT INTO matches (id,user1_id,user2_id) VALUES (?,?,?)", (match_id, u1, u2))
    return jsonify({'success': True, 'match_id': match_id})

# ── Stories ────────────────────────────────────────────────────────────────────
@app.route('/api/stories')
@require_login
def get_stories():
    uid_me = session['user_id']
    with get_db() as conn:
        stories = conn.execute("""SELECT s.*,u.name,u.profile_photo FROM stories s
            JOIN users u ON s.user_id=u.id WHERE s.expires_at>datetime('now')
            AND (s.user_id=? OR s.user_id IN (
                SELECT CASE WHEN user1_id=? THEN user2_id ELSE user1_id END
                FROM matches WHERE user1_id=? OR user2_id=?))
            ORDER BY s.created_at DESC""", (uid_me, uid_me, uid_me, uid_me)).fetchall()
    result = []
    for s in stories:
        d = dict(s)
        d['views']  = json.loads(d.get('views') or '[]')
        d['viewed'] = uid_me in d['views']
        result.append(d)
    return jsonify(result)

@app.route('/api/stories', methods=['POST'])
@require_login
def create_story():
    if 'media' not in request.files: return jsonify({'error': 'No media'}), 400
    f    = request.files['media']
    ext  = os.path.splitext(f.filename)[1].lower()
    fname = f"story_{uid()}{ext}"
    f.save(os.path.join(UPLOAD_FOLDER, fname))
    url     = f"/static/uploads/{fname}"
    sid     = uid()
    expires = (datetime.datetime.now() + datetime.timedelta(hours=24)).isoformat()
    mt      = 'video' if ext in ['.mp4', '.mov', '.webm'] else 'image'
    with get_db() as conn:
        conn.execute("INSERT INTO stories (id,user_id,media_url,media_type,caption,expires_at) VALUES (?,?,?,?,?,?)",
                     (sid, session['user_id'], url, mt, request.form.get('caption', ''), expires))
    return jsonify({'success': True, 'story_id': sid})

@app.route('/api/stories/<sid>/view', methods=['POST'])
@require_login
def view_story(sid):
    uid_me = session['user_id']
    with get_db() as conn:
        s = conn.execute("SELECT views FROM stories WHERE id=?", (sid,)).fetchone()
        if s:
            views = json.loads(s['views'] or '[]')
            if uid_me not in views:
                views.append(uid_me)
                conn.execute("UPDATE stories SET views=? WHERE id=?", (json.dumps(views), sid))
    return jsonify({'success': True})

# ── Live ───────────────────────────────────────────────────────────────────────
@app.route('/api/live/start', methods=['POST'])
@require_login
def start_live():
    d      = request.json
    uid_me = session['user_id']
    sid    = uid()
    with get_db() as conn:
        conn.execute("UPDATE live_sessions SET active=0,ended_at=datetime('now') WHERE host_id=? AND active=1", (uid_me,))
        conn.execute("INSERT INTO live_sessions (id,host_id,title) VALUES (?,?,?)", (sid, uid_me, d.get('title', 'Live')))
    return jsonify({'success': True, 'session_id': sid})

@app.route('/api/live/active')
def get_lives():
    with get_db() as conn:
        lives = conn.execute("""SELECT ls.*,u.name,u.profile_photo FROM live_sessions ls
            JOIN users u ON ls.host_id=u.id WHERE ls.active=1 ORDER BY ls.created_at DESC""").fetchall()
    result = []
    for l in lives:
        d = dict(l)
        d['viewers']      = json.loads(d.get('viewers') or '[]')
        d['viewer_count'] = len(d['viewers'])
        result.append(d)
    return jsonify(result)

@app.route('/api/live/<sid>/join', methods=['POST'])
@require_login
def join_live(sid):
    uid_me = session['user_id']
    with get_db() as conn:
        l = conn.execute("SELECT * FROM live_sessions WHERE id=?", (sid,)).fetchone()
        if l:
            viewers = json.loads(l['viewers'] or '[]')
            if uid_me not in viewers:
                viewers.append(uid_me)
                conn.execute("UPDATE live_sessions SET viewers=? WHERE id=?", (json.dumps(viewers), sid))
    return jsonify({'success': True})

@app.route('/api/live/<sid>/end', methods=['POST'])
@require_login
def end_live(sid):
    with get_db() as conn:
        conn.execute("UPDATE live_sessions SET active=0,ended_at=datetime('now') WHERE id=? AND host_id=?",
                     (sid, session['user_id']))
    return jsonify({'success': True})

# ── Report / Block ─────────────────────────────────────────────────────────────
@app.route('/api/report', methods=['POST'])
@require_login
def report():
    d = request.json
    with get_db() as conn:
        conn.execute("INSERT INTO reports (id,reporter_id,reported_id,reason,details) VALUES (?,?,?,?,?)",
                     (uid(), session['user_id'], d['reported_id'], d['reason'], d.get('details', '')))
    return jsonify({'success': True})

@app.route('/api/block', methods=['POST'])
@require_login
def block():
    d = request.json
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO blocks (id,blocker_id,blocked_id) VALUES (?,?,?)",
                         (uid(), session['user_id'], d['blocked_id']))
    except sqlite3.IntegrityError:
        pass
    return jsonify({'success': True})

@app.route('/api/users/<user_id>')
@require_login
def get_user(user_id):
    with get_db() as conn:
        u = conn.execute("""SELECT id,name,age,gender,bio,interests,profile_photo,photos,location_city,
            height,education,job,relationship_goal,online,last_seen,verified,is_bot
            FROM users WHERE id=?""", (user_id,)).fetchone()
    if not u: return jsonify({'error': 'Not found'}), 404
    d = dict(u)
    try:    d['photos'] = json.loads(d.get('photos') or '[]')
    except: d['photos'] = []
    return jsonify(d)

# ── Startup ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    seed_bots()
    print(f"[Sheets] Fixed spreadsheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    threading.Thread(target=sheets_ensure_headers, daemon=True).start()
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
