from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO, emit
import yt_dlp
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# This function runs every time yt-dlp downloads a chunk
def progress_hook(d):
    if d['status'] == 'downloading':
        # Clean the percentage string to get a float
        percent_str = d.get('_percent_str', '0%').replace('%','')
        try:
            percent = float(percent_str)
            socketio.emit('progress', {'percentage': percent})
        except:
            pass
    elif d['status'] == 'finished':
        socketio.emit('progress', {'percentage': 100})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    video_url = request.form.get('url')
    download_folder = 'downloads'
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'progress_hooks': [progress_hook], # Connect the hook here
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{download_folder}/%(title)s.%(ext)s',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3').replace('.mp4', '.mp3')

    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    socketio.run(app, debug=True,port=1000,host="0.0.0.0")