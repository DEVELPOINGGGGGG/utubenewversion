import os
import sys
import socket
import tempfile
import threading
from flask import Flask, request, jsonify, render_template_string, send_file
import yt_dlp

# ==============================================================================
# 1. THREAD-AWARE GOOGLE / CLOUDFLARE DNS RESOLVER
# ==============================================================================
_original_getaddrinfo = socket.getaddrinfo
dns_state = threading.local()

try:
    import dns.resolver
    DNS_MODULE_AVAILABLE = True
except ImportError:
    DNS_MODULE_AVAILABLE = False

def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    use_bypass = getattr(dns_state, 'enable_dns_bypass', True)
    if use_bypass and DNS_MODULE_AVAILABLE and host:
        if any(d in host for d in ("youtube.com", "googlevideo.com", "youtu.be", "ytimg.com")):
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = ['8.8.8.8', '1.1.1.1', '8.8.4.4', '1.0.0.1']
                resolver.timeout = 2.0
                resolver.lifetime = 2.0
                answers = resolver.resolve(host, 'A')
                ip_addr = answers[0].to_text()
                return [(socket.AF_INET, type, proto, '', (ip_addr, port))]
            except Exception:
                pass
    return _original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = custom_getaddrinfo

# ==============================================================================
# 2. FLASK SERVER & ZEN UI
# ==============================================================================
app = Flask(__name__)

PEACEFUL_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zen Media Hub - 7-Tier Fallback</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0f172a;
            --bg-surface: #1e293b;
            --accent-primary: #38bdf8;
            --accent-secondary: #818cf8;
            --accent-peace: #34d399;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-soft: #334155;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: radial-gradient(circle at 50% 0%, #1e293b 0%, var(--bg-base) 75%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 24px;
        }
        .container {
            width: 100%;
            max-width: 600px;
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 28px;
            padding: 36px 32px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 24px; font-weight: 700; color: #fff; }
        .input-group { margin-bottom: 20px; }
        label { display: block; font-size: 13px; font-weight: 600; color: var(--text-muted); margin-bottom: 8px; }
        input[type="text"], select {
            width: 100%;
            padding: 14px 18px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-soft);
            border-radius: 16px;
            color: var(--text-main);
            font-size: 14px;
            outline: none;
        }
        input[type="text"]:focus, select:focus { border-color: var(--accent-primary); }
        .btn-action {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
            border: none;
            border-radius: 16px;
            color: #0f172a;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            margin-top: 10px;
        }
        .status-panel {
            margin-top: 24px;
            padding: 18px;
            border-radius: 16px;
            display: none;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-soft);
            font-size: 13.5px;
            line-height: 1.6;
        }
        .fallback-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px;
            margin-top: 20px;
        }
        .fallback-pill {
            font-size: 10.5px;
            font-weight: 600;
            padding: 6px 10px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-soft);
            border-radius: 8px;
            color: var(--text-muted);
        }
        .fallback-pill.active { color: var(--accent-peace); border-color: rgba(52, 211, 153, 0.3); background: rgba(52, 211, 153, 0.08); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ 7-Tier Resilient Downloader</h1>
        </div>
        <div class="input-group">
            <label>Media Link</label>
            <input type="text" id="videoUrl" placeholder="https://www.youtube.com/watch?v=...">
        </div>
        <div class="input-group">
            <label>Format</label>
            <select id="mediaFormat">
                <option value="video_best">Video (Best MP4)</option>
                <option value="audio_only">Audio Only (M4A/MP3)</option>
            </select>
        </div>
        <button class="btn-action" id="extractBtn" onclick="initiateExtraction()">Extract via Multi-Fallback</button>
        <div class="status-panel" id="statusPanel"></div>
        <div class="fallback-grid">
            <div class="fallback-pill active">1. Web Client (Cookies)</div>
            <div class="fallback-pill active">2. Android Client</div>
            <div class="fallback-pill active">3. IOS Client</div>
            <div class="fallback-pill active">4. TV Embedded Client</div>
            <div class="fallback-pill active">5. Web Creator Client</div>
            <div class="fallback-pill active">6. Embedded Music Client</div>
            <div class="fallback-pill active">7. Plain HTTP Fallback</div>
        </div>
    </div>
    <script>
        async function initiateExtraction() {
            const url = document.getElementById('videoUrl').value.trim();
            const format = document.getElementById('mediaFormat').value;
            const btn = document.getElementById('extractBtn');
            const panel = document.getElementById('statusPanel');
            if (!url) { alert("Please paste a link."); return; }
            btn.disabled = true;
            panel.style.display = 'block';
            panel.innerHTML = '🔄 Cycling through 7 fallback extraction tiers...';
            try {
                const response = await fetch('/api/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, format: format })
                });
                if (response.ok) {
                    panel.innerHTML = '✨ Success! Downloading file...';
                    const blob = await response.blob();
                    const link = document.createElement('a');
                    link.href = window.URL.createObjectURL(blob);
                    link.download = "media_download.mp4";
                    document.body.appendChild(link);
                    link.click();
                    link.remove();
                    panel.innerHTML = '🌿 Download complete.';
                } else {
                    const err = await response.json();
                    panel.innerHTML = `⚠️ All 7 tiers failed:<br><br>${err.error}`;
                }
            } catch (err) {
                panel.innerHTML = `⚠️ Network error: ${err.message}`;
            }
            btn.disabled = false;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(PEACEFUL_HTML_TEMPLATE)

# ==============================================================================
# 3. 7-TIER FALLBACK EXTRACTION PIPELINE
# ==============================================================================
EXTRACTION_TIERS = [
    {"name": "Tier 1: Web Client with Cookies", "client": "web", "force_ipv4": False},
    {"name": "Tier 2: Android Client", "client": "android", "force_ipv4": False},
    {"name": "Tier 3: iOS Client", "client": "ios", "force_ipv4": False},
    {"name": "Tier 4: TV Embedded Client", "client": "tv", "force_ipv4": False},
    {"name": "Tier 5: Web Creator Client", "client": "web_creator", "force_ipv4": False},
    {"name": "Tier 6: Embedded Music Client", "client": "mweb", "force_ipv4": False},
    {"name": "Tier 7: Direct Plain HTTP Fallback", "client": "web", "force_ipv4": True},
]

def build_ydl_options(format_type, output_dir, tier):
    opts = {
        'outtmpl': os.path.join(output_dir, '%(title).100s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'no_check_certificate': True,
        'legacyserverconnect': True,
        'cachedir': False,
        'extractor_args': {
            'youtube': {
                'player_client': [tier["client"]]
            }
        }
    }

    if tier["force_ipv4"]:
        opts['force_ipv4'] = True

    if format_type == 'audio_only':
        opts['format'] = 'm4a/bestaudio/best'
    else:
        opts['format'] = 'b[ext=mp4]/b/best'

    if os.path.exists("cookies.txt"):
        opts['cookiefile'] = "cookies.txt"

    return opts

@app.route('/api/extract', methods=['POST'])
def handle_extraction():
    payload = request.get_json()
    if not payload or 'url' not in payload:
        return jsonify({"error": "No URL provided"}), 400

    target_url = payload['url']
    format_type = payload.get('format', 'video_best')
    temp_dir = tempfile.mkdtemp()
    
    last_error = ""

    # Execute 7-Tier Fallback Loop
    for tier in EXTRACTION_TIERS:
        try:
            print(f"[PIPELINE] Executing {tier['name']}...", file=sys.stderr)
            ydl_opts = build_ydl_options(format_type, temp_dir, tier)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([target_url])

            downloaded_files = os.listdir(temp_dir)
            if not downloaded_files:
                continue

            target_file_path = os.path.join(temp_dir, downloaded_files[0])
            filename = os.path.basename(target_file_path)

            print(f"[PIPELINE] Success using {tier['name']}!", file=sys.stderr)
            return send_file(
                target_file_path,
                as_attachment=True,
                download_name=filename
            )

        except Exception as e:
            last_error = str(e)
            print(f"[PIPELINE] {tier['name']} failed: {last_error}", file=sys.stderr)

    return jsonify({
        "error": f"All 7 extraction mechanisms exhausted.\nLast Error: {last_error}"
    }), 500

# ==============================================================================
# 4. RUNNER
# ==============================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
