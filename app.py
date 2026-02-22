"""
HeartSafe Dating App v4 - Full Rebuild
New Features:
- Persistent session (permanent sessions, no logout on browser close)
- Username search with filters
- Feed/Posts system (create, like, comment)
- Account privacy (public/private toggle)
- Mobile-first responsive bottom nav (all visible)
- Follow/Unfollow system
- All components visible on mobile bottom nav
"""

from flask import Flask, render_template, request, jsonify, session, redirect, send_from_directory
import sqlite3, os, json, base64, uuid, hashlib, datetime, threading, time, math
import urllib.request, urllib.parse, urllib.error, ssl, subprocess, tempfile

app = Flask(__name__)

# ── Persistent Session Config ──────────────────────────────────────────────────
# Fixed stable secret key — never changes so sessions survive server restarts
app.secret_key = "HeartSafe$2024#StableKey!DoNotChange_v4_XyZ9"
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024

# Make sessions permanent (survive browser close / page refresh)
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=90)  # 90-day sessions

# Cookie settings — keep session across mobile browsers
app.config['SESSION_COOKIE_HTTPONLY']  = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'   # works on http too
app.config['SESSION_COOKIE_SECURE']   = False    # set True only with HTTPS
app.config['SESSION_COOKIE_NAME']     = 'heartsafe_session'
app.config['SESSION_COOKIE_PATH']     = '/'

@app.before_request
def make_session_permanent():
    """Force every request to keep the session alive."""
    session.permanent = True

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DB_PATH       = os.path.join(BASE_DIR, 'heartsafe_v4.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

GEMINI_API_KEY = "AIzaSyBqJD2DtB3xejohja21B0KAALCsvIA0Wuk"
GEMINI_URL     = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# ── Bot Profiles ───────────────────────────────────────────────────────────────
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
    {"name":"Aman Kapoor","age":27,"gender":"male","bio":"Architect & travel junkie ✈️ 20 countries. Need a co-pilot.","interests":"Travel,Architecture,Photography,Music","city":"Delhi","persona":"You are Aman, a well-traveled architect from Delhi. Adventurous, sophisticated. 1-3 sentences."},
    {"name":"Rohit Sharma","age":26,"gender":"male","bio":"Startup co-founder 🚀 Building EdTech for rural India.","interests":"Tech,Social Impact,Travel,Cricket","city":"Bangalore","persona":"You are Rohit, a passionate entrepreneur. 1-3 sentences."},
    {"name":"Vikram Singh","age":28,"gender":"male","bio":"Army officer 🎖️ Serving the nation, valuing loyalty.","interests":"Fitness,Travel,Reading,Mountains","city":"Dehradun","persona":"You are Vikram, a disciplined army officer. 1-3 sentences."},
    {"name":"Arjun Mehta","age":25,"gender":"male","bio":"Music producer 🎹 Made Bollywood beats. Looking for my muse.","interests":"Music,Bollywood,Travel,Photography","city":"Mumbai","persona":"You are Arjun, a creative music producer. Charismatic, artistic. 1-3 sentences."},
    {"name":"Karan Malhotra","age":29,"gender":"male","bio":"Cardiologist ❤️ Healing hearts professionally.","interests":"Medicine,Fitness,Travel,Books","city":"Delhi","persona":"You are Karan, a caring cardiologist. 1-3 sentences."},
]

# ── Gemini AI ──────────────────────────────────────────────────────────────────
def gemini_chat(persona, history, user_msg):
    try:
        parts = [{"text": f"System: {persona}\nBe warm and flirty but respectful. Max 2 sentences."}]
        for h in history[-6:]:
            parts.append({"text": f"{'User' if h['role']=='user' else 'You'}: {h['content']}"})
        parts.append({"text": f"User: {user_msg}\nYou:"})
        body = json.dumps({"contents":[{"parts":parts}],"generationConfig":{"maxOutputTokens":120,"temperature":0.9}}).encode()
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
            verified INTEGER DEFAULT 0, premium INTEGER DEFAULT 0,
            is_private INTEGER DEFAULT 0,
            follower_count INTEGER DEFAULT 0,
            following_count INTEGER DEFAULT 0,
            post_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS follows (
            id TEXT PRIMARY KEY, follower_id TEXT NOT NULL,
            following_id TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(follower_id, following_id)
        );
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
            caption TEXT, media_url TEXT, media_type TEXT DEFAULT 'image',
            like_count INTEGER DEFAULT 0, comment_count INTEGER DEFAULT 0,
            visibility TEXT DEFAULT 'public',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS post_likes (
            id TEXT PRIMARY KEY, post_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(post_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS post_comments (
            id TEXT PRIMARY KEY, post_id TEXT NOT NULL,
            user_id TEXT NOT NULL, content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
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
        CREATE TABLE IF NOT EXISTS stories (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
            media_url TEXT NOT NULL, media_type TEXT DEFAULT 'image',
            caption TEXT, views TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')), expires_at TEXT
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
        CREATE TABLE IF NOT EXISTS blocks (
            id TEXT PRIMARY KEY, blocker_id TEXT NOT NULL,
            blocked_id TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(blocker_id, blocked_id)
        );
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY, reporter_id TEXT NOT NULL,
            reported_id TEXT NOT NULL, reason TEXT NOT NULL,
            details TEXT, created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS location_shares (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL UNIQUE,
            latitude REAL, longitude REAL, accuracy REAL,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        """)
    print("[DB] v4 Initialized")

# ── Utilities ──────────────────────────────────────────────────────────────────
def _dicebear_url(name, gender):
    seed  = name.replace(' ', '')
    style = 'adventurer' if gender == 'female' else 'big-smile'
    return f"https://api.dicebear.com/7.x/{style}/svg?seed={seed}&backgroundColor=b6e3f4,c0aede,d1d4f9,ffd5dc&radius=50"

def haversine(lat1, lon1, lat2, lon2):
    R    = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a    = (math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))

def hp(pw):     return hashlib.sha256(pw.encode()).hexdigest()
def cpw(pw, h): return hp(pw) == h
def uid():      return str(uuid.uuid4())
def now_str():  return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

ALLOWED_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov'}

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

def seed_bots():
    import random
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM users WHERE is_bot=1").fetchone()[0]
        if count < 10:
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
                     relationship_goal,looking_for,verified,profile_photo,is_private)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
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
                    _dicebear_url(bot['name'], bot['gender']),
                    0
                ))
            # Seed some bot posts
            all_bots = conn.execute("SELECT id,name FROM users WHERE is_bot=1").fetchall()
            post_captions = [
                "Beautiful morning in the city! 🌅 Starting the day with chai ☕",
                "Just finished my yoga session 🧘‍♀️ Feeling so refreshed and alive!",
                "Cooked something special today 🍳 Food is love!",
                "Weekend adventures call ✈️ Where should I explore next?",
                "Late night thoughts and stargazing 🌟 Life is beautiful.",
                "New book day! 📚 Any recommendations for me?",
                "Rainy day vibes and hot coffee ☔ Bliss!",
                "Training session done 💪 Hard work pays off!",
            ]
            import random
            for bot in all_bots:
                existing = conn.execute("SELECT COUNT(*) FROM posts WHERE user_id=?", (bot['id'],)).fetchone()[0]
                if existing == 0:
                    for j in range(random.randint(1, 3)):
                        conn.execute("INSERT OR IGNORE INTO posts (id,user_id,caption,like_count,comment_count,visibility) VALUES (?,?,?,?,?,?)",
                            (uid(), bot['id'], random.choice(post_captions), random.randint(5, 120), random.randint(0, 20), 'public'))
            print("[Bots] Seeded successfully")

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
                (id,username,email,password_hash,name,age,gender,bio,interests,looking_for,relationship_goal,is_private)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (user_id, d['username'], d['email'], hp(d['password']),
                 d['name'], d.get('age', 18), d.get('gender', 'female'),
                 d.get('bio', ''), d.get('interests', ''),
                 d.get('looking_for', 'male'), d.get('goal', 'relationship'),
                 1 if d.get('is_private') else 0))
        session.permanent = True
        session['user_id'] = user_id
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
        session.permanent = True
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
    # Renew the session on every /api/me call (heartbeat)
    session.modified = True
    with get_db() as conn:
        u = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    if not u: return jsonify({'error': 'Not found'}), 404
    d = dict(u)
    d.pop('password_hash', None)
    d.pop('bot_persona', None)
    try:    d['photos'] = json.loads(d.get('photos') or '[]')
    except: d['photos'] = []
    return jsonify(d)

@app.route('/api/session-info')
@require_login
def session_info():
    """Return info about the current session."""
    uid_me = session['user_id']
    exp = datetime.datetime.now() + app.config['PERMANENT_SESSION_LIFETIME']
    return jsonify({
        'user_id': uid_me,
        'session_cookie': app.config['SESSION_COOKIE_NAME'],
        'expires': exp.strftime('%Y-%m-%d %H:%M:%S'),
        'days_remaining': 90,
        'permanent': True,
    })

@app.route('/api/profile', methods=['PUT'])
@require_login
def update_profile():
    d = request.json
    allowed = ['name','age','bio','interests','location_city','looking_for','height','education',
               'job','relationship_goal','telegram_bot_token','telegram_chat_id','sos_message','is_private']
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

# ── Search Users ───────────────────────────────────────────────────────────────
@app.route('/api/search/users')
@require_login
def search_users():
    q      = request.args.get('q', '').strip()
    gender = request.args.get('gender', '')
    city   = request.args.get('city', '')
    min_age = request.args.get('min_age', '')
    max_age = request.args.get('max_age', '')
    uid_me  = session['user_id']

    if not q and not gender and not city and not min_age and not max_age:
        return jsonify([])

    conditions = ["id != ?", "is_bot = 0"]
    params = [uid_me]

    if q:
        conditions.append("(username LIKE ? OR name LIKE ? OR location_city LIKE ? OR interests LIKE ?)")
        like = f"%{q}%"
        params += [like, like, like, like]
    if gender:
        conditions.append("gender = ?")
        params.append(gender)
    if city:
        conditions.append("location_city LIKE ?")
        params.append(f"%{city}%")
    if min_age:
        conditions.append("age >= ?")
        params.append(int(min_age))
    if max_age:
        conditions.append("age <= ?")
        params.append(int(max_age))

    sql = f"""SELECT id,username,name,age,gender,bio,profile_photo,location_city,
        interests,verified,online,is_private FROM users
        WHERE {' AND '.join(conditions)} ORDER BY online DESC, name ASC LIMIT 30"""

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        result.append(d)
    return jsonify(result)

# ── Feed / Posts ───────────────────────────────────────────────────────────────
@app.route('/api/feed')
@require_login
def get_feed():
    uid_me = session['user_id']
    page   = int(request.args.get('page', 1))
    limit  = 20
    offset = (page - 1) * limit

    with get_db() as conn:
        # Get posts from public accounts + followed users + self
        following_ids = [r['following_id'] for r in conn.execute(
            "SELECT following_id FROM follows WHERE follower_id=? AND status='active'", (uid_me,)).fetchall()]
        following_ids.append(uid_me)

        # Public posts + following posts
        ph = ','.join('?' * len(following_ids))
        posts = conn.execute(f"""
            SELECT p.*, u.name, u.username, u.profile_photo, u.verified, u.is_private,
                (SELECT 1 FROM post_likes WHERE post_id=p.id AND user_id=?) as liked_by_me
            FROM posts p JOIN users u ON p.user_id=u.id
            WHERE (u.is_private=0 OR p.user_id IN ({ph}))
            AND p.user_id NOT IN (SELECT blocked_id FROM blocks WHERE blocker_id=?)
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
        """, [uid_me] + following_ids + [uid_me, limit, offset]).fetchall()

    result = []
    for p in posts:
        d = dict(p)
        d['liked_by_me'] = bool(d.get('liked_by_me'))
        result.append(d)
    return jsonify(result)

@app.route('/api/posts/user/<user_id>')
@require_login
def get_user_posts(user_id):
    uid_me = session['user_id']
    with get_db() as conn:
        u = conn.execute("SELECT is_private FROM users WHERE id=?", (user_id,)).fetchone()
        if not u:
            return jsonify({'error': 'User not found'}), 404

        # Check if private account and not following
        if u['is_private'] and user_id != uid_me:
            is_following = conn.execute(
                "SELECT id FROM follows WHERE follower_id=? AND following_id=? AND status='active'",
                (uid_me, user_id)).fetchone()
            if not is_following:
                return jsonify({'private': True, 'posts': []})

        posts = conn.execute("""
            SELECT p.*, u.name, u.username, u.profile_photo, u.verified,
                (SELECT 1 FROM post_likes WHERE post_id=p.id AND user_id=?) as liked_by_me
            FROM posts p JOIN users u ON p.user_id=u.id
            WHERE p.user_id=? ORDER BY p.created_at DESC LIMIT 50
        """, (uid_me, user_id)).fetchall()

    result = [dict(p) for p in posts]
    for r in result:
        r['liked_by_me'] = bool(r.get('liked_by_me'))
    return jsonify({'private': False, 'posts': result})

@app.route('/api/posts', methods=['POST'])
@require_login
def create_post():
    uid_me   = session['user_id']
    caption  = request.form.get('caption', '')
    visibility = request.form.get('visibility', 'public')
    media_url = None
    media_type = 'text'

    if 'media' in request.files:
        f = request.files['media']
        if f.filename:
            url = save_upload(f)
            if url:
                media_url  = url
                ext = os.path.splitext(f.filename)[1].lower()
                media_type = 'video' if ext in ['.mp4','.mov','.webm'] else 'image'

    post_id = uid()
    with get_db() as conn:
        conn.execute("INSERT INTO posts (id,user_id,caption,media_url,media_type,visibility) VALUES (?,?,?,?,?,?)",
                     (post_id, uid_me, caption, media_url, media_type, visibility))
        conn.execute("UPDATE users SET post_count=post_count+1 WHERE id=?", (uid_me,))
    return jsonify({'success': True, 'post_id': post_id})

@app.route('/api/posts/<post_id>/like', methods=['POST'])
@require_login
def like_post(post_id):
    uid_me = session['user_id']
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM post_likes WHERE post_id=? AND user_id=?", (post_id, uid_me)).fetchone()
        if existing:
            conn.execute("DELETE FROM post_likes WHERE post_id=? AND user_id=?", (post_id, uid_me))
            conn.execute("UPDATE posts SET like_count=MAX(0,like_count-1) WHERE id=?", (post_id,))
            return jsonify({'liked': False})
        else:
            conn.execute("INSERT INTO post_likes (id,post_id,user_id) VALUES (?,?,?)", (uid(), post_id, uid_me))
            conn.execute("UPDATE posts SET like_count=like_count+1 WHERE id=?", (post_id,))
            return jsonify({'liked': True})

@app.route('/api/posts/<post_id>/comments')
@require_login
def get_comments(post_id):
    with get_db() as conn:
        comments = conn.execute("""
            SELECT pc.*, u.name, u.username, u.profile_photo
            FROM post_comments pc JOIN users u ON pc.user_id=u.id
            WHERE pc.post_id=? ORDER BY pc.created_at ASC
        """, (post_id,)).fetchall()
    return jsonify([dict(c) for c in comments])

@app.route('/api/posts/<post_id>/comments', methods=['POST'])
@require_login
def add_comment(post_id):
    d = request.json
    content = d.get('content', '').strip()
    if not content: return jsonify({'error': 'Empty comment'}), 400
    cid = uid()
    uid_me = session['user_id']
    with get_db() as conn:
        conn.execute("INSERT INTO post_comments (id,post_id,user_id,content) VALUES (?,?,?,?)",
                     (cid, post_id, uid_me, content))
        conn.execute("UPDATE posts SET comment_count=comment_count+1 WHERE id=?", (post_id,))
    return jsonify({'success': True, 'comment_id': cid})

@app.route('/api/posts/<post_id>', methods=['DELETE'])
@require_login
def delete_post(post_id):
    uid_me = session['user_id']
    with get_db() as conn:
        p = conn.execute("SELECT user_id FROM posts WHERE id=?", (post_id,)).fetchone()
        if not p or p['user_id'] != uid_me:
            return jsonify({'error': 'Not authorized'}), 403
        conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
        conn.execute("DELETE FROM post_likes WHERE post_id=?", (post_id,))
        conn.execute("DELETE FROM post_comments WHERE post_id=?", (post_id,))
        conn.execute("UPDATE users SET post_count=MAX(0,post_count-1) WHERE id=?", (uid_me,))
    return jsonify({'success': True})

# ── Follow System ──────────────────────────────────────────────────────────────
@app.route('/api/follow/<target_id>', methods=['POST'])
@require_login
def follow_user(target_id):
    uid_me = session['user_id']
    if uid_me == target_id:
        return jsonify({'error': 'Cannot follow yourself'}), 400
    with get_db() as conn:
        existing = conn.execute("SELECT id,status FROM follows WHERE follower_id=? AND following_id=?",
                                (uid_me, target_id)).fetchone()
        if existing:
            conn.execute("DELETE FROM follows WHERE follower_id=? AND following_id=?", (uid_me, target_id))
            conn.execute("UPDATE users SET follower_count=MAX(0,follower_count-1) WHERE id=?", (target_id,))
            conn.execute("UPDATE users SET following_count=MAX(0,following_count-1) WHERE id=?", (uid_me,))
            return jsonify({'following': False})
        else:
            conn.execute("INSERT INTO follows (id,follower_id,following_id) VALUES (?,?,?)",
                         (uid(), uid_me, target_id))
            conn.execute("UPDATE users SET follower_count=follower_count+1 WHERE id=?", (target_id,))
            conn.execute("UPDATE users SET following_count=following_count+1 WHERE id=?", (uid_me,))
            return jsonify({'following': True})

@app.route('/api/follow/<target_id>/status')
@require_login
def follow_status(target_id):
    uid_me = session['user_id']
    with get_db() as conn:
        f = conn.execute("SELECT id FROM follows WHERE follower_id=? AND following_id=? AND status='active'",
                         (uid_me, target_id)).fetchone()
    return jsonify({'following': bool(f)})

# ── User Profile Public View ───────────────────────────────────────────────────
@app.route('/api/users/<user_id>')
@require_login
def get_user(user_id):
    uid_me = session['user_id']
    with get_db() as conn:
        u = conn.execute("""SELECT id,username,name,age,gender,bio,interests,profile_photo,photos,location_city,
            height,education,job,relationship_goal,online,last_seen,verified,is_bot,is_private,
            follower_count,following_count,post_count FROM users WHERE id=?""", (user_id,)).fetchone()
        if not u: return jsonify({'error': 'Not found'}), 404
        d = dict(u)
        try:    d['photos'] = json.loads(d.get('photos') or '[]')
        except: d['photos'] = []
        # Check follow status
        f = conn.execute("SELECT id FROM follows WHERE follower_id=? AND following_id=? AND status='active'",
                         (uid_me, user_id)).fetchone()
        d['is_following'] = bool(f)
        d['is_me'] = (uid_me == user_id)
    return jsonify(d)

# ── Discover ───────────────────────────────────────────────────────────────────
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
        real = conn.execute(
            f"SELECT {cols} FROM users WHERE id NOT IN ({ph}) AND is_bot=0 ORDER BY online DESC, last_seen DESC LIMIT 20", excl).fetchall()
        bots = conn.execute(
            f"SELECT {cols} FROM users WHERE id NOT IN ({ph}) AND is_bot=1 ORDER BY RANDOM() LIMIT 10", excl).fetchall()

    def to_d(u):
        d = dict(u)
        try:    d['photos'] = json.loads(d.get('photos') or '[]')
        except: d['photos'] = []
        return d

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
            unread = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE match_id=? AND sender_id!=? AND read_at IS NULL",
                (m['match_id'], uid_me)).fetchone()[0]
            if other:
                result.append({'match_id': m['match_id'], 'matched_at': m['created_at'],
                                'user': dict(other), 'last_message': dict(lm) if lm else None,
                                'unread': unread})
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
    return jsonify({'success': True, 'message_id': msg_id})

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
    sos_id = uid()
    with get_db() as conn:
        conn.execute("INSERT INTO sos_alerts (id,user_id,latitude,longitude,message,sent_to) VALUES (?,?,?,?,?,?)",
                     (sos_id, uid_me, lat, lon, 'SOS Alert', json.dumps(['app'])))
    return jsonify({'success': True, 'sos_id': sos_id})

# ── Stories ────────────────────────────────────────────────────────────────────
@app.route('/api/stories')
@require_login
def get_stories():
    uid_me = session['user_id']
    with get_db() as conn:
        stories = conn.execute("""SELECT s.*,u.name,u.username,u.profile_photo FROM stories s
            JOIN users u ON s.user_id=u.id WHERE s.expires_at>datetime('now')
            ORDER BY s.created_at DESC LIMIT 50""").fetchall()
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
    f = request.files['media']
    url = save_upload(f)
    if not url: return jsonify({'error': 'Invalid file'}), 400
    sid     = uid()
    expires = (datetime.datetime.now() + datetime.timedelta(hours=24)).isoformat()
    ext     = os.path.splitext(f.filename)[1].lower()
    mt      = 'video' if ext in ['.mp4', '.mov', '.webm'] else 'image'
    with get_db() as conn:
        conn.execute("INSERT INTO stories (id,user_id,media_url,media_type,caption,expires_at) VALUES (?,?,?,?,?,?)",
                     (sid, session['user_id'], url, mt, request.form.get('caption', ''), expires))
    return jsonify({'success': True, 'story_id': sid})

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

# ── Location ───────────────────────────────────────────────────────────────────
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

# ── Stats ──────────────────────────────────────────────────────────────────────
@app.route('/api/stats')
@require_login
def get_stats():
    uid_me = session['user_id']
    with get_db() as conn:
        matches = conn.execute("SELECT COUNT(*) FROM matches WHERE user1_id=? OR user2_id=?", (uid_me, uid_me)).fetchone()[0]
        posts   = conn.execute("SELECT COUNT(*) FROM posts WHERE user_id=?", (uid_me,)).fetchone()[0]
        followers = conn.execute("SELECT COUNT(*) FROM follows WHERE following_id=? AND status='active'", (uid_me,)).fetchone()[0]
        following = conn.execute("SELECT COUNT(*) FROM follows WHERE follower_id=? AND status='active'", (uid_me,)).fetchone()[0]
        likes_got = conn.execute("SELECT COALESCE(SUM(like_count),0) FROM posts WHERE user_id=?", (uid_me,)).fetchone()[0]
    return jsonify({'matches': matches, 'posts': posts, 'followers': followers, 'following': following, 'likes_got': likes_got})

if __name__ == '__main__':
    init_db()
    seed_bots()
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
