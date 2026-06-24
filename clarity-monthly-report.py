"""
Microsoft Clarity + Claude + SendGrid  |  Monthly UX Report (CSV Edition)
-------------------------------------------------------------------------
Run this once a month after downloading your Clarity CSV export.

Steps:
  1. Go to clarity.microsoft.com -> your project -> Export CSV
  2. Save the file as clarity_data.csv in this folder
  3. Run: python3 clarity_monthly_report.py

Setup (one time only):
  pip install anthropic sendgrid
"""

import anthropic
import base64
import csv
import glob
import json
import os
import re
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ─────────────────────────────────────────────
#  CONFIGURATION — fill these in
# ─────────────────────────────────────────────

ANTHROPIC_API_KEY = ""    # console.anthropic.com
SENDGRID_API_KEY  = ""     # sendgrid.com > Settings > API Keys
EMAIL_SENDER      = ""         # verified sender in SendGrid
EMAIL_RECIPIENTS  = [""]   # who receives the report

PRODUCT_NAME      = ""

CSV_FILE          = ""           # export from Clarity dashboard
HEATMAP_GLOB      = ""                # optional: heatmap_1.jpg, heatmap_2.jpg etc.


# ─────────────────────────────────────────────
#  STEP 1: READ CSV
# ─────────────────────────────────────────────

def read_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"\n  CSV not found: '{path}'\n"
            f"  Export your Clarity dashboard as CSV and save it as '{path}'\n"
            f"  in the same folder as this script, then run again.\n"
        )
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            rows.append(", ".join(row))
    print(f"  Read {len(rows)} rows from {path}")
    return "\n".join(rows)


# ─────────────────────────────────────────────
#  STEP 2: LOAD HEATMAPS (optional)
# ─────────────────────────────────────────────

def detect_media_type(path):
    ext = os.path.splitext(path)[1].lower()
    return "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

def load_heatmaps(pattern):
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"  No heatmaps found — skipping heatmap analysis.")
        return []
    heatmaps = []
    for path in files:
        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")
        heatmaps.append({
            "filename":    os.path.basename(path),
            "base64_data": data,
            "media_type":  detect_media_type(path)
        })
        print(f"  Loaded heatmap: {os.path.basename(path)}")
    return heatmaps


# ─────────────────────────────────────────────
#  STEP 3: ANALYSE WITH CLAUDE
# ─────────────────────────────────────────────

REPORT_PROMPT = """
You are a senior UX analyst producing a monthly report for {product_name}.

You have been given a CSV export from Microsoft Clarity and optional heatmap screenshots.

Write a Monthly UX Intelligence Report covering ALL sections below.
Name SPECIFIC pages, URLs, or workflows for every finding.
Be direct and actionable. Flag critical issues with [CRITICAL] and wins with [WIN].

## 1. Executive Summary
3-5 sentences. Most important action item this month. What improved?

## 2. Monthly UX Trends
Plain-English summary of overall UX health and patterns this month.

## 3. Device and Browser Breakdown
List each browser and device type with session count and percentage of total.
Flag any with disproportionately high friction signals.

## 4. Anomaly Detection
Flag any metric that looks unusually high or low. For each:
- Metric and what is unusual
- Specific page or workflow
- Likely hypothesis for why

## 5. Session Metadata Analysis
Analyse dead clicks, scroll depth, drop-off patterns. For each:
- Exact page or workflow
- What the pattern looks like
- Hypothesis for why it is happening

## 6. Funnel and Segment Cross-Reference
Which user segments have the worst experience?
Which funnel steps are leaking most users?

## 7. Session Recordings - Priority Watch List
Top 5 pages to watch recordings this month.
For each: what to look for and why it matters. Numbered list.

## 8. Heatmap Attention Patterns
Based on heatmap images if provided.
Where is attention concentrated? Where is it going to wrong places?
Suggest specific layout or content changes.
If no heatmaps provided, suggest which pages to prioritise for heatmap review.

## 9. Accessibility and Usability Signals
Error clicks and dead clicks indicating confusing UI.
Name specific pages and UI areas. Recommend specific fixes.

## 10. Forms and Task Completion
Which forms or flows have the most friction?
Where are users abandoning task flows? Suggest fixes.

## 11. Navigation and Findability
Are users finding what they need?
Which pages show failed findability? Suggest structural or label changes.

## 12. Where Users Struggled Most
Top 8 pages ranked by struggle signals.
Format: Page | Primary Struggle Signal | Recommended Intervention

## 13. Top 5 Recommended Actions This Month
Format: [Priority N] Page -> Problem -> Fix -> Expected Impact

CSV DATA:
{csv_data}
"""

def analyse_with_claude(csv_data, heatmaps):
    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    content = [{
        "type": "text",
        "text": REPORT_PROMPT.format(
            product_name=PRODUCT_NAME,
            csv_data=csv_data
        )
    }]
    for hm in heatmaps:
        content.append({"type": "text", "text": f"\nHeatmap: {hm['filename']}"})
        content.append({
            "type": "image",
            "source": {
                "type":       "base64",
                "media_type": hm["media_type"],
                "data":       hm["base64_data"]
            }
        })
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": content}]
    )
    print("  Claude analysis complete.")
    return message.content[0].text


# ─────────────────────────────────────────────
#  STEP 4: FORMAT HTML EMAIL
# ─────────────────────────────────────────────

BADGES = {
    "executive":   "SUMMARY",
    "trends":      "TRENDS",
    "device":      "DEVICES",
    "anomaly":     "ANOMALIES",
    "metadata":    "SESSIONS",
    "funnel":      "FUNNEL",
    "recordings":  "RECORDINGS",
    "heatmap":     "HEATMAPS",
    "access":      "ACCESSIBILITY",
    "forms":       "FORMS",
    "navigation":  "NAVIGATION",
    "struggled":   "STRUGGLES",
    "recommended": "ACTIONS",
}

def get_badge(title):
    tl = title.lower()
    for key, label in BADGES.items():
        if key in tl:
            return label
    return "SECTION"

def inline_fmt(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*',     r'<em>\1</em>', text)
    text = re.sub(r'`([^`]+)`',     r'<code>\1</code>', text)
    return text

def md_to_html(text):
    lines = text.split("\n")
    out   = []
    in_ul = in_ol = False

    def close():
        nonlocal in_ul, in_ol
        if in_ul: out.append("</ul>"); in_ul = False
        if in_ol: out.append("</ol>"); in_ol = False

    for line in lines:
        if line.startswith("## "):
            close()
            title = re.sub(r'^\d+\.\s+', '', line[3:].strip())
            badge = get_badge(title)
            out.append(f'<h2><span class="badge">{badge}</span>{title}</h2>')
        elif line.startswith("### "):
            close(); out.append(f'<h3>{line[4:].strip()}</h3>')
        elif re.match(r'^\d+\. ', line):
            m = re.match(r'^\d+\. (.+)', line)
            if not in_ol: close(); out.append("<ol>"); in_ol = True
            out.append(f"<li>{inline_fmt(m.group(1))}</li>")
        elif re.match(r'^[-*] ', line):
            m = re.match(r'^[-*] (.+)', line)
            if not in_ul: close(); out.append("<ul>"); in_ul = True
            out.append(f"<li>{inline_fmt(m.group(1))}</li>")
        elif line.strip() in ("---", "___"):
            close(); out.append("<hr>")
        elif line.strip() == "":
            close()
        else:
            close()
            row = inline_fmt(line)
            if "[CRITICAL]" in row:
                out.append(f'<p class="alert-red">{row}</p>')
            elif "[WIN]" in row:
                out.append(f'<p class="alert-green">{row}</p>')
            else:
                out.append(f"<p>{row}</p>")
    close()
    return "\n".join(out)


def get_month_label():
    """Returns the previous month name e.g. 'May 2026'"""
    today     = datetime.utcnow()
    month_num = today.month - 1 if today.month > 1 else 12
    year      = today.year if today.month > 1 else today.year - 1
    return datetime(year, month_num, 1).strftime("%B %Y")


def format_html_email(report_text, heatmap_count):
    body      = md_to_html(report_text)
    month     = get_month_label()
    hm_note   = f"{heatmap_count} heatmap(s) analysed" if heatmap_count else "No heatmaps"
    generated = datetime.utcnow().strftime("%B %d, %Y")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:#0d0d14;color:#d0d0e8;font-size:15px;line-height:1.7}}
.wrap{{max-width:700px;margin:28px auto;background:#13131e;border-radius:14px;border:1px solid #22223a;overflow:hidden}}
.hdr{{background:linear-gradient(140deg,#1a0640,#0c1a45,#001c30);padding:36px 40px 30px}}
.hdr-tag{{display:inline-block;background:rgba(130,80,255,.2);color:#a480ff;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:3px 10px;border-radius:20px;border:1px solid rgba(130,80,255,.3);margin-bottom:14px}}
.hdr h1{{font-size:24px;font-weight:700;color:#fff;margin-bottom:6px}}
.hdr p{{color:#6060a0;font-size:13px}}
.hdr p b{{color:#a480ff}}
.meta{{display:flex;border-bottom:1px solid #1c1c2e}}
.mc{{flex:1;padding:12px 16px;border-right:1px solid #1c1c2e;font-size:11px}}
.mc:last-child{{border-right:none}}
.ml{{display:block;color:#40405a;text-transform:uppercase;letter-spacing:.8px;font-weight:700;margin-bottom:2px}}
.mv{{color:#8080b0;font-weight:500}}
.body{{padding:8px 40px 32px}}
h2{{font-size:15px;font-weight:700;color:#dcdcf8;display:flex;align-items:center;gap:8px;margin:28px 0 12px;padding-bottom:8px;border-bottom:1px solid #1c1c2e}}
.badge{{background:#7c3aed;color:#fff;font-size:9px;font-weight:700;letter-spacing:1.2px;padding:2px 7px;border-radius:4px;flex-shrink:0}}
h3{{font-size:11px;font-weight:700;color:#5050a0;text-transform:uppercase;letter-spacing:.8px;margin:14px 0 5px}}
p{{color:#9898c8;margin-bottom:9px}}
strong{{color:#d8d8f4;font-weight:600}}
em{{color:#a0a0c8;font-style:italic}}
code{{font-family:'JetBrains Mono',monospace;font-size:12px;background:#1a1a2e;color:#a480ff;padding:1px 5px;border-radius:3px;border:1px solid #28284a}}
hr{{border:none;border-top:1px solid #1c1c2e;margin:18px 0}}
ul,ol{{padding-left:20px;margin-bottom:10px}}
li{{color:#9898c8;margin-bottom:4px}}
li strong{{color:#d0d0f0}}
.alert-red{{background:rgba(220,38,38,.08);border-left:3px solid rgba(220,38,38,.5);padding:8px 12px;border-radius:0 5px 5px 0;margin-left:-12px}}
.alert-green{{background:rgba(22,163,74,.08);border-left:3px solid rgba(22,163,74,.4);padding:8px 12px;border-radius:0 5px 5px 0;margin-left:-12px}}
.ftr{{background:#0a0a10;padding:16px 40px;text-align:center;font-size:11px;color:#303050;border-top:1px solid #18182a}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <div class="hdr-tag">Monthly UX Intelligence</div>
    <h1>UX Report - {month}</h1>
    <p><b>{PRODUCT_NAME}</b> - Microsoft Clarity + Claude AI</p>
  </div>
  <div class="meta">
    <div class="mc"><span class="ml">Period</span><span class="mv">{month}</span></div>
    <div class="mc"><span class="ml">Data</span><span class="mv">Clarity CSV</span></div>
    <div class="mc"><span class="ml">Heatmaps</span><span class="mv">{hm_note}</span></div>
    <div class="mc"><span class="ml">Generated</span><span class="mv">{generated}</span></div>
  </div>
  <div class="body">
    {body}
  </div>
  <div class="ftr">Auto-generated - Microsoft Clarity + Claude (Anthropic)</div>
</div>
</body>
</html>"""


# ─────────────────────────────────────────────
#  STEP 5: SEND VIA SENDGRID
# ─────────────────────────────────────────────

def send_email(html_content):
    month   = get_month_label()
    subject = f"[{PRODUCT_NAME}] Monthly UX Report - {month}"
    message = Mail(
        from_email=EMAIL_SENDER,
        to_emails=EMAIL_RECIPIENTS,
        subject=subject,
        html_content=html_content
    )
    try:
        sg       = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"  Report emailed. Status: {response.status_code}")
    except Exception as e:
        print(f"  SendGrid error: {e.body}")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n  {PRODUCT_NAME} Monthly UX Report starting...\n")

    print("  [1/4] Reading CSV export...")
    csv_data = read_csv(CSV_FILE)

    print("\n  [2/4] Loading heatmap images...")
    heatmaps = load_heatmaps(HEATMAP_GLOB)

    print("\n  [3/4] Sending to Claude for analysis...")
    report_text = analyse_with_claude(csv_data, heatmaps)

    print("\n  [4/4] Sending via SendGrid...")
    html_email = format_html_email(report_text, len(heatmaps))
    send_email(html_email)

    print(f"\n  Done! {PRODUCT_NAME} monthly UX report delivered.\n")
