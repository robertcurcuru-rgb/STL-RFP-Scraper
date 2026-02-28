import os
import requests
import time
import smtplib
from email.mime.text import MIMEText
import google.genai as genai
from datetime import datetime

# 1. Load secrets from GitHub
API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# 2. Expanded Regional Search List
# Includes Top 10 K-12 Districts and County Portals for St. Louis Metro
districts = {
    "Top 10 K-12 Districts (Enrollment)": [
        "https://www.slps.org/departments/finance-division/welcome-to-procurement/bonfire-bid-opportunities", # SLPS
        "https://www.rockwood.k12.mo.us/departments/finance/purchasing/bids-and-rfps", # Rockwood
        "https://www.parkwayschools.net/contact/departments/facilities/construction-bids", # Parkway
        "https://www.fhsdschools.org/departments/business-services/purchasing/bids-rfps", # Francis Howell
        "https://www.fz.k12.mo.us/page/bids-and-proposals", # Fort Zumwalt
        "https://www.hazelwoodschools.org/Page/8230", # Hazelwood
        "https://www.wentzville.k12.mo.us/Page/142", # Wentzville
        "https://www.mehlvilleschooldistrict.com/departments/finances/request-for-proposal-rfp", # Mehlville
        "https://www.kirkwoodschools.org/Page/1109", # Kirkwood
        "https://www.fox.k12.mo.us/departments/finance/purchasing/bids" # Fox (Jefferson Co)
    ],
    "County-Level Portals": [
        "https://stlouiscountymo.gov/services/services-links/procurement/", # St. Louis County
        "https://www.stcharlescitymo.gov/161/Bids-Purchases", # St. Charles City/County Hub
        "https://www.jeffcomo.gov/347/Bids", # Jefferson County
        "https://www.franklinmo.org/bids" # Franklin County
    ],
    "Regional Municipalities": [
        "https://stlmuni.org/the-league/rfps/", # St. Louis Municipal League (Covers 80+ Cities)
        "https://www.stlouis-mo.gov/government/procurement/index.cfm", # City of St. Louis
        "https://www.claytonmo.gov/government/bid-documents-rfp-rfq" # Clayton
    ]
}

KEYWORDS = "roofing, tuckpointing, windows, or construction"
client = genai.Client(api_key=API_KEY)
history_file = "seen_ids.txt"

# 3. Forced Threshold to February 21, 2026
threshold_date = "February 21, 2026"
print(f"Force filtering for leads posted on or after: {threshold_date}")

# 4. Load memory
if os.path.exists(history_file):
    with open(history_file, "r") as f:
        seen_leads = f.read().splitlines()
else:
    seen_leads = []

all_new_leads = []
current_session_ids = []

# 5. Scraper Logic with Rate-Limit Protection
for batch_name, urls in districts.items():
    for url in urls:
        try:
            print(f"--- Checking: {url} ---")
            response = requests.get(url, timeout=15)
            
            prompt = (
                f"Identify active bids for {KEYWORDS} that were POSTED on or after "
                f"{threshold_date}. If you find a match, list it as: "
                f"[POSTED DATE] - [TITLE] - [DUE DATE]. "
                f"Website content: {response.text[:10000]}"
            )
            
            result = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            lead_text = result.text.strip()
            
            # Print AI response for log visibility
            print(f"AI Result: {lead_text[:100]}...")

            if "no active" not in lead_text.lower() and len(lead_text) > 15:
                if lead_text not in seen_leads:
                    all_new_leads.append(f"({batch_name}) RECENT LEAD at {url}:\n{lead_text}")
                    current_session_ids.append(lead_text)
            
            # CRITICAL: 20-second wait to prevent 429 RESOURCE_EXHAUSTED errors
            print("Cooling down for 20 seconds...")
            time.sleep(20) 
            
        except Exception as e:
            print(f"Error at {url}: {e}")
            time.sleep(30) # Wait longer if an error occurs

# 6. Email Notification
if all_new_leads:
    msg = MIMEText("\n\n".join(all_new_leads))
    msg['Subject'] = f"🚨 Regional RFP Digest - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

    with open(history_file, "a") as f:
        for item in current_session_ids:
            f.write(item + "\n")
    print("Success: Email sent and history updated.")
else:
    print("Finished: No new leads found.")
