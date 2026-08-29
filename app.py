import os
import sys
import socket
import tempfile
from flask import Flask, request, jsonify, render_template_string, send_file
from pytubefix import YouTube

# ==============================================================================
# 2. FLASK SERVER & EMBEDDED DASHBOARD UI
# ==============================================================================
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI PRO SUITE - YouTube Downloader</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            max-width: 650px; 
            margin: 40px auto; 
            padding: 20px; 
            background-color: #0d1117; 
            color: #f0f6fc; 
        }
        h2 { text-align: center; color: #ff3333; letter-spacing: 1px; }
        .card { 
            background: #161b22; 
            padding: 25px; 
            border-radius: 12px; 
            border: 1px solid #30363d; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.5); 
        }
        label { font-weight: bold; margin-top: 15px; display: block; color: #8b949e; font-size: 13px; }
        input, select { 
            width: 100%; 
            padding: 12px; 
            margin-top: 8px; 
            border-radius: 8px; 
            border: 1px solid #30363d; 
            background: #0d1117; 
            color: #fff; 
            font-size: 14px; 
        }
        input:focus, select:focus { outline: none; border-color: #ff3333; }
        button { 
            width: 100%; 
            background-color: #ff3333; 
            color: white; 
            border: none; 
            padding: 14px; 
            font-size: 16px; 
            font-weight: bold; 
            border-radius: 8px; 
            cursor: pointer; 
            margin-top: 20px; 
            transition: 0.2s; 
        }
        button:hover { background-color: #cc0000; }
        button:disabled { background-color: #484f58; cursor: not-allowed; }
        #statusBox { 
            margin-top: 20px; 
            padding: 15px; 
            border-radius: 8px; 
            display: none; 
            background: #21262d; 
            line-height: 1.6; 
            font-size: 14px; 
            word-break: break-word; 
        }
        .loader { 
            border: 3px solid #30363d; 
            border-top: 3px solid #ff3333; 
            border-radius: 50%; 
            width: 18px; 
            height: 18px; 
            animation: spin 1s linear infinite; 
            display: inline-block; 
            vertical-align: middle; 
            margin-right: 8px; 
        }
        .oauth-badge { 
            background: #1f6feb22; 
            border: 1px solid #1f6feb; 
            color: #58a6ff; 
            padding: 10px; 
            border-radius: 6px; 
            margin-top: 10px; 
            font-size: 12px; 
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <h2>⚡ AI PRO SUITE DOWNLOADER</h2>
    <div class="card">
        <label>YouTube Video URL:</label>
        <input type="text" id="urlInput" placeholder="https://www.youtube.com/watch?v=...">
        
        <label>Format:</label>
        <select id="formatSelect">
            <option value="video">Best Video (.mp4)</option>
            <option value="audio">Best Audio (.mp3 / .m4a)</option>
        </select>
        
        <button id="downloadBtn" onclick="processDownload()">Download Video</button>
        
        <div class="oauth-badge">
            🔐 <strong>OAuth2 Device Flow Active:</strong> If this is your first run, check your Render server logs to approve the device code once.
        </div>
        
        <div id="statusBox"></div>
    </div>

    <script>
        async function processDownload() {
            const url = document.getElementById('urlInput').value.trim();
            const format = document.getElementById('formatSelect').value;
            const statusBox = document.getElementById('statusBox');
            const btn = document.getElementById('downloadBtn');

            if (!url) {
                alert("Please enter a YouTube URL.");
                return;
            }

            btn.disabled = true;
            statusBox.style.display = 'block';
            statusBox.style.borderLeft = '4px solid #1f6feb';
            statusBox.innerHTML = '<div class="loader"></div> Connecting via Google DNS & fetching streams...';

            try {
                // Submit download trigger
                const response = await fetch('/api/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, format: format })
                });

                if (response.ok) {
                    statusBox.style.borderLeft = '4px solid #238636';
                    statusBox.innerHTML = '⬇️ Video ready! Sending file to your browser...';
                    
                    // Retrieve file blob from Render server
                    const blob = await response.blob();
                    const contentDisposition = response.headers.get('Content-Disposition');
                    let filename = "download.mp4";
                    if (contentDisposition && contentDisposition.includes('filename=')) {
                        filename = contentDisposition.split('filename=')[1].replace(/"/g, '').trim();
                    }

                    // Trigger browser download
                    const dlUrl = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = dlUrl;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(dlUrl);

                    statusBox.innerHTML = `✅ <strong>Download Finished:</strong> ${filename}`;
                } else {
                    const data = await response.json();
                    statusBox.style.borderLeft = '4px solid #da3633';
                    statusBox.innerHTML = `❌ <strong>Download Failed:</strong><br><br>${data.error || 'Unknown error occurred.'}`;
                }
            } catch (err) {
                statusBox.style.borderLeft = '4px solid #da3633';
                statusBox.innerHTML = `❌ <strong>Network Error:</strong> ${err.message}`;
            }

            btn.disabled = false;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

# ==============================================================================
# 3. DOWNLOAD & PROXY ROUTE
# ==============================================================================
@app.route('/api/download', methods=['POST'])
def handle_download():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "Missing YouTube URL"}), 400

    url = data['url']
    format_type = data.get('format', 'video')

    try:
        print(f"[FETCH] Starting pytubefix for: {url}", file=sys.stderr)

        # Initialize YouTube with OAuth2 support
        yt = YouTube(
            url,
            use_oauth=True,
            allow_oauth_cache=True
        )

        temp_dir = tempfile.mkdtemp()

        if format_type == 'audio':
            stream = yt.streams.get_audio_only()
        else:
            stream = yt.streams.get_highest_resolution()

        if not stream:
            return jsonify({"error": "No compatible streams found for this video."}), 404

        print(f"[DOWNLOADING] Saving '{yt.title}' to Render temporary storage...", file=sys.stderr)
        saved_file_path = stream.download(output_path=temp_dir)

        # Stream physical file from Render server directly to the browser
        return send_file(
            saved_file_path,
            as_attachment=True,
            download_name=os.path.basename(saved_file_path)
        )

    except Exception as e:
        print(f"[ERROR] {str(e)}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500

# ==============================================================================
# 4. RENDER ENTRY POINT (Reads dynamic PORT)
# ==============================================================================
if __name__ == "__main__":
    # Render assigns the listening port via the PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
