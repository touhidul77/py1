import streamlit as st
import sqlite3
import hashlib
import base64
from datetime import datetime
import pandas as pd

# মোবাইলের জন্য রেসপনসিভ পেজ কনফিগারেশন
st.set_page_config(
    page_title="PySquad Hub",
    page_icon="🐍",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# মডার্ন ডার্ক থিম সিএসএস (মোবাইল ফ্রেন্ডলি ডিজাইন)
st.markdown("""
<style>
    /* স্ট্রিমলিটের ডিফল্ট হেডার-ফুটার হাইড করার জন্য */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ব্যাকগ্রাউন্ড ও টেক্সট কালার */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    
    /* রেসপনসিভ ইউটিউব ভিডিও প্লেয়ার (মোবাইলে ফুলস্ক্রিন সাপোর্ট করবে) */
    .video-container {
        position: relative;
        padding-bottom: 56.25%; /* 16:9 Aspect Ratio */
        height: 0;
        overflow: hidden;
        border-radius: 12px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        margin-bottom: 15px;
    }
    .video-container iframe {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        border: 0;
    }
    
    /* কার্ড ডিজাইন */
    .card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    /* টাইটেল এবং ব্যাজ স্টাইল */
    .app-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #58a6ff;
        text-align: center;
        margin-bottom: 5px;
        font-family: 'Inter', sans-serif;
    }
    .app-subtitle {
        font-size: 1rem;
        color: #8b949e;
        text-align: center;
        margin-bottom: 25px;
    }
    .badge {
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
    }
    
    /* বাটনের মডার্ন স্টাইল */
    div.stButton > button {
        background-color: #21262d !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        width: 100% !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #58a6ff !important;
        color: #0d1117 !important;
        border-color: #58a6ff !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- ডাটাবেজ ইউটিলিটি -----------------
DB_FILE = "learning_tracker.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # ইউজার টেবিল
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        """)
        # ভিডিও ও টাস্ক টেবিল
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                task_desc TEXT,
                date_added TEXT NOT NULL
            )
        """)
        # ভিডিও ভিউ ট্র্যাকিং টেবিল
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS views (
                username TEXT,
                video_id INTEGER,
                viewed_at TEXT,
                PRIMARY KEY (username, video_id)
            )
        """)
        # টাস্ক সাবমিশন টেবিল
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                video_id INTEGER,
                screenshot TEXT, -- Base64 ফরম্যাটে ছবি সেভ হবে
                submitted_at TEXT,
                FOREIGN KEY (video_id) REFERENCES videos(id)
            )
        """)
        
        # ডিফল্ট অ্যাডমিন অ্যাকাউন্ট তৈরি (Touhidul#20 পাসওয়ার্ড দিয়ে)
        admin_pass_hash = hashlib.sha256("Touhidul#20".encode()).hexdigest()
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                           ("admin", admin_pass_hash, "admin"))
        conn.commit()

# ডাটাবেজ চালু করা
init_db()

# ভিডিও লিংক প্রসেস করার ফাংশন (ইউটিউব এর জন্য এমবেড লিংক বের করবে)
def get_embed_url(url):
    if "youtu.be/" in url:
        return "https://www.youtube.com/embed/" + url.split("youtu.be/")[1].split("?")[0]
    elif "youtube.com/watch" in url:
        try:
            return "https://www.youtube.com/embed/" + url.split("v=")[1].split("&")[0]
        except IndexError:
            return url
    return url

# আপলোড করা ছবিকে Base64 টেক্সটে কনভার্ট করার ফাংশন
def file_to_base64(uploaded_file):
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        return base64.b64encode(file_bytes).decode("utf-8")
    return None

# ----------------- সেশন স্টেট (ইউজার লগইন ট্র্যাকিং) -----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "Home"

# ----------------- ইউজার লগইন ও রেজিস্টার সিস্টেম -----------------
def login_user(username, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_pw))
        user = cursor.fetchone()
        if user:
            st.session_state.logged_in = True
            st.session_state.username = user["username"]
            st.session_state.role = user["role"]
            return True
    return False

def register_user(username, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                           (username, hashed_pw, "user"))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False

# ----------------- অ্যাপ রেন্ডারিং -----------------

st.markdown("<h1 class='app-title'>🐍 PySquad Hub</h1>", unsafe_allow_html=True)
st.markdown("<div class='app-subtitle'>সবাই মিলে একসাথে পাইথন শিখি ও প্রোগ্রেস ট্র্যাক করি</div>", unsafe_allow_html=True)

if not st.session_state.logged_in:
    # লগইন ও সাইনআপ ফর্ম
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    auth_mode = st.radio("আপনার অ্যাকশন সিলেক্ট করুন", ["লগইন করুন", "নতুন অ্যাকাউন্ট খুলুন"], horizontal=True)
    
    username_input = st.text_input("ইউজারনেম (Username)", placeholder="যেমন: Touhidul")
    password_input = st.text_input("পাসওয়ার্ড (Password)", type="password", placeholder="পাসওয়ার্ড লিখুন")
    
    if auth_mode == "লগইন করুন":
        if st.button("ড্যাশবোর্ডে প্রবেশ করুন 🚀"):
            if username_input and password_input:
                if login_user(username_input, password_input):
                    st.success(f"স্বাগতম, {st.session_state.username}!")
                    st.rerun()
                else:
                    st.error("ভুল ইউজারনেম অথবা পাসওয়ার্ড! আবার চেষ্টা করুন।")
            else:
                st.warning("দয়া করে সবগুলো ঘর পূরণ করুন।")
    else:
        if st.button("রেজিস্ট্রেশন সম্পন্ন করুন ✨"):
            if username_input and password_input:
                if len(password_input) < 4:
                    st.error("পাসওয়ার্ড অন্তত ৪ অক্ষরের হতে হবে।")
                elif register_user(username_input, password_input):
                    st.success("অ্যাকাউন্ট তৈরি সফল হয়েছে! এখন লগইন করুন।")
                else:
                    st.error("এই ইউজারনেমটি ইতিমধ্যে ব্যবহৃত হয়েছে। অন্য নাম দিন।")
            else:
                st.warning("দয়া করে সবগুলো ঘর পূরণ করুন।")
    st.markdown("</div>", unsafe_allow_html=True)

else:
    # মোবাইলের জন্য সহজে ব্যবহারযোগ্য নেভিগেশন বার
    st.markdown("---")
    nav_cols = st.columns(4 if st.session_state.role == "admin" else 3)
    
    with nav_cols[0]:
        if st.button("🎬 ভিডিওসমূহ"): st.session_state.current_tab = "Home"
    with nav_cols[1]:
        if st.button("📊 ট্র্যাকার"): st.session_state.current_tab = "Tracker"
    with nav_cols[2]:
        if st.button("🔓 লগআউট"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.role = None
            st.rerun()
    if st.session_state.role == "admin":
        with nav_cols[3]:
            if st.button("⚙️ অ্যাডমিন"): st.session_state.current_tab = "Admin"

    # ----------------- পেজ ১: ভিডিও পোর্টাল (HOME) -----------------
    if st.session_state.current_tab == "Home":
        st.subheader("আপনার আজকের ক্লাসের ভিডিও")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos ORDER BY id ASC")
            all_videos = cursor.fetchall()
            
        if not all_videos:
            st.info("এখনো কোনো ভিডিও আপলোড করা হয়নি। গ্রুপ লিডারকে ভিডিও দেওয়ার জন্য বলুন!")
        else:
            for idx, vid in enumerate(all_videos):
                vid_id = vid["id"]
                st.markdown(f"<div class='card'>", unsafe_allow_html=True)
                st.markdown(f"<h3>ভিডিও #{idx+1}: {vid['title']}</h3>", unsafe_allow_html=True)
                
                # ভিডিও দেখা হয়েছে কিনা চেক করা
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM views WHERE username = ? AND video_id = ?", 
                                   (st.session_state.username, vid_id))
                    watched = cursor.fetchone() is not None
                
                if watched:
                    st.markdown("<span class='badge' style='background-color:#1f6feb;'>দেখেছি ✅</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span class='badge' style='background-color:#da3633;'>দেখা হয়নি ❌</span>", unsafe_allow_html=True)
                
                st.write("")
                
                # রেসপনসিভ ইউটিউব ভিডিও প্লেয়ার
                embed_link = get_embed_url(vid["url"])
                st.markdown(f"""
                    <div class="video-container">
                        <iframe src="{embed_link}" allowfullscreen></iframe>
                    </div>
                """, unsafe_allow_html=True)
                
                # প্র্যাকটিস টাস্কের বিবরণ
                with st.expander("📝 প্র্যাকটিস টাস্কের বিস্তারিত দেখুন", expanded=True):
                    st.markdown(f"**আজকের কাজ:** \n{vid['task_desc']}")
                
                # অ্যাকশন বাটনসমূহ
                col1, col2 = st.columns(2)
                with col1:
                    if not watched:
                        if st.button("দেখা শেষ করলাম 👀", key=f"watch_btn_{vid_id}"):
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("INSERT OR IGNORE INTO views (username, video_id, viewed_at) VALUES (?, ?, ?)",
                                               (st.session_state.username, vid_id, datetime.now().strftime("%Y-%m-%d %H:%M")))
                                conn.commit()
                            st.success("ভিডিও দেখা সফলভাবে সেভ হয়েছে!")
                            st.rerun()
                with col2:
                    # স্ক্রিনশট আপলোড সেকশন
                    with st.expander("📤 স্ক্রিনশট জমা দিন"):
                        up_file = st.file_uploader("আপনার প্র্যাকটিসের স্ক্রিনশট সিলেক্ট করুন", type=["png", "jpg", "jpeg"], key=f"up_{vid_id}")
                        comment = st.text_input("কোনো মন্তব্য থাকলে লিখুন", key=f"comm_{vid_id}", placeholder="ভাইয়া, আমার কোড ঠিকমতো কাজ করেছে!")
                        if st.button("টাস্ক সাবমিট করুন 🚀", key=f"sub_btn_{vid_id}"):
                            if up_file:
                                b64_img = file_to_base64(up_file)
                                with get_db_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("INSERT INTO submissions (username, video_id, screenshot, submitted_at) VALUES (?, ?, ?, ?)",
                                                   (st.session_state.username, vid_id, b64_img, datetime.now().strftime("%Y-%m-%d %H:%M")))
                                    # সাবমিট করলে অটোমেটিক্যালি ভিডিও দেখা কমপ্লিট হয়ে যাবে
                                    cursor.execute("INSERT OR IGNORE INTO views (username, video_id, viewed_at) VALUES (?, ?, ?)",
                                                   (st.session_state.username, vid_id, datetime.now().strftime("%Y-%m-%d %H:%M")))
                                    conn.commit()
                                st.success("আপনার টাস্কের স্ক্রিনশট সফলভাবে জমা হয়েছে!")
                                st.rerun()
                            else:
                                st.error("দয়া করে একটি ইমেজ বা স্ক্রিনশট সিলেক্ট করুন।")
                
                st.markdown("</div>", unsafe_allow_html=True)

    # ----------------- পেজ ২: প্রোগ্রেস ট্র্যাকার (TRACKER) -----------------
    elif st.session_state.current_tab == "Tracker":
        st.subheader("গ্রুপের বন্ধুদের কাজের ট্র্যাকিং")
        
        with get_db_connection() as conn:
            # অ্যাডমিন বাদে অন্য সব ইউজার
            df_users = pd.read_sql_query("SELECT username FROM users WHERE role != 'admin'", conn)
            # সর্বমোট ভিডিওর সংখ্যা
            df_vids = pd.read_sql_query("SELECT id, title FROM videos", conn)
            # সাবমিশন ডাটা
            df_subs = pd.read_sql_query("SELECT username, video_id FROM submissions", conn)
            
        if df_users.empty:
            st.info("এখনো কোনো মেম্বার রেজিস্ট্রেশন করেনি।")
        elif df_vids.empty:
            st.info("ট্র্যাক করার জন্য এখনো কোনো ভিডিও আপলোড করা হয়নি।")
        else:
            st.write("### 📉 কার কার কোন টাস্ক বাদ আছে?")
            for _, u in df_users.iterrows():
                user = u["username"]
                completed_ids = set(df_subs[df_subs["username"] == user]["video_id"].tolist())
                all_ids = set(df_vids["id"].tolist())
                missing_ids = all_ids - completed_ids
                
                st.markdown(f"<div class='card' style='padding: 15px;'>", unsafe_allow_html=True)
                st.markdown(f"**👤 মেম্বার:** `{user}`")
                if not missing_ids:
                    st.markdown("<span class='badge' style='background-color:#238636;'>সবগুলো টাস্ক সম্পন্ন করেছে! 🔥</span>", unsafe_allow_html=True)
                else:
                    missing_labels = []
                    for m_id in missing_ids:
                        idx = df_vids[df_vids["id"] == m_id].index[0] + 1
                        missing_labels.append(f"ভিডিও {idx}")
                    st.markdown(f"🔴 **বাকি আছে:** {', '.join(missing_labels)}")
                st.markdown("</div>", unsafe_allow_html=True)
            
            # বন্ধুদের জমা দেওয়া কাজের লাইভ ফিড
            st.write("### 📸 সবার জমা দেওয়া প্র্যাকটিস স্ক্রিনশটসমূহ")
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT s.username, s.submitted_at, s.screenshot, v.title, v.id as vid_id 
                    FROM submissions s 
                    JOIN videos v ON s.video_id = v.id 
                    ORDER BY s.id DESC
                """)
                all_subs = cursor.fetchall()
                
            if not all_subs:
                st.info("এখনো কেউ স্ক্রিনশট জমা দেয়নি।")
            else:
                for sub in all_subs:
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    st.markdown(f"👤 **{sub['username']}** স্ক্রিনশট জমা দিয়েছে - **ভিডিও: `{sub['title']}`**-এর জন্য")
                    st.caption(f"জমা দেওয়ার সময়: {sub['submitted_at']}")
                    
                    # Base64 থেকে ছবি ডিকোড করে দেখানো
                    img_data = sub["screenshot"]
                    try:
                        st.image(base64.b64decode(img_data), use_column_width=True)
                    except Exception:
                        st.error("ছবিটি লোড করতে সমস্যা হচ্ছে।")
                    st.markdown("</div>", unsafe_allow_html=True)

    # ----------------- পেজ ৩: অ্যাডমিন প্যানেল (ADMIN) -----------------
    elif st.session_state.current_tab == "Admin" and st.session_state.role == "admin":
        st.subheader("গ্রুপ লিডার কন্ট্রোল প্যানেল (অ্যাডমিন)")
        
        # সেকশন ১: নতুন ভিডিও আপলোড
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.write("### 🎬 নতুন ভিডিও ও টাস্ক আপলোড করুন")
        v_title = st.text_input("ভিডিওর শিরোনাম (যেমন: Python List Tutorial)", placeholder="শিরোনাম লিখুন...")
        v_url = st.text_input("ইউটিউব/ড্রাইভ ভিডিও লিংক", placeholder="যেমন: https://www.youtube.com/watch?v=...")
        v_task = st.text_area("আজকের প্র্যাকটিস কাজের বিবরণ", placeholder="বন্ধুদের কী কী কোড প্র্যাকটিস করতে হবে তা এখানে লিখুন...")
        
        if st.button("ভিডিও এবং টাস্ক পাবলিশ করুন 📣"):
            if v_title and v_url:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO videos (title, url, task_desc, date_added) VALUES (?, ?, ?, ?)",
                                   (v_title, v_url, v_task, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                st.success(f"সফলভাবে পাবলিশ করা হয়েছে: {v_title}")
                st.rerun()
            else:
                st.error("ভিডিওর শিরোনাম এবং লিংক অবশ্যই দিতে হবে!")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # সেকশন ২: ভিডিও অনুযায়ী কে কে দেখেছে তার তালিকা
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.write("### 👁️ কোন ভিডিও কে কে দেখেছে দেখুন")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM videos")
            vids_list = cursor.fetchall()
            
        if vids_list:
            selected_vid = st.selectbox("ভিডিও সিলেক্ট করুন", 
                                        options=[v["id"] for v in vids_list], 
                                        format_func=lambda x: f"ভিডিও {x} - " + [v["title"] for v in vids_list if v["id"] == x][0])
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, viewed_at FROM views 
                    WHERE video_id = ?
                """, (selected_vid,))
                viewers = cursor.fetchall()
                
            if viewers:
                st.success(f"মোট ভিউয়ার্স সংখ্যা: {len(viewers)} জন")
                for vw in viewers:
                    st.write(f"- 👤 **{vw['username']}** (দেখেছে: {vw['viewed_at']})")
            else:
                st.warning("এখনো কেউ এই ভিডিওটি দেখেছে হিসেবে মার্ক করেনি।")
        else:
            st.info("ভিউয়ার্স ট্র্যাক করার জন্য আগে ভিডিও আপলোড করুন।")
        st.markdown("</div>", unsafe_allow_html=True)
