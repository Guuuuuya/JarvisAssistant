from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/tasks",
]
BASE = Path(__file__).parent
CREDS = BASE / "credentials.json"
TOKEN = BASE / "token.json"


def _get_creds():
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
    if not creds or not creds.valid:
        if not CREDS.exists():
            raise FileNotFoundError("credentials.json missing — see README Google setup section")
        creds = InstalledAppFlow.from_client_secrets_file(str(CREDS), SCOPES).run_local_server(port=8080)
        TOKEN.write_text(creds.to_json())
    return creds


def calendar_today() -> str:
    from datetime import datetime, timezone
    svc = build("calendar", "v3", credentials=_get_creds())
    now = datetime.now(timezone.utc).isoformat()
    end = datetime.now(timezone.utc).replace(hour=23, minute=59).isoformat()
    ev = svc.events().list(calendarId="primary", timeMin=now, timeMax=end, singleEvents=True, orderBy="startTime").execute()
    items = ev.get("items", [])
    if not items:
        return "No events left today."
    lines = []
    for e in items[:10]:
        t = e["start"].get("dateTime", e["start"].get("date", ""))[:16].replace("T", " ")
        lines.append(f"{t} {e.get('summary','(no title)')}")
    return "Today's events: " + "; ".join(lines)


def gmail_unread() -> str:
    svc = build("gmail", "v1", credentials=_get_creds())
    res = svc.users().messages().list(userId="me", q="is:unread", maxResults=5).execute()
    msgs = res.get("messages", [])
    if not msgs:
        return "No unread emails."
    subjects = []
    for m in msgs:
        full = svc.users().messages().get(userId="me", id=m["id"], format="metadata", metadataHeaders=["Subject"]).execute()
        for h in full["payload"]["headers"]:
            if h["name"] == "Subject":
                subjects.append(h["value"])
    return "Unread emails: " + "; ".join(subjects)


def tasks_list() -> str:
    svc = build("tasks", "v1", credentials=_get_creds())
    res = svc.tasks().list(tasklist="@default", maxResults=10, showCompleted=False).execute()
    items = res.get("items", [])
    if not items:
        return "Task list empty."
    return "Your tasks: " + "; ".join(t["title"] for t in items)


def tasks_add(text: str) -> str:
    svc = build("tasks", "v1", credentials=_get_creds())
    svc.tasks().insert(tasklist="@default", body={"title": text}).execute()
    return f"Added task: {text}"
