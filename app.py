from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import uuid

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "URL missing"}), 400

    try:
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "success": True,
            "title": info.get("title", "Unknown Video"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", ""),
            "formats": [
                {
                    "format_id": f.get("format_id"),
                    "quality": f.get("format_note"),
                    "ext": f.get("ext"),
                    "height": f.get("height"),
                    "filesize": f.get("filesize")
                }
                for f in info.get("formats", [])
                if f.get("height")
            ]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/download", methods=["POST"])
def download():
    data = request.get_json()

    url = data.get("url", "").strip()
    quality = data.get("quality", "720")

    if not url:
        return jsonify({"error": "URL missing"}), 400

    allowed = {
        "360": "bestvideo[height<=360]+bestaudio/best[height<=360]",
        "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "2160": "bestvideo[height<=2160]+bestaudio/best[height<=2160]"
    }

    format_code = allowed.get(str(quality))

    if not format_code:
        return jsonify({"error": "Invalid quality"}), 400

    file_id = str(uuid.uuid4())

    output = os.path.join(
        DOWNLOAD_DIR,
        file_id + ".%(ext)s"
    )

    options = {
        "format": format_code,
        "outtmpl": output,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)

        filename = ydl.prepare_filename(info)

        base = os.path.splitext(filename)[0]

        possible_files = [
            base + ".mp4",
            filename
        ]

        final_file = None

        for f in possible_files:
            if os.path.exists(f):
                final_file = f
                break

        if not final_file:
            return jsonify({
                "error": "Downloaded file not found"
            }), 500

        return send_file(
            final_file,
            as_attachment=True,
            download_name="video.mp4"
        )

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port
  )
