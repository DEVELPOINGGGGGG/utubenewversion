import sys
from flask import Flask, request, jsonify, render_template_string
import yt_dlp

app = Flask(__name__)

# --- EMBEDDED HTML UI ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YOUTUBE SEARCH - AI PRO SUITE (Downloader)</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 650px; margin: 40px auto; padding: 20px; background-color: #0f0f13; color: #fff; }
        h2 { text-align: center; color: #ff0000; letter-spacing: 1px; }
        .card { background: #1c1c24; padding: 25px; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.5); }
        label { font-weight: bold; margin-top: 15px; display: block; color: #aaa; }
        input, select { width: 100%; padding: 12px; margin-top: 8px; border-radius: 6px; border: 1px solid #333; background: #2a2a35; color: #fff; box-sizing: border-box; }
        input:focus, select:focus { outline: none; border-color: #ff0000; }
        button { width: 100%; background-color: #ff0000; color: white; border: none; padding: 14px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; margin-top: 20px; transition: 0.3s; }
        button:hover { background-color: #cc0000; }
        button:disabled { background-color: #555; cursor: not-allowed; }
        #statusBox { margin-top: 20px; padding: 15px; border-radius: 6px; display: none; background: #2a2a35; white-space: pre-wrap; word-wrap: break-word; line-height: 1.5; }
        .loader { border: 3px solid #333; border-top: 3px solid #ff0000; border-radius: 50%; width: 18px; height: 18px; animation: spin 1s linear infinite; display: inline-block; vertical-align: middle; margin-right: 10px; }
        .btn-dl { display: block; text-align: center; margin-top: 15px; padding: 12px; background: #4CAF50; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; }
        .btn-dl:hover { background: #45a049; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <h2>AI PRO SUITE - DOWNLOADER</h2>
    <div class="card">
        <label>YouTube Video URL:</label>
        <input type="text" id="urlInput" placeholder="https://www.youtube.com/watch?v=...">
        
        <label>Format:</label>
        <select id="formatSelect">
            <option value="video">Best Video + Audio (.mp4)</option>
            <option value="audio">Best Audio Only (.m4a)</option>
        </select>
        
        <button id="downloadBtn" onclick="startProcess()">Extract Download Link</button>
        
        <div id="statusBox"></div>
    </div>

    <script>
        async function startProcess() {
            const url = document.getElementById('urlInput').value.trim();
            const format = document.getElementById('formatSelect').value;
            const statusBox = document.getElementById('statusBox');
            const btn = document.getElementById('downloadBtn');

            if(!url) {
                alert("Please enter a valid URL.");
                return;
            }

            btn.disabled = true;
            statusBox.style.display = 'block';
            statusBox.style.borderLeft = '4px solid #2196F3';
            statusBox.innerHTML = '<div class="loader"></div> Spoofing mobile clients to bypass IP blocks...';

            try {
                const response = await fetch('/api/get_link', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, format: format })
                });

                const data = await response.json();

                if(response.ok && data.status === "ok") {
                    statusBox.style.borderLeft = '4px solid #4CAF50';
                    statusBox.innerHTML = `
                        <strong style="color:#4CAF50">✅ Success!</strong><br><br>
                        <strong>Title:</strong> ${data.title}<br>
                        <strong>Method Used:</strong> <span style="color:#aaa">${data.strategy_used}</span><br>
                        <a href="${data.download_url}" target="_blank" class="btn-dl">⬇️ Download File</a>
                    `;
                } else {
                    statusBox.style.borderLeft = '4px solid #f44336';
                    statusBox.innerHTML = `
                        <strong style="color:#f44336">❌ Extraction Failed</strong><br><br>
                        <span style="color:#aaa">${data.error || 'Unknown error occurred.'}</span>
                    `;
                }
            } catch (err) {
                statusBox.style.borderLeft = '4px solid #f44336';
                statusBox.innerHTML = `<strong style="color:#f44336">❌ Network Error</strong><br><br>${err.message}`;
            }

            btn.disabled = false;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

def extract_video_info(url, format_type, client_type):
    fmt = 'bestaudio[ext=m4a]/bestaudio' if format_type == 'audio' else 'best[ext=mp4]/best'

    ydl_opts = {
        'format': fmt,
        'quiet': True,
        'noplaylist': True,
        'skip_download': True,
        'simulate': True,
        'no_check_certificate': True,
        'force_ipv4': True,
        # This is the magic sauce: Pretend we are not a web browser
        'extractor_args': {
            'youtube': {
                'player_client': [client_type]
            }
        }
    }

    # If you upload a cookies.txt file to your Hugging Face Space, 
    # uncomment the line below so YouTube thinks you are logged in.
    ydl_opts['cookiefile'] = 'cookies.txt'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "download_url": info.get('url'),
            "title": info.get('title')
        }

@app.route('/api/get_link', methods=['POST'])
def get_link():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "URL is missing"}), 400

    youtube_url = data['url']
    format_type = data.get('format', 'video')

    # STRATEGY 1: Spoof an Android App
    try:
        print("Attempt 1: Spoofing Android Mobile Client...", file=sys.stderr)
        result = extract_video_info(youtube_url, format_type, 'android')
        
        return jsonify({
            "status": "ok",
            "download_url": result["download_url"],
            "title": result["title"],
            "strategy_used": "Android Client Spoofing"
        })
        
    except Exception as e1:
        error_msg_1 = str(e1)
        print(f"Android Spoof Failed: {error_msg_1}", file=sys.stderr)
        
        # STRATEGY 2: Spoof an iOS App
        try:
            print("Attempt 2: Spoofing iOS Mobile Client...", file=sys.stderr)
            result = extract_video_info(youtube_url, format_type, 'ios')
            
            return jsonify({
                "status": "ok",
                "download_url": result["download_url"],
                "title": result["title"],
                "strategy_used": "iOS Client Spoofing"
            })
            
        except Exception as e2:
            print(f"iOS Spoof Failed: {str(e2)}", file=sys.stderr)
            return jsonify({
                "error": "YouTube blocked the Hugging Face Server IP.\n\n" +
                         "To fix this permanently, you MUST upload a 'cookies.txt' file " +
                         "to your Hugging Face space and uncomment the cookie line in app.py."
            }), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7860)
