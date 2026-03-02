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

# 2. Expanded Search List: St. Louis Regional Districts (11-21) + County Hubs
districts = {
    "St. Louis Regional Districts (Ranked 11-21)": [
        "https://www.nwr1.k12.mo.us/departments/finance/purchasing/bids-and-rfps", # Northwest R-1
        "https://www.psdr3.org/departments/operations/purchasing", # Pattonville R-3
        "https://www.lindberghschools.ws/departments/business-and-finance/bids-proposals-and-qualifications", # Lindbergh
        "https://www.stcharlessd.org/Page/190", # St. Charles R-VI
        "https://www.mvr3.k12.mo.us/page/vendor-bid-information", # Meramec Valley R-III
        "https://www.washington.k12.mo.us/49133_3", # School District of Washington
        "https://www.rgsd.k12.mo.us/Page/107", # Riverview Gardens
        "https://www.fergflor.k12.mo.us/Page/506", # Ferguson-Florissant
        "https://www.ritenour.k12.mo.us/Page/156", # Ritenour
        "https://www.webster.k12.mo.us/Page/147", # Webster Groves
        "https://www.troyschools.net/departments/financial-affairs/bids-and-requests-for-proposals-rfp" # Troy R-III
    ],
    "County & Regional Hubs": [
        "https://stlouiscountymo.gov/services/services-links/procurement/",
        "https://www.stlouis-mo.gov/government/procurement/index.cfm",
        "https://www.stcharlescitymo.gov/161/Bids-Purchases",
        "https://www.jeffcomo.gov/347/Bids",
        "https://www.franklinmo.org/bids",
        "https://stlmuni.org/the-league/rfps/"
    ]
}

KEYWORDS = "roofing, tuckpointing, windows, or construction"
client = genai.Client(api_key=API_KEY)
history_file = "seen_ids.txt"

# 3. Load memory (prevents duplicate emails)
if os.path.exists(history_file):
    with open(history_file, "r") as f:
        seen_leads = f.read().splitlines()
else:
    seen_leads = []

all_new_leads = []
current_session_ids = []

# 4. Scraper Logic with 35-second API cooldown
for batch_name, urls in districts.items():
    for url in urls:
        try:
            print(f"--- Checking: {url} ---")
            response = requests.get(url, timeout=20)
            
            prompt = (
                f"Identify any active or open bids for {KEYWORDS} on this page. "
                f"If found, list them clearly as: [TITLE] - [DUE DATE]. "
                f"Website content: {response.text[:10000]}"
            )
            
            result = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            lead_text = result.text.strip()
            
            print(f"AI Result for {url}: {lead_text[:100]}...")

            if "no active" not in lead_text.lower() and len(lead_text) > 15:
                if lead_text not in seen_leads:
                    all_new_leads.append(f"({batch_name}) ACTIVE LEAD at {url}:\n{lead_text}")
                    current_session_ids.append(lead_text)
            
            # MANDATORY 35s COOL DOWN: Prevents 429 Error on Free Tier
            print("Cooling down 35 seconds...")
            time.sleep(35) 
            
        except Exception as e:
            print(f"Error at {url}: {e}")
            time.sleep(40) 

# 5. Email Notification
if all_new_leads:
    msg = MIMEText("\n\n".join(all_new_leads))
    msg['Subject'] = f"🚨 Regional RFP Alert - {datetime.now().strftime('%Y-%m-%d')}"
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
