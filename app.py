from flask import Flask, request, jsonify, render_template_string
import requests
import os

app = Flask(__name__)

# The entire HTML, CSS, and JS is stored inside this Python variable
HTML_TEMPLATE = """
{% raw %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NexGen Downloader</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- FontAwesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- SweetAlert2 -->
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
    <!-- Confetti -->
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
    
    <style>
        /* Feature: Flowing Gradient Background */
        body {
            background: linear-gradient(-45deg, #1e3c72, #2a5298, #ff6a00, #ee0979);
            background-size: 400% 400%;
            animation: gradientBG 15s ease infinite;
            min-height: 100vh;
            font-family: 'Inter', sans-serif;
            transition: all 0.5s ease;
        }
        @keyframes gradientBG {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        /* Feature: Extreme Glassmorphism */
        .glass-panel {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px) saturate(150%);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 25px 45px rgba(0, 0, 0, 0.2);
            border-radius: 2rem;
        }
        /* Feature: Dark Mode Injection */
        body.dark-mode {
            background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364, #000000);
        }
        body.dark-mode .glass-panel {
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #f1f1f1;
        }
        /* Feature: Striped Animated Progress Bar */
        .progress-stripe {
            background-image: linear-gradient(45deg, rgba(255,255,255,0.2) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.2) 50%, rgba(255,255,255,0.2) 75%, transparent 75%, transparent);
            background-size: 1rem 1rem;
            animation: stripe-motion 1s linear infinite;
        }
        @keyframes stripe-motion { 0% { background-position: 1rem 0; } 100% { background-position: 0 0; } }
        /* Feature: Floating Animation */
        .float-hover:hover { transform: translateY(-5px); transition: transform 0.3s ease; }
        .hidden { display: none !important; }
    </style>
</head>
<body class="flex items-center justify-center p-4 text-white">

    <div class="glass-panel w-full max-w-3xl p-8 relative overflow-hidden">
        
        <!-- Theme Toggle -->
        <button onclick="toggleTheme()" class="absolute top-6 right-6 bg-white/20 hover:bg-white/40 p-3 rounded-full backdrop-blur-md transition shadow-lg float-hover">
            <i class="fas fa-moon text-xl" id="theme-icon"></i>
        </button>

        <div class="text-center mb-8">
            <h1 class="text-5xl font-extrabold mb-3 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-yellow-300 to-pink-500 drop-shadow-lg">
                <i class="fab fa-youtube text-red-500 drop-shadow-md"></i> NexGen Fetch
            </h1>
            <p class="text-lg opacity-90 font-medium tracking-wide">Paste a link. Get your file. No BS.</p>
        </div>

        <!-- Main Input UI -->
        <div class="flex flex-col md:flex-row gap-4 mb-6">
            <button onclick="pasteClipboard()" title="Auto-paste" class="bg-indigo-500/80 hover:bg-indigo-600 text-white px-5 py-4 rounded-2xl shadow-xl float-hover transition">
                <i class="fas fa-clipboard-list text-xl"></i>
            </button>
            <input type="url" id="url-input" placeholder="https://www.youtube.com/watch?v=..." class="flex-1 px-6 py-4 rounded-2xl bg-white/20 backdrop-blur-md border border-white/40 focus:border-white focus:outline-none focus:ring-2 focus:ring-white/50 transition text-lg shadow-inner placeholder-white/60 font-semibold text-white">
            <button onclick="fetchMetadata()" class="bg-gradient-to-r from-emerald-400 to-cyan-500 hover:from-emerald-500 hover:to-cyan-600 text-white font-bold px-8 py-4 rounded-2xl shadow-xl float-hover transition text-lg flex items-center justify-center">
                <i class="fas fa-bolt mr-2"></i> Scan
            </button>
        </div>

        <!-- Video Metadata Reveal -->
        <div id="video-details" class="hidden animate-[fadeIn_0.5s_ease-out] bg-white/10 rounded-3xl p-5 mb-6 shadow-2xl border border-white/20">
            <div class="flex flex-col md:flex-row gap-6 items-center">
                <div class="relative group w-full md:w-64">
                    <img id="thumb-preview" src="" alt="Thumbnail" class="w-full rounded-xl shadow-lg object-cover aspect-video border-2 border-white/30 group-hover:border-white/70 transition">
                    <div class="absolute inset-0 bg-black/40 rounded-xl opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                        <i class="fas fa-play-circle text-4xl text-white"></i>
                    </div>
                </div>
                <div class="flex-1 text-center md:text-left">
                    <h2 id="video-title" class="text-2xl font-bold line-clamp-2 mb-2 drop-shadow-md">Video Title</h2>
                    <p id="video-author" class="text-md opacity-80 mb-5 font-semibold"><i class="fas fa-user-edit mr-2"></i>Author Name</p>
                    
                    <div class="flex flex-wrap gap-3 justify-center md:justify-start">
                        <button onclick="startDownload(false)" class="bg-gradient-to-r from-red-500 to-red-700 hover:from-red-600 hover:to-red-800 px-5 py-3 rounded-xl font-bold shadow-xl float-hover transition flex items-center border border-red-400/50">
                            <i class="fas fa-film mr-2 text-xl"></i> MP4
                        </button>
                        <button onclick="startDownload(true)" class="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 px-5 py-3 rounded-xl font-bold shadow-xl float-hover transition flex items-center border border-blue-400/50">
                            <i class="fas fa-headphones mr-2 text-xl"></i> MP3
                        </button>
                        <button onclick="resetUI()" title="Clear Form" class="bg-gray-600/50 hover:bg-gray-700/80 px-4 py-3 rounded-xl shadow-xl float-hover transition border border-gray-400/30">
                            <i class="fas fa-trash-alt text-lg"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Real-Time Progress Bar -->
        <div id="progress-container" class="hidden mt-6 bg-black/30 p-5 rounded-2xl border border-white/20 shadow-inner">
            <div class="flex justify-between font-bold text-sm mb-3 tracking-wide drop-shadow-md">
                <span id="status-text" class="text-emerald-300"><i class="fas fa-spinner fa-spin"></i> Initializing...</span>
                <span id="percentage-text" class="text-cyan-300">0%</span>
            </div>
            <div class="w-full bg-black/50 rounded-full h-5 overflow-hidden shadow-inner border border-white/10">
                <div id="progress-bar" class="progress-stripe bg-gradient-to-r from-green-400 via-cyan-500 to-blue-500 h-5 rounded-full" style="width: 0%; transition: width 0.3s ease;"></div>
            </div>
        </div>

        <!-- Feature: The Captcha Fallback UI -->
        <div id="captcha-fallback-container" class="hidden mt-6 text-center bg-gradient-to-r from-red-600/80 to-orange-600/80 p-6 rounded-2xl border-2 border-red-400 shadow-2xl animate-[pulse_2s_infinite]">
            <i class="fas fa-robot text-4xl text-white mb-3"></i>
            <h3 class="text-2xl font-extrabold text-white mb-2 tracking-wide">Bot Shield Engaged</h3>
            <p class="text-white/90 font-medium mb-5">Cloudflare blocked our automated fetch. You must solve the Captcha manually to download this file.</p>
            <a id="captcha-solve-btn" href="#" target="_blank" class="inline-block bg-yellow-400 hover:bg-yellow-500 text-black font-extrabold py-3 px-8 rounded-xl shadow-xl float-hover transition">
                <i class="fas fa-shield-alt mr-2"></i> Solve Captcha on Cobalt
            </a>
        </div>

        <!-- Feature: Manual Download Fallback Button -->
        <div id="manual-download-container" class="hidden mt-6 text-center animate-[fadeIn_1s_ease-out]">
            <a id="manual-download-btn" href="#" class="inline-block bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 text-white font-extrabold py-4 px-10 rounded-2xl shadow-2xl float-hover transition border border-green-400">
                <i class="fas fa-arrow-down mr-2"></i> Download File Now
            </a>
            <p class="text-sm text-white/70 mt-3 font-medium">Your file is ready. Click the button if it didn't save automatically.</p>
        </div>

    </div>

    <script>
        const Toast = Swal.mixin({ toast: true, position: 'top-end', showConfirmButton: false, timer: 3500, timerProgressBar: true });

        function toggleTheme() {
            document.body.classList.toggle('dark-mode');
            document.getElementById('theme-icon').classList.toggle('fa-moon');
            document.getElementById('theme-icon').classList.toggle('fa-sun');
        }

        async function pasteClipboard() {
            try {
                const txt = await navigator.clipboard.readText();
                document.getElementById('url-input').value = txt;
                Toast.fire({ icon: 'success', title: 'Pasted successfully!' });
            } catch (e) { Toast.fire({ icon: 'error', title: 'Allow clipboard permissions!' }); }
        }

        function resetUI() {
            document.getElementById('url-input').value = '';
            ['video-details', 'progress-container', 'captcha-fallback-container', 'manual-download-container'].forEach(id => {
                document.getElementById(id).classList.add('hidden');
            });
            document.getElementById('progress-bar').style.width = '0%';
        }

        async function fetchMetadata() {
            const url = document.getElementById('url-input').value;
            if (!url.match(/(youtu\.be|youtube\.com)/)) return Toast.fire({ icon: 'error', title: 'Invalid YouTube URL' });
            Toast.fire({ icon: 'info', title: 'Extracting metadata...' });
            
            try {
                const res = await fetch('/api/metadata', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });
                const data = await res.json();
                if (data.error) throw new Error(data.error);

                document.getElementById('video-title').innerText = data.title;
                document.getElementById('video-author').innerText = data.author_name;
                document.getElementById('thumb-preview').src = data.thumbnail_url;
                
                document.getElementById('video-details').classList.remove('hidden');
                document.getElementById('progress-container').classList.add('hidden');
                document.getElementById('captcha-fallback-container').classList.add('hidden');
                document.getElementById('manual-download-container').classList.add('hidden');
                
                Toast.fire({ icon: 'success', title: 'Video Found!' });
            } catch (e) { Toast.fire({ icon: 'error', title: e.message }); }
        }

        async function startDownload(isAudio) {
            const ytUrl = document.getElementById('url-input').value;
            const ui = {
                prog: document.getElementById('progress-container'),
                bar: document.getElementById('progress-bar'),
                pct: document.getElementById('percentage-text'),
                stat: document.getElementById('status-text'),
                cap: document.getElementById('captcha-fallback-container'),
                man: document.getElementById('manual-download-container')
            };

            ui.prog.classList.remove('hidden'); ui.cap.classList.add('hidden'); ui.man.classList.add('hidden');
            ui.stat.innerHTML = '<i class="fas fa-satellite-dish fa-spin"></i> Bypassing blocks...';
            ui.bar.style.width = '15%'; ui.pct.innerText = 'Wait';

            // Feature: Multiple API Fallbacks
            const apis = ['https://cobalt.meowing.de/', 'https://api.cobalt.tools/'];
            let directUrl = null;

            for (let api of apis) {
                try {
                    const req = await fetch(api, {
                        method: 'POST',
                        headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: ytUrl, downloadMode: isAudio ? 'audio' : 'auto' })
                    });
                    if (!req.ok) continue; // Cloudflare blocked this one
                    const data = await req.json();
                    if (data.status === 'error') continue;
                    if (data.url) { directUrl = data.url; break; }
                } catch(e) { /* Network/CORS block, try next */ }
            }

            // Feature: The Captcha Fallback Trigger
            if (!directUrl) {
                ui.prog.classList.add('hidden');
                ui.cap.classList.remove('hidden');
                document.getElementById('captcha-solve-btn').href = "https://cobalt.tools/?u=" + encodeURIComponent(ytUrl);
                return Toast.fire({ icon: 'warning', title: 'Captcha Required!' });
            }

            ui.stat.innerHTML = '<i class="fas fa-cloud-download-alt"></i> Stream active. Pulling data...';
            
            try {
                // Feature: Real File Stream Progress
                const res = await fetch(directUrl);
                const len = res.headers.get('content-length');
                let blob;

                if (!len) {
                    ui.stat.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Downloading...';
                    blob = await res.blob();
                } else {
                    const total = parseInt(len, 10);
                    let loaded = 0;
                    const reader = res.body.getReader();
                    const stream = new ReadableStream({
                        async start(ctrl) {
                            while (true) {
                                const { done, value } = await reader.read();
                                if (done) break;
                                loaded += value.byteLength;
                                const pct = Math.round((loaded / total) * 100);
                                ui.bar.style.width = pct + '%'; ui.pct.innerText = pct + '%';
                                ctrl.enqueue(value);
                            }
                            ctrl.close();
                        }
                    });
                    blob = await new Response(stream).blob();
                }

                // Feature: Final Download Delivery
                const title = document.getElementById('video-title').innerText.replace(/[^a-z0-9]/gi, '_');
                const ext = isAudio ? 'mp3' : 'mp4';
                const fileUrl = window.URL.createObjectURL(blob);
                
                // 1. Force Auto-Download
                const a = document.createElement('a');
                a.href = fileUrl; a.download = `${title}.${ext}`;
                document.body.appendChild(a); a.click(); document.body.removeChild(a);
                
                // 2. Reveal Manual Button
                const manBtn = document.getElementById('manual-download-btn');
                manBtn.href = fileUrl; manBtn.download = `${title}.${ext}`;
                ui.man.classList.remove('hidden');

                ui.stat.innerHTML = '<i class="fas fa-check-circle text-green-400"></i> Done!';
                confetti({ particleCount: 200, spread: 90, origin: { y: 0.6 } });
                Toast.fire({ icon: 'success', title: 'Download triggered!' });

            } catch (e) {
                // Feature: Emergency Link Fallback
                ui.stat.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Stream blocked. Opening direct link...';
                ui.bar.style.backgroundColor = '#f56565';
                
                const manBtn = document.getElementById('manual-download-btn');
                manBtn.href = directUrl; manBtn.target = "_blank"; manBtn.removeAttribute('download');
                ui.man.classList.remove('hidden');
                
                window.open(directUrl, '_blank');
                Toast.fire({ icon: 'info', title: 'Opened in new tab due to stream error.' });
            }
        }
    </script>
</body>
</html>
{% endraw %}
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/metadata', methods=['POST'])
def get_metadata():
    # Safely fetches video details without downloading the video
    data = request.get_json()
    url = data.get('url')
    if not url or 'youtu' not in url:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
    try:
        r = requests.get(oembed_url, timeout=5)
        if r.status_code == 200:
            return jsonify(r.json())
        else:
            return jsonify({"error": "Could not fetch details. Video might be private."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
