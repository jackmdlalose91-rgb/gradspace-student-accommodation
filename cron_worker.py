
"""
Cron worker for Gradspace
- Mark overdue invoices
- Send invoice and overdue reminders
Run with env vars / secrets:
SUPABASE_URL, SUPABASE_ANON_KEY, SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASS, CURRENCY (optional)
"""
import os, sys
from datetime import date, datetime
from email.message import EmailMessage

from supabase import create_client
import pandas as pd

def send_email(to_email, subject, body):
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    if not EMAIL_USER or not EMAIL_PASS: 
        print("Email not configured; skip send to", to_email)
        return False
    import smtplib
    msg = EmailMessage(); msg["From"]=EMAIL_USER; msg["To"]=to_email; msg["Subject"]=subject; msg.set_content(body)
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(msg)
    return True

def main():
    url = os.getenv("SUPABASE_URL"); key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        print("Supabase creds missing"); sys.exit(1)
    supa = create_client(url, key)
    currency = os.getenv("CURRENCY", "ZAR")

    # fetch students & users map
    users = {u["id"]: u for u in supa.table("users").select("*").execute().data}
    students = supa.table("students").select("*").execute().data
    sid_by_id = {s["id"]: s for s in students}

    # find invoices due or overdue
    inv = supa.table("invoices").select("*").execute().data
    today = date.today()
    overdue_to_update = []
    for i in inv:
        due = i.get("due_date")
        if due:
            due_d = date.fromisoformat(due)
            if due_d < today and i.get("status") == "unpaid":
                overdue_to_update.append(i["id"])

    if overdue_to_update:
        supa.table("invoices").update({"status":"overdue"}).in_("id", overdue_to_update).execute()

    # email reminders
    for i in inv:
        sid = i.get("student_id"); srec = sid_by_id.get(sid)
        if not srec: continue
        uid = srec.get("user_id"); u = users.get(uid)
        email = u and u.get("email")
        amount = float(i.get("amount") or 0)
        note = i.get("note") or "rent"
        due = i.get("due_date") or ""
        if i.get("status") == "unpaid":
            subject = "Your Gradspace invoice"
            body = f"Hello {u.get('full_name') or 'Student'}, your invoice ({note}) is {amount:.2f} {currency}, due {due}."
            send_email(email, subject, body)
        elif i.get("status") == "overdue":
            subject = "Overdue: Gradspace invoice"
            body = f"Hi {u.get('full_name') or 'Student'}, your invoice ({note}) is overdue: {amount:.2f} {currency}. Please pay."
            send_email(email, subject, body)

if __name__ == "__main__":
    main()
