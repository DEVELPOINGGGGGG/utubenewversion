from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

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
            return jsonify({"error": "Could not fetch video details. It might be private."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Render binds to the PORT environment variable
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
