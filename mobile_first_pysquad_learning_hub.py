import streamlit as st
import sqlite3
import hashlib
import base64
from datetime import datetime
import pandas as pd

# Page Configuration for Mobile-First Display
st.set_page_config(
    page_title="PySquad Hub",
    page_icon="🐍",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom Ultra-Modern Dark Theme CSS (Optimized for Mobile Screens)
st.markdown("""
<style>
    /* Hide Default Streamlit Elements for App-Like Feel */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Overall Background and Text Styling */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    
    /* Custom Responsive Video Container (Supports Fullscreen on Mobile) */
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
    
    /* Modern Card Layout for Videos and Tasks */
    .card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    /* Sleek Title and Badge UI */
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
        background-color: #238636;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    
    /* Streamlit Button Customizations */
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

# ----------------- DATABASE UTILITIES -----------------
DB_FILE = "learning_tracker.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        """)
        # Videos / Tasks Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                task_desc TEXT,
                date_added TEXT NOT NULL
            )
        """)
        # Video Views Tracker Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS views (
                username TEXT,
                video_id INTEGER,
                viewed_at TEXT,
                PRIMARY KEY (username, video_id)
            )
        """)
        # Task Submissions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                video_id INTEGER,
                screenshot TEXT, -- Base64 encoded string
                submitted_at TEXT,
                FOREIGN KEY (video_id) REFERENCES videos(id)
            )
        """)
        
        # Insert Admin User with password Touhidul#20 if not exists
        admin_pass_hash = hashlib.sha256("Touhidul#20".encode()).hexdigest()
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                           ("admin", admin_pass_hash, "admin"))
        conn.commit()

# Run database initialization
init_db()

# Helper to process Video URLs for direct responsive embedding
def get_embed_url(url):
    if "youtu.be/" in url:
        return "https://www.youtube.com/embed/" + url.split("youtu.be/")[1].split("?")[0]
    elif "youtube.com/watch" in url:
        try:
            return "https://www.youtube.com/embed/" + url.split("v=")[1].split("&")[0]
        except IndexError:
            return url
    return url

# Helper to convert uploaded files to Base64
def file_to_base64(uploaded_file):
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        return base64.b64encode(file_bytes).decode("utf-8")
    return None

# ----------------- SESSION STATE -----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "Home"

# ----------------- USER LOGIN / REGISTER -----------------
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

# ----------------- APP RENDERING -----------------

st.markdown("<h1 class='app-title'>🐍 PySquad Hub</h1>", unsafe_allow_html=True)
st.markdown("<div class='app-subtitle'>Learn Python together with structured tracking</div>", unsafe_allow_html=True)

if not st.session_state.logged_in:
    # Beautiful Custom Centered Form
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    auth_mode = st.radio("Choose Action", ["Login", "Register"], horizontal=True)
    
    username_input = st.text_input("Username", placeholder="e.g., Touhidul")
    password_input = st.text_input("Password", type="password", placeholder="Enter your password")
    
    if auth_mode == "Login":
        if st.button("Unlock Dashboard 🚀"):
            if username_input and password_input:
                if login_user(username_input, password_input):
                    st.success(f"Welcome back, {st.session_state.username}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Try again.")
            else:
                st.warning("Please fill out all fields.")
    else:
        if st.button("Create Account ✨"):
            if username_input and password_input:
                if len(password_input) < 4:
                    st.error("Password must be at least 4 characters long.")
                elif register_user(username_input, password_input):
                    st.success("Account created successfully! Please login.")
                else:
                    st.error("Username already taken.")
            else:
                st.warning("Please fill out all fields.")
    st.markdown("</div>", unsafe_allow_html=True)

else:
    # Native Mobile Navigation Bar
    st.markdown("---")
    nav_cols = st.columns(4 if st.session_state.role == "admin" else 3)
    
    with nav_cols[0]:
        if st.button("🎬 Videos"): st.session_state.current_tab = "Home"
    with nav_cols[1]:
        if st.button("📊 Tracker"): st.session_state.current_tab = "Tracker"
    with nav_cols[2]:
        if st.button("🔓 Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.role = None
            st.rerun()
    if st.session_state.role == "admin":
        with nav_cols[3]:
            if st.button("⚙️ Admin"): st.session_state.current_tab = "Admin"

    # ----------------- PAGE 1: VIDEO HUB (HOME) -----------------
    if st.session_state.current_tab == "Home":
        st.subheader("Your Video Assignments")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos ORDER BY id ASC")
            all_videos = cursor.fetchall()
            
        if not all_videos:
            st.info("No videos uploaded yet. Ask your group leader to post some!")
        else:
            for idx, vid in enumerate(all_videos):
                vid_id = vid["id"]
                st.markdown(f"<div class='card'>", unsafe_allow_html=True)
                st.markdown(f"<h3>Video #{idx+1}: {vid['title']}</h3>", unsafe_allow_html=True)
                
                # Check if already marked as watched
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM views WHERE username = ? AND video_id = ?", 
                                   (st.session_state.username, vid_id))
                    watched = cursor.fetchone() is not None
                
                if watched:
                    st.markdown("<span class='badge' style='background-color:#1f6feb;'>Watched ✅</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span class='badge' style='background-color:#da3633;'>Not Watched ❌</span>", unsafe_allow_html=True)
                
                st.write("")
                
                # Embed Video inside responsive wrapper with fullscreen enabled
                embed_link = get_embed_url(vid["url"])
                st.markdown(f"""
                    <div class="video-container">
                        <iframe src="{embed_link}" allowfullscreen></iframe>
                    </div>
                """, unsafe_allow_html=True)
                
                # Expandable Task Details
                with st.expander("📝 View Practice Task Details", expanded=True):
                    st.markdown(f"**Task Description:** \n{vid['task_desc']}")
                
                # Actions (Watch Logging & Screenshot Submission)
                col1, col2 = st.columns(2)
                with col1:
                    if not watched:
                        if st.button("Mark as Watched 👀", key=f"watch_btn_{vid_id}"):
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("INSERT OR IGNORE INTO views (username, video_id, viewed_at) VALUES (?, ?, ?)",
                                               (st.session_state.username, vid_id, datetime.now().strftime("%Y-%m-%d %H:%M")))
                                conn.commit()
                            st.success("Logged as watched!")
                            st.rerun()
                with col2:
                    # Submit task button/expander
                    with st.expander("📤 Submit Screenshot"):
                        up_file = st.file_uploader("Practice Screenshot", type=["png", "jpg", "jpeg"], key=f"up_{vid_id}")
                        comment = st.text_input("Add any comments/notes", key=f"comm_{vid_id}", placeholder="I completed this!")
                        if st.button("Submit Task 🚀", key=f"sub_btn_{vid_id}"):
                            if up_file:
                                b64_img = file_to_base64(up_file)
                                with get_db_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("INSERT INTO submissions (username, video_id, screenshot, submitted_at) VALUES (?, ?, ?, ?)",
                                                   (st.session_state.username, vid_id, b64_img, datetime.now().strftime("%Y-%m-%d %H:%M")))
                                    # Also auto-mark as watched
                                    cursor.execute("INSERT OR IGNORE INTO views (username, video_id, viewed_at) VALUES (?, ?, ?)",
                                                   (st.session_state.username, vid_id, datetime.now().strftime("%Y-%m-%d %H:%M")))
                                    conn.commit()
                                st.success("Task uploaded and submitted!")
                                st.rerun()
                            else:
                                st.error("Please select a screenshot file.")
                
                st.markdown("</div>", unsafe_allow_html=True)

    # ----------------- PAGE 2: PROGRESS TRACKER -----------------
    elif st.session_state.current_tab == "Tracker":
        st.subheader("Group Analytics & Submissions")
        
        with get_db_connection() as conn:
            # Load users (excluding admin)
            df_users = pd.read_sql_query("SELECT username FROM users WHERE role != 'admin'", conn)
            # Load total videos
            df_vids = pd.read_sql_query("SELECT id, title FROM videos", conn)
            # Load submissions
            df_subs = pd.read_sql_query("SELECT username, video_id FROM submissions", conn)
            
        if df_users.empty:
            st.info("No regular users registered yet.")
        elif df_vids.empty:
            st.info("No videos registered to track.")
        else:
            st.write("### 📉 Missing Task Tracker List")
            for _, u in df_users.iterrows():
                user = u["username"]
                completed_ids = set(df_subs[df_subs["username"] == user]["video_id"].tolist())
                all_ids = set(df_vids["id"].tolist())
                missing_ids = all_ids - completed_ids
                
                st.markdown(f"<div class='card' style='padding: 15px;'>", unsafe_allow_html=True)
                st.markdown(f"**👤 User:** `{user}`")
                if not missing_ids:
                    st.markdown("<span class='badge' style='background-color:#238636;'>All Tasks Submitted! 🔥</span>", unsafe_allow_html=True)
                else:
                    missing_labels = []
                    for m_id in missing_ids:
                        idx = df_vids[df_vids["id"] == m_id].index[0] + 1
                        missing_labels.append(f"Video {idx}")
                    st.markdown(f"🔴 **Missing Tasks:** {', '.join(missing_labels)}")
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Global feed of code submissions
            st.write("### 📸 Live Practice Screenshot Feed")
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
                st.info("No screenshots submitted by anyone yet.")
            else:
                for sub in all_subs:
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    st.markdown(f"**{sub['username']}** submitted **Practice Screenshot** for Video: `{sub['title']}`")
                    st.caption(f"Submitted on: {sub['submitted_at']}")
                    
                    # Decode base64 and display image safely
                    img_data = sub["screenshot"]
                    try:
                        st.image(base64.b64decode(img_data), use_column_width=True)
                    except Exception:
                        st.error("Error displaying screenshot.")
                    st.markdown("</div>", unsafe_allow_html=True)

    # ----------------- PAGE 3: ADMIN PANEL -----------------
    elif st.session_state.current_tab == "Admin" and st.session_state.role == "admin":
        st.subheader("Admin Control Panel")
        
        # Section A: Upload Video
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.write("### 🎬 Upload New Video Assignment")
        v_title = st.text_input("Video Title", placeholder="e.g., Python Lists and Tuples")
        v_url = st.text_input("Video URL (YouTube/Drive Link)", placeholder="e.g., https://www.youtube.com/watch?v=...")
        v_task = st.text_area("Task Description for Students", placeholder="Type what they need to practice...")
        
        if st.button("Publish Assignment 📣"):
            if v_title and v_url:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO videos (title, url, task_desc, date_added) VALUES (?, ?, ?, ?)",
                                   (v_title, v_url, v_task, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                st.success(f"Successfully published: {v_title}")
                st.rerun()
            else:
                st.error("Title and URL are required!")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section B: Viewers Tracking
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.write("### 👁️ View & Watch Logs per Video")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM videos")
            vids_list = cursor.fetchall()
            
        if vids_list:
            selected_vid = st.selectbox("Select Video to Check Viewers", 
                                        options=[v["id"] for v in vids_list], 
                                        format_func=lambda x: f"Video {x} - " + [v["title"] for v in vids_list if v["id"] == x][0])
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, viewed_at FROM views 
                    WHERE video_id = ?
                """, (selected_vid,))
                viewers = cursor.fetchall()
                
            if viewers:
                st.success(f"Total Viewers: {len(viewers)}")
                for vw in viewers:
                    st.write(f"- 👤 **{vw['username']}** (Watched at: {vw['viewed_at']})")
            else:
                st.warning("No one has logged watching this video yet.")
        else:
            st.info("No videos uploaded to track views.")
        st.markdown("</div>", unsafe_allow_html=True)
```
eof

### 📋 পাইথন প্রজেক্টটি ফ্রিতে হোস্ট ও রিকোয়েস্ট করার মাস্টার প্রম্পট (Prompt)

ভবিষ্যতে যদি এই প্রজেক্টে আরও কোনো নতুন ফিচার যুক্ত করতে চান বা কোড পরিবর্তন করতে চান, তাহলে নিচের প্রম্পটটি সরাসরি যেকোনো এআই চ্যাটে ব্যবহার করতে পারবেন:

```text
You are an expert full-stack developer. Optimize the existing single-file Streamlit web app (`app.py`) for a dedicated mobile-first learning platform called "PySquad Hub". The user base consists of students learning Python who access the portal primarily from their smartphones.

### Core Architecture & Technical Requirements:
1. **Framework:** Python 3 + Streamlit. Keep all components, backend logic, Custom CSS, and routing in a single file (`app.py`).
2. **Database System:** Use SQLite (`learning_tracker.db`) to keep the hosting completely free on Streamlit Community Cloud (no expensive external API/databases needed).
3. **Admin Controls:** Hardcode default credentials to: Username: `admin`, Password Hash of: `Touhidul#20`.

### Visual & Mobile UI Design Constraints:
1. **App-Like Styling:** Inject custom CSS to hide the standard Streamlit top banner, side menu, and standard footer. Use a dark background `#0d1117` and card borders `#30363d` for a modern, sleek developer feel.
2. **Responsive Mobile Video Player:** Wrap video widgets in a CSS iframe container that auto-scales dynamically (16:9 ratio) and supports full-screen toggle seamlessly on iOS/Android browsers.
3. **Custom Navigation:** Create custom action buttons at the top of the interface that behave like app tabs (Videos, Analytics/Leaderboard, Admin) so users don't have to open the sidebar.

### Feature Flow:
- **Videos:** Display list of lessons. Enable a "Mark as Watched" log that maps user action to the database.
- **Task Submission:** Enable files (PNG, JPG, JPEG) to be uploaded as practice screenshots under each video assignment. Convert files instantly to Base64 to save them safely as a text column inside SQLite.
- **Progress Tracker:** Display a clear "Missing Task List" for each student (e.g., "User Rahim is missing Video 3 Task, Video 4 Task").
- **Admin Panel:** Grant exclusive access to the 'admin' role. The admin must be able to:
  1. Post new Videos with Title, URL, and Task Descriptions.
  2. Select any video from a dropdown and see a list of usernames who watched it.
  3. Review all screenshot submissions with details of which student uploaded them for which video assignment.
```

### 🛠️ কিভাবে সাইটটি ফ্রিতে রান ও লাইভ করবেন:

১. **কম্পিউটারে রান করতে:**
   - আপনার কম্পিউটারে টার্মিনাল খুলে টাইপ করুন: `pip install streamlit pandas`
   - এরপর ফাইলটি যে ফোল্ডারে আছে সেখানে গিয়ে রান করুন: `streamlit run app.py`

২. **১০০% ফ্রিতে লাইভ হোস্ট করতে:**
   - কোডটি আপনার **GitHub** অ্যাকাউন্টে একটি রিপোজিটরি বানিয়ে পুশ (Upload) করুন।
   - **[Streamlit Community Cloud](https://share.streamlit.io/)**-এ গিয়ে ফ্রি অ্যাকাউন্ট তৈরি করুন এবং আপনার গিটহাবের সাথে কানেক্ট করুন।
   - আপনার রিপোজিটরি সিলেক্ট করে "Deploy" বাটনে ক্লিক করুন। 

আপনার বন্ধুদের লার্নিং গ্রুপকে দারুণভাবে পরিচালনা করার জন্য ওয়েবসাইটটি এখন পুরোপুরি প্রস্তুত! কোনো নতুন ফিচার যোগ করতে চাইলে বা কোনো জায়গায় বুঝতে সমস্যা হলে আমাকে জানাবেন।