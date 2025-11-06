# Nuvix Tickets (Discord, Python)

Render-ready professional ticket bot with:
- Ticket panel + category modals (Purchases / Not Received / Replace / Support)
- Private channels with Assign / Unclaim / Close buttons
- Trial Support+ permissions for commands, assign & close
- Admin+ for /delete, blacklist add/remove, /panel
- Transcripts saved to `data/transcripts/` and sent to Logs + Transcripts channels
- Deleted tickets also send their transcripts
- DM on close with review (1–5 stars + comment) -> forwards to REVIEWS channel
- Inactivity warning after 24h of no messages in ticket
- `/activity` counts tickets where the staff sent ≥5 distinct messages
- Command usage logs and ticket action logs

## Quick start
1. Copy `.env.example` to `.env` and fill with your IDs (keep TOKEN secret).
2. `pip install -r requirements.txt`
3. `python bot.py` (or deploy on Render with the provided Procfile and render.yaml)
