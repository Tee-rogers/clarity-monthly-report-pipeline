Clarity UX Report Pipeline

An automated reporting pipeline that transforms raw Microsoft Clarity behavioral data into structured, AI-analyzed UX insights — delivered straight to your inbox.

Built to solve a real product team problem: turning weeks of scattered session data across 11 products into a single, prioritized monthly report without manual analysis.

The Problem

Our product team used Microsoft Clarity to track user behavior across 11 products, but reviewing raw session recordings, heatmaps, and click data manually didn't scale. Insights were inconsistent, time-consuming to produce, and easy to deprioritize during busy sprints — which meant real UX issues went unnoticed for weeks.

The Solution

This pipeline:


Ingests Microsoft Clarity behavioral data (sessions, clicks, scroll depth, device/browser breakdown, heatmaps)
Analyzes it using Claude (Anthropic's AI model) to identify patterns, anomalies, and prioritized action items
Delivers a fully formatted HTML report via email — no manual review required


The report covers 13 structured sections, including:


Executive summary & monthly UX trends
Device/browser breakdown with usage percentages
Anomaly detection (e.g. rage click spikes, unusual drop-off patterns)
Accessibility & usability signals
Forms & task completion friction
Navigation & findability issues
A ranked "where users struggled most" map
Top 5 recommended actions, prioritized by impact


Why This Approach

The original plan used Clarity's live API for full automation. In practice, the API only supports 1–3 day windows, which doesn't support monthly historical reporting. Rather than abandon the automation goal, the pipeline was redesigned around a CSV export step, keeping the AI analysis and email delivery fully automated while working within the platform's real constraints.

This kind of constraint-driven iteration — adjusting the technical approach without losing the underlying goal — was a key part of getting this into production use.

Tech Stack


Python — orchestration logic
Anthropic Claude API — UX data analysis and report generation
Microsoft Clarity — source behavioral data (CSV export + heatmap screenshots)
Resend / SendGrid — automated email delivery
HTML/CSS — custom report template


How It Works

Clarity CSV Export + Heatmap Screenshots
              ↓
      Claude AI Analysis
   (13-section structured report)
              ↓
     HTML Email Formatting
              ↓
      Automated Email Delivery

Setup

bashpip install anthropic resend


Export your Clarity dashboard data as CSV
(Optional) Add heatmap screenshots to the project folder
Add your API keys to the configuration section at the top of the script
Run:


bashpython3 clarity_monthly_report.py

Sample Output

See /sample-report for a real (anonymized) report generated from this pipeline, showing the kind of actionable, specific insights it surfaces — including a JavaScript bug responsible for a 14% dead-click rate, identified in the very first run.

Impact


Eliminated ~10–15 minutes of manual reporting per product, per reporting cycle
Scaled to 11 products without added manual effort
Surfaced real, fixable bugs (not just metrics) within the first report generated



Built by [Your Name] · Product/UX, Liaison Educational
