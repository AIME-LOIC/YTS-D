import os
import logging
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, send_file, abort
from flask_socketio import SocketIO
import yt_dlp

# Basic logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def progress_hook(d):
    status = d.get('status')
    try:
        if status == 'downloading':
            percent_str = d.get('_percent_str', '0%').replace('%', '').strip()
            percent = float(percent_str) if percent_str else 0.0
            socketio.emit('progress', {'percentage': percent}, namespace='/', broadcast=True)
        elif status == 'finished':
            # When finished, the postprocessor may still run; signal 100%
            socketio.emit('progress', {'percentage': 100}, namespace='/', broadcast=True)
    except Exception:
        # Avoid crashing the hook for unexpected payloads
        log.exception("Error in progress_hook")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    video_url = request.form.get('url', '').strip()
    if not video_url:
        return abort(400, description="Missing 'url' form field")

    # Use video id for deterministic filenames
    outtmpl = os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s')
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'progress_hooks': [progress_hook],
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': outtmpl,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
    except yt_dlp.DownloadError as e:
        log.exception("Download failed")
        return abort(500, description=f"Download failed: {e}")
    except Exception as e:
        log.exception("Unexpected error during download")
        return abort(500, description="Unexpected error during download")

    # Construct expected mp3 path using video id
    video_id = info.get('id')
    if not video_id:
        return abort(500, description="Could not determine video id")

    mp3_path = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.mp3")
    if not os.path.isfile(mp3_path):
        # Fallback: try to find any mp3 produced for this id
        candidates = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith('.mp3') and f.startswith(video_id)]
        if candidates:
            mp3_path = os.path.join(DOWNLOAD_FOLDER, candidates[0])
        else:
            log.error("Expected mp3 not found after download")
            return abort(500, description="Downloaded file not found")

    return send_file(mp3_path, as_attachment=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=1000, host="0.0.0.0")