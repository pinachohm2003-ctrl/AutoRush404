"""
Informe semanal: recopila las estadísticas de los últimos 7 días
(vistas, likes, comentarios, retención media, suscriptores ganados)
y manda un resumen por Telegram cada domingo a las 22:00.
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
from telegram_notify import send_telegram_message

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def _get_creds():
    return Credentials(
        token=None,
        refresh_token=YT_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET,
        scopes=SCOPES,
    )


def _get_channel_id(youtube):
    resp = youtube.channels().list(part="id", mine=True).execute()
    return resp["items"][0]["id"]


def build_report():
    creds = _get_creds()
    youtube = build("youtube", "v3", credentials=creds)
    analytics = build("youtubeAnalytics", "v2", credentials=creds)

    channel_id = _get_channel_id(youtube)

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=7)

    totals = analytics.reports().query(
        ids=f"channel=={channel_id}",
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics="views,likes,comments,shares,subscribersGained,averageViewPercentage",
    ).execute()

    row = totals.get("rows", [[0, 0, 0, 0, 0, 0]])[0]
    views, likes, comments, shares, subs_gained, avg_pct = row

    top_videos = analytics.reports().query(
        ids=f"channel=={channel_id}",
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics="views,likes,averageViewPercentage",
        dimensions="video",
        sort="-views",
        maxResults=3,
    ).execute()

    top_lines = []
    for r in top_videos.get("rows", []):
        video_id, v_views, v_likes, v_pct = r
        top_lines.append(f"  • https://youtube.com/shorts/{video_id} — {int(v_views)} vistas, {v_pct:.0f}% retención")

    worst_line = ""
    if top_videos.get("rows") and len(top_videos["rows"]) > 0:
        worst = min(top_videos["rows"], key=lambda r: r[3])
        if worst[3] < 40:
            worst_line = (
                f"\n⚠️ El short con peor retención tuvo un {worst[3]:.0f}% — "
                f"si varios bajan de ahí, prueba a acortar el gancho inicial o cambiar el ritmo del guion."
            )

    message = (
        f"📊 <b>Informe semanal</b> ({start_date} → {end_date})\n\n"
        f"👁️ Vistas: {int(views)}\n"
        f"👍 Likes: {int(likes)}\n"
        f"💬 Comentarios: {int(comments)}\n"
        f"🔁 Compartidos: {int(shares)}\n"
        f"🆕 Suscriptores ganados: {int(subs_gained)}\n"
        f"⏱️ Retención media: {avg_pct:.1f}%\n\n"
        f"🏆 <b>Top 3 de la semana:</b>\n" + "\n".join(top_lines) +
        worst_line
    )

    return message


if __name__ == "__main__":
    try:
        report = build_report()
        print(report)
        send_telegram_message(report)
    except Exception as e:
        err = f"❌ Error generando el informe semanal: {type(e).__name__}: {e}"
        print(err)
        try:
            send_telegram_message(err)
        except Exception:
            pass
        sys.exit(1)
