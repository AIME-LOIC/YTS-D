from flask import Flask, render_template, request, send_file
import yt_dlp
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    video_url = request.form.get('url')
    
    # 1. Path to save files
    download_folder = 'downloads'
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # 2. Stealth Options to bypass 403 Forbidden
    ydl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    
    # 1. Use multiple clients to find one that works
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios'],
            'skip': ['web_safari', 'web']
        }
    },
    
    # 2. Force a modern User-Agent
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    
    # 3. Handle the file conversion
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    
    # 4. Output template
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'quiet': False,
    'no_warnings': False,
}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info and download
            info = ydl.extract_info(video_url, download=True)
            # Find the path of the created mp3
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp3_filename = base + ".mp3"

        return send_file(mp3_filename, as_attachment=True)
    
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)