import os
import requests
import time
import smtplib
from email.mime.text import MIMEText
import google.genai as genai

# Load secrets from GitHub
API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# Targeted regional URLs for construction and maintenance
districts = {
    "St. Louis County & Schools": [
        "https://www.parkwayschools.net/contact/departments/facilities/construction-bids",
        "https://www.mehlvilleschooldistrict.com/departments/finances/request-for-proposal-rfp",
        "https://www.slps.org/departments/finance-division/welcome-to-procurement/bonfire-bid-opportunities",
        "https://stlouiscountymo.gov/services/services-links/procurement/"
    ],
    "St. Louis Municipalities": [
        "https://stlmuni.org/the-league/rfps/",
        "https://www.stlouis-mo.gov/government/procurement/index.cfm",
        "https://www.claytonmo.gov/government/bid-documents-rfp-rfq"
    ]
}

KEYWORDS = "roofing, tuckpointing, windows, or construction"
client = genai.Client(api_key=API_KEY)
history_file = "seen_ids.txt"

# Load memory of previously found leads
if os.path.exists(history_file):
    with open(history_file, "r") as f:
        seen_leads = f.read().splitlines()
else:
    seen_leads = []

all_new_leads = []
current_session_ids = []

# Scraper Logic
for batch_name, urls in districts.items():
    for url in urls:
        try:
            response = requests.get(url, timeout=15)
            prompt = f"Extract active bid titles and due dates for {KEYWORDS} from this page: {response.text[:10000]}"
            result = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            
            lead_text = result.text.strip()
            if lead_text not in seen_leads and "no active" not in lead_text.lower():
                all_new_leads.append(f"NEW LEAD found at {url}:\n{lead_text}")
                current_session_ids.append(lead_text)
            time.sleep(5)
        except Exception as e:
            print(f"Error scanning {url}: {e}")

# Email Notification
if all_new_leads:
    msg = MIMEText("\n\n".join(all_new_leads))
    msg['Subject'] = f"🚨 New Bid Alert - {time.strftime('%Y-%m-%d')}"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

    # Save new leads to the history file
    with open(history_file, "a") as f:
        for item in current_session_ids:
            f.write(item + "\n")
