"""
Sube el vídeo final a YouTube usando el refresh token generado una sola vez
(no requiere volver a iniciar sesión nunca).
"""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

CATEGORY_ID_EDUCATION = "27"  # "Education" en YouTube


def _get_service():
    creds = Credentials(
        token=None,
        refresh_token=YT_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET,
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds)


def upload_short(video_path, title, description, hashtags):
    service = _get_service()

    full_description = description.strip() + "\n\n" + " ".join(hashtags)
    tags = [h.lstrip("#") for h in hashtags]

    body = {
        "snippet": {
            "title": title[:100],
            "description": full_description[:4900],
            "tags": tags,
            "categoryId": CATEGORY_ID_EDUCATION,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")

    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()

    video_id = response["id"]
    return f"https://youtube.com/shorts/{video_id}"


if __name__ == "__main__":
    import sys
    url = upload_short(sys.argv[1], "Título de prueba", "Descripción de prueba", ["#shorts", "#curiosidades"])
    print("Subido:", url)
