import os
import requests
import time
import smtplib
from email.mime.text import MIMEText
import google.genai as genai
from datetime import datetime, timedelta

# 1. Load secrets from GitHub
API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# 2. Targeted regional URLs for construction and maintenance
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

# 3. Calculate the 7-day threshold
seven_days_ago = datetime.now() - timedelta(days=7)
threshold_date = seven_days_ago.strftime('%B %d, %Y')
print(f"Filtering for leads posted on or after: {threshold_date}")

# 4. Load memory of previously found leads
if os.path.exists(history_file):
    with open(history_file, "r") as f:
        seen_leads = f.read().splitlines()
else:
    seen_leads = []

all_new_leads = []
current_session_ids = []

# 5. Scraper Logic with 7-Day Filter
for batch_name, urls in districts.items():
    for url in urls:
        try:
            print(f"Scanning: {url}")
            response = requests.get(url, timeout=15)
            
            # This prompt forces the AI to check the dates on the page
            prompt = (
                f"Identify active bids for {KEYWORDS} that were POSTED on or after "
                f"{threshold_date}. If you find a match, list it as: "
                f"[POSTED DATE] - [TITLE] - [DUE DATE]. "
                f"Website content: {response.text[:10000]}"
            )
            
            result = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            lead_text = result.text.strip()

            # Filter out "No active bids found" responses
            if "no active" not in lead_text.lower() and len(lead_text) > 15:
                if lead_text not in seen_leads:
                    all_new_leads.append(f"({batch_name}) RECENT LEAD (Last 7 Days) at {url}:\n{lead_text}")
                    current_session_ids.append(lead_text)
            
            # Short pause to prevent being blocked
            time.sleep(5) 
        except Exception as e:
            print(f"Error scanning {url}: {e}")

# 6. Email Notification
if all_new_leads:
    msg = MIMEText("\n\n".join(all_new_leads))
    msg['Subject'] = f"🚨 7-Day RFP Digest - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

    # Save new leads to the history file
    with open(history_file, "a") as f:
        for item in current_session_ids:
            f.write(item + "\n")
    print("Email sent and history updated.")
else:
    print("No new leads found within the last 7 days.")
