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
    print("[DNS] 'dnspython' not installed. System DNS will be used.", file=sys.stderr)

def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    use_bypass = getattr(dns_state, 'enable_dns_bypass', True)
    
    if use_bypass and DNS_MODULE_AVAILABLE and host:
        youtube_domains = ("youtube.com", "googlevideo.com", "youtu.be", "ytimg.com")
        if any(d in host for d in youtube_domains):
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = ['8.8.8.8', '1.1.1.1', '8.8.4.4', '1.0.0.1']
                resolver.timeout = 2.5
                resolver.lifetime = 2.5
                answers = resolver.resolve(host, 'A')
                ip_addr = answers[0].to_text()
                return [(socket.AF_INET, type, proto, '', (ip_addr, port))]
            except Exception:
                pass
                
    return _original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = custom_getaddrinfo

# ==============================================================================
# 2. FLASK SERVER & PEACEFUL ZEN UI
# ==============================================================================
app = Flask(__name__)

PEACEFUL_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zen Media Hub</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0f172a;
            --bg-surface: #1e293b;
            --bg-elevated: #334155;
            --accent-primary: #38bdf8;
            --accent-secondary: #818cf8;
            --accent-peace: #34d399;
            --accent-warning: #fbbf24;
            --accent-danger: #f87171;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-soft: #334155;
            --border-highlight: #475569;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
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
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 28px;
            padding: 36px 32px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
        }

        .header-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(56, 189, 248, 0.1);
            color: var(--accent-primary);
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
            border: 1px solid rgba(56, 189, 248, 0.2);
        }

        .header h1 {
            font-size: 26px;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #ffffff 0%, var(--text-muted) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .input-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 8px;
        }

        input[type="text"], select {
            width: 100%;
            padding: 14px 18px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-soft);
            border-radius: 16px;
            color: var(--text-main);
            font-size: 14px;
            font-family: inherit;
            outline: none;
            transition: all 0.2s ease;
        }

        input[type="text"]:focus, select:focus {
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.15);
            background: rgba(15, 23, 42, 0.85);
        }

        .btn-action {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
            border: none;
            border-radius: 16px;
            color: #0f172a;
            font-size: 15px;
            font-weight: 700;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 10px 20px -5px rgba(56, 189, 248, 0.3);
            margin-top: 10px;
        }

        .btn-action:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 25px -5px rgba(56, 189, 248, 0.45);
        }

        .btn-action:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
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

        .pulse-ring {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: var(--accent-primary);
            box-shadow: 0 0 0 rgba(56, 189, 248, 0.4);
            animation: pulse 1.8s infinite;
            margin-right: 8px;
        }

        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(56, 189, 248, 0); }
            100% { box-shadow: 0 0 0 0 rgba(56, 189, 248, 0); }
        }

        .bypass-pill-list {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 20px;
        }

        .bypass-pill {
            font-size: 11px;
            font-weight: 600;
            padding: 4px 10px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-soft);
            border-radius: 8px;
            color: var(--text-muted);
        }

        .bypass-pill.active {
            color: var(--accent-peace);
            border-color: rgba(52, 211, 153, 0.3);
            background: rgba(52, 211, 153, 0.08);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-badge">
                <span>🍃</span> <span>CALM & RESILIENT</span>
            </div>
            <h1>Zen Video Extraction</h1>
        </div>

        <div class="input-group">
            <label for="videoUrl">Media Link</label>
            <input type="text" id="videoUrl" placeholder="https://www.youtube.com/watch?v=..." autocomplete="off">
        </div>

        <div class="input-group">
            <label for="mediaFormat">Extraction Target</label>
            <select id="mediaFormat">
                <option value="video_best">Video (Best Quality MP4)</option>
                <option value="audio_only">Audio Only (MP3 / M4A)</option>
            </select>
        </div>

        <button class="btn-action" id="extractBtn" onclick="initiateExtraction()">
            Begin Clean Download
        </button>

        <div class="status-panel" id="statusPanel"></div>

        <div class="bypass-pill-list">
            <div class="bypass-pill active">✓ Google DNS (8.8.8.8)</div>
            <div class="bypass-pill active">✓ Cloudflare (1.1.1.1)</div>
            <div class="bypass-pill" id="cookiePill">○ cookies.txt (Checking...)</div>
            <div class="bypass-pill active">✓ Client Spoofing</div>
        </div>
    </div>

    <script>
        // Check cookie status on page load
        fetch('/api/cookie_status')
            .then(r => r.json())
            .then(data => {
                const pill = document.getElementById('cookiePill');
                if (data.present) {
                    pill.className = 'bypass-pill active';
                    pill.innerText = '✓ cookies.txt Loaded';
                } else {
                    pill.innerText = '○ cookies.txt Optional';
                }
            })
            .catch(() => {});

        async function initiateExtraction() {
            const url = document.getElementById('videoUrl').value.trim();
            const format = document.getElementById('mediaFormat').value;
            const btn = document.getElementById('extractBtn');
            const panel = document.getElementById('statusPanel');

            if (!url) {
                alert("Please paste a valid link.");
                return;
            }

            btn.disabled = true;
            panel.style.display = 'block';
            panel.style.borderColor = 'var(--border-soft)';
            panel.innerHTML = '<span class="pulse-ring"></span> Resolving stream securely through bypass pipeline...';

            try {
                const response = await fetch('/api/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, format: format })
                });

                if (response.ok) {
                    panel.style.borderColor = 'rgba(52, 211, 153, 0.4)';
                    panel.innerHTML = '✨ Stream acquired. Streaming file to your system...';

                    const contentDisp = response.headers.get('Content-Disposition');
                    let filename = "media_download.mp4";
                    if (contentDisp && contentDisp.includes('filename=')) {
                        filename = contentDisp.split('filename=')[1].replace(/"/g, '').trim();
                    }

                    const blob = await response.blob();
                    const downloadUrl = window.URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = downloadUrl;
                    link.download = filename;
                    document.body.appendChild(link);
                    link.click();
                    link.remove();
                    window.URL.revokeObjectURL(downloadUrl);

                    panel.innerHTML = `🌿 <strong>Completed:</strong> ${filename}`;
                } else {
                    const err = await response.json();
                    panel.style.borderColor = 'rgba(248, 113, 113, 0.4)';
                    panel.innerHTML = `⚠️ <strong>Notice:</strong><br><br>${err.error || 'Extraction failed.'}`;
                }
            } catch (err) {
                panel.style.borderColor = 'rgba(248, 113, 113, 0.4)';
                panel.innerHTML = `⚠️ <strong>Connection error:</strong> ${err.message}`;
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

@app.route('/api/cookie_status', methods=['GET'])
def cookie_status():
    return jsonify({"present": os.path.exists("cookies.txt")})

# ==============================================================================
# 3. CORE EXTRACTION PIPELINE (MULTI-CLIENT FALLBACK + COOKIES)
# ==============================================================================
CLIENT_FALLBACK_ORDER = ['ios', 'android', 'tv', 'web']

def build_ydl_options(format_type, output_dir, client_name):
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
                'player_client': [client_name]
            }
        }
    }

    if format_type == 'audio_only':
        opts['format'] = 'bestaudio/best'
    else:
        # Best available combined stream
        opts['format'] = 'best[ext=mp4]/best'

    # Auto-detect cookies.txt in working directory
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

    # Attempt extraction across client spoofing list
    for client in CLIENT_FALLBACK_ORDER:
        try:
            print(f"[EXTRACTOR] Attempting extraction with '{client}' client...", file=sys.stderr)
            ydl_opts = build_ydl_options(format_type, temp_dir, client)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([target_url])

            downloaded_files = os.listdir(temp_dir)
            if not downloaded_files:
                continue

            target_file_path = os.path.join(temp_dir, downloaded_files[0])
            filename = os.path.basename(target_file_path)

            return send_file(
                target_file_path,
                as_attachment=True,
                download_name=filename
            )

        except Exception as e:
            last_error = str(e)
            print(f"[EXTRACTOR] Client '{client}' failed: {last_error}", file=sys.stderr)

    return jsonify({
        "error": f"Extraction could not be completed.\nDetails: {last_error}\n\n"
                 f"Tip: If YouTube has blacklisted the server IP, place an exported 'cookies.txt' "
                 f"file in the root folder to authenticate automatically."
    }), 500

# ==============================================================================
# 4. RUNNER
# ==============================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
