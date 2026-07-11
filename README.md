# 🤖 FinBot — AI Personal Finance Assistant (Telegram)

Chat with your money like you'd chat with a friend. FinBot turns free-form
messages, receipt photos, bank statement PDFs, CSV files, and voice notes
into structured rows in **your own Google Sheet** — matched exactly to the
*Personal Finance Template* spreadsheet, no manual spreadsheet work.

```
"Makan bakso 25rb"           →  ✅ Expense · Lunch · Rp25.000
"Gajian 8.5 juta masuk BCA"  →  ✅ Income · Salary · Rp8.500.000
"Nabung emergency fund 500rb" →  ✅ Transfer · Emergency Fund · Rp500.000
📸 [receipt photo]           →  ✅ OCR'd, extracted, confirmed
📄 [bank_statement.pdf]      →  ✅ N transactions previewed & imported
🎙️ [voice note]              →  ✅ transcribed & parsed
```

**No service account. No Google API key. No credentials file at all.**
The bot never talks to the Google Sheets API directly — it POSTs to a small
Google Apps Script Web App that lives *inside your own spreadsheet*, and
that script does the actual reading and writing. See [Architecture](#architecture).

## Table of Contents
1. [Architecture](#architecture)
2. [Google Apps Script Setup](#google-apps-script-setup) — replaces service accounts
3. [Telegram Bot Setup](#telegram-bot-setup)
4. [Local Development](#local-development)
5. [Railway Deployment](#railway-deployment)
6. [Webhook](#webhook)
7. [Folder Structure](#folder-structure)
8. [Bot Commands](#bot-commands)
9. [How It Maps to Your Spreadsheet](#how-it-maps-to-your-spreadsheet)
10. [Environment Variables](#environment-variables)

---

## Architecture

```
Telegram → Railway (FastAPI + aiogram) → HTTPS POST → Google Apps Script Web App → Google Sheets
                    │
      ┌─────────────┼──────────────┬──────────────┐
      ▼             ▼              ▼              ▼
   llm/           ocr/           pdf/         repositories/
(OpenAI/Claude/  (Tesseract +  (pdfplumber/  (ONE module: apps_script_client —
  Gemini)         OpenCV)       PyMuPDF)      the only thing that ever calls
                                               out to Google, over plain HTTP)
```

**Why Apps Script instead of a service account?**
- **Zero credentials to manage.** No JSON key file, no IAM roles, no
  "share this sheet with a robot email" step.
- **The script runs *as you*,** inside your own Google account, so it
  already has permission to your sheet — nothing to grant.
- **One shared secret** (a random string you pick) is all that stands
  between the internet and your spreadsheet, since a Web App deployed with
  "Anyone" access has no built-in auth otherwise.
- The trade-off: every "action" the bot can perform (add/edit/delete a
  transaction, read data, compute balance, touch Budget/Goal cells) has to
  be a named function in `google-apps-script/Code.gs` — there's no generic
  "run any spreadsheet formula" escape hatch, which is a feature, not a bug.

**Design principles**
- **The spreadsheet's structure is never changed.** No new tabs, no new
  columns, no rows inserted outside what the template already reserves.
  Code.gs only reads/writes cells that already exist in *your* uploaded
  template.
- **The LLM never touches Google Sheets.** It only produces a validated
  Pydantic `TransactionCreate`; `apps_script_client` is the sole caller of
  Google, over one HTTP action per request.
- **Provider-agnostic LLM layer.** Switch between OpenAI / Claude / Gemini
  with one env var (`LLM_PROVIDER`), no code changes.
- **Confirm before save.** Every parsed transaction shows a card with
  ✅ Save / ✏️ Edit / ❌ Cancel before it touches the sheet.
- **Budget threshold checks are atomic.** Apps Script increments the
  Budget Planner's AKTUAL cell and checks 80/90/100% in the *same* call
  that appends the transaction — no separate read-modify-write race.

Full PRD, DB mapping, and diagrams: see [`docs/01_DESIGN.md`](docs/01_DESIGN.md)
(written for the original service-account version — the sheet mapping
section is superseded by [How It Maps to Your Spreadsheet](#how-it-maps-to-your-spreadsheet)
below, which matches your actual uploaded template).

---

## Google Apps Script Setup

This replaces the old "create a service account" flow entirely — there is
no Google Cloud Console step anymore.

1. Open **your** Google Sheet (the Personal Finance Template).
2. **Extensions → Apps Script.** This opens the script editor, already
   bound to your spreadsheet — it can read/write it as you, with no
   sharing step needed.
3. Delete anything in the default `Code.gs` file and paste in the entire
   contents of [`google-apps-script/Code.gs`](google-apps-script/Code.gs)
   from this repo.
4. **Project Settings** (gear icon, left sidebar) → **Script Properties**
   → **Add script property** → name it `SHARED_SECRET`, value = any long
   random string (e.g. generate one with `openssl rand -hex 24`). This is
   the only thing that authenticates the bot to your script — keep it
   secret, treat it like a password.
5. Back in the editor, select `testPing` from the function dropdown (top
   toolbar) and click **Run** once. Google will ask you to authorize the
   script — approve it (it's your own script, running as you, touching
   only your own sheet). Check **View → Logs** to confirm it printed
   balance/budget/goal data with no errors — this proves the script can
   read your sheet's actual tabs before you deploy it.
6. **Deploy → New deployment.** Click the gear next to "Select type" →
   **Web app**. Set:
   - **Execute as:** Me
   - **Who has access:** Anyone
   (this doesn't mean "anyone can edit your sheet" — it means anyone who
   *also* has your `SHARED_SECRET` can call the endpoint; without the
   secret, every call is rejected with `Unauthorized`.)
7. Click **Deploy**, authorize again if prompted, then copy the **Web app
   URL** (ends in `/exec`).
8. Put that URL and your secret into the bot's `.env`:
   ```
   GAS_WEB_APP_URL=https://script.google.com/macros/s/xxxxxxxx/exec
   GAS_SHARED_SECRET=<the same random string from step 4>
   ```

**Updating the script later:** edit `Code.gs` in the Apps Script editor,
then **Deploy → Manage deployments → ✏️ (edit) → Version: New version →
Deploy**. Just saving the file is *not* enough — Web Apps run whatever
version was active at your last deployment.

**Sanity-checking without the bot:** you can `curl` the Web App directly:
```bash
curl -X POST "$GAS_WEB_APP_URL" \
  -H "Content-Type: application/json" \
  -d '{"secret":"YOUR_SECRET","action":"getBalance","payload":{}}'
```

## Telegram Bot Setup

1. Message [@BotFather](https://t.me/BotFather) on Telegram.
2. `/newbot` → follow the prompts → copy the token into `BOT_TOKEN`.
3. Optionally set a description, profile picture, and command list via
   BotFather (`/setcommands`) using:
   ```
   start - Welcome message
   help - Show all commands
   today - Today's summary
   month - This month's summary
   summary - Quick overview
   saldo - Calculate your balance (all-time)
   report - Generate a PDF report
   chart - Visualize your spending
   budget - Set & check budgets
   goals - Track savings goals
   export - Export your data
   settings - View preferences
   ```

## Local Development

```bash
git clone <your-repo>
cd finance-bot
cp .env.example .env        # fill in your real values (see sections above)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# System dependency for OCR (Ubuntu/Debian):
sudo apt-get install tesseract-ocr tesseract-ocr-ind

uvicorn app.main:app --reload --port 8000
```

For local development, Telegram webhooks need a public HTTPS URL. Use
[ngrok](https://ngrok.com/) (`ngrok http 8000`) and set `BASE_URL` to the
ngrok URL, or swap `bot.set_webhook`/the webhook route for
`dp.start_polling(bot)` in `app/main.py` for polling mode instead — both
are standard aiogram patterns.

Run the test suite (all Python-side logic, plus a Node-based mock of the
Apps Script runtime used while developing `Code.gs`):
```bash
pytest tests/ -v
```

## Railway Deployment

1. Push this repo to GitHub.
2. On [Railway](https://railway.app/), **New Project → Deploy from GitHub repo**.
3. Railway auto-detects the `Dockerfile` (via `railway.json`) and builds it.
4. Under **Variables**, add every key from `.env.example` with your real
   values — including `GAS_WEB_APP_URL` and `GAS_SHARED_SECRET` from the
   Apps Script setup above. Do **not** set `PORT` — Railway injects it
   automatically.
5. Once deployed, copy the generated public domain (Settings → Networking →
   **Generate Domain**) into `BASE_URL`, then redeploy so the webhook
   registers against the correct URL.
6. On startup, the app automatically calls Telegram's `setWebhook` with
   `BASE_URL + /webhook/<WEBHOOK_SECRET>` — no manual `curl` needed.

## Webhook

The webhook path is `/webhook/<WEBHOOK_SECRET>` (kept secret/random so
nobody can POST fake Telegram updates). Registration happens automatically
in the FastAPI `lifespan` startup hook (`app/main.py`).

## Folder Structure

```
finance-bot/
├── app/
│   ├── main.py                # FastAPI app, webhook route, startup wiring
│   ├── bot/
│   │   ├── factory.py          # builds aiogram Bot + Dispatcher
│   │   ├── keyboards.py        # inline keyboard builders
│   │   ├── handlers/           # one file per feature (text, photo, document, voice, budget, goals...)
│   │   ├── middlewares/        # logging + error-guard middleware
│   │   └── routers/            # registers all routers in the right order
│   ├── services/               # business logic: transaction, summary, budget, goal, chart, report, export, voice, ai_chat
│   ├── repositories/           # turn Apps Script JSON responses into Pydantic models
│   ├── google/
│   │   └── apps_script_client.py   # the ONLY module that calls Google — one httpx POST per action
│   ├── llm/                    # provider-agnostic parser (OpenAI/Claude/Gemini) + prompts
│   ├── ocr/                    # receipt OCR pipeline (OpenCV preprocessing + Tesseract)
│   ├── pdf/                    # bank statement/CSV extraction + PDF report generation
│   ├── schemas/                # Pydantic v2 models (Transaction, BudgetStatus, Goal)
│   ├── models/                 # enums (TransactionType, TransactionSource)
│   ├── config/                 # Settings (pydantic-settings) + the exact category taxonomy from your sheet
│   ├── utils/                  # retry decorators, currency normalization, message formatting
│   └── prompts/                # LLM system prompts
├── google-apps-script/
│   └── Code.gs                 # paste this into Extensions → Apps Script in your sheet — see setup above
├── tests/                      # pytest unit tests
├── docs/01_DESIGN.md           # original PRD / diagrams (see note above)
├── Dockerfile
├── docker-compose.yml
├── Procfile
├── railway.json
├── requirements.txt
└── .env.example
```

## Bot Commands

| Command | Description |
|---|---|
| `/start`, `/help` | Onboarding & command list |
| *(just type)* | Log a transaction in natural language |
| 📸 photo | Log a transaction from a receipt (OCR) |
| 📄 PDF/CSV | Import a bank statement or transaction export |
| 🎙️ voice note | Log a transaction by speaking |
| `/today` | Today's income/expense/transfer summary |
| `/month`, `/summary` | This month's summary |
| `/saldo` | **Hitung saldo** — all-time balance computed server-side from every row in Cashflow Harian |
| `/report` | Generate a full PDF report |
| `/chart` | Pie/bar/line/income-vs-expense charts |
| `/export` | Export all transactions as CSV |
| `/budget` | View live Budget Planner status; `/budget <label> <amount>` to set one (label must match a row already in your Budget Planner tab) |
| `/goals` | View live Goal Planning status; `/goals add <name> <amount>` to contribute; `/goals target <name> <amount>` to change a target |
| `/settings` | View current preferences |
| *(ask a question)* | "How much did I spend on food this month?" — answered by the AI over your real data |

## How It Maps to Your Spreadsheet

This bot is wired to the exact structure of the uploaded *Personal Finance
Template*, not a generic schema — nothing about the sheet's layout was
changed.

**`Cashflow Harian`** (the transaction log) — every save appends one row,
columns A:M exactly as the template defines them:
`Transaction ID · Date · Time · Type · Category · Need/Want/Goal ·
Fixed/Variable · Amount · Account · Merchant · Payment Method · Notes · Tags`.
`Transaction ID` (`TRX000123`) is assigned by Apps Script itself by
scanning for the current highest ID — Python never guesses it. `Category`
must be one of the ~58 values in the template's own dropdown list (copied
exactly into `app/config/categories.py`); `Need/Want/Goal` and
`Fixed/Variable` are *derived* from the category automatically, never
asked of the LLM, so they can never drift out of sync with the sheet's own
lookup table.

**`Type`** only has 3 values in this template — `Expense`, `Income`,
`Transfer` — matching the sheet's dropdown. Investments and savings-goal
contributions are `Transfer` transactions under a Category like
`Emergency Fund` / `Investment` / `House`, exactly as the template models it.

**`Budget Planner`** — the bot reads/writes the 14 pre-existing category
rows (Needs/Wants/Saving & Invest sections). Saving an Expense or Transfer
auto-increments the matching row's **AKTUAL** column via the
`BUDGET_CATEGORY_MAP` table (e.g. `Fuel`/`Transportation`/`Parking` all
roll up into the "Transportasi" row), and fires a Telegram alert the
moment that row crosses 80/90/100% of its budget. New budget *categories*
can't be created from the bot — the template's SUM ranges are sized to
those exact 14 rows.

**`Goal Planning`** — the bot reads/contributes to the 3 goals the template
ships with (Dana Darurat, Mobil, Menikah). Their *names* are formula-linked
from the `Cashflow` tab's TABUNGAN & INVESTASI section by the template
itself, so they aren't editable from the bot — only `Target` and
`Sudah Terkumpul` (current amount) are, via `/goals target` and
`/goals add`.

**Not wired up (out of scope, to avoid guessing at your formulas):**
`Dashboard`, `Aset & Liabilitas`, `Investment Tracker`, `Financial Ratios`,
`Insights & Rekomendasi` — these stay exactly as the template computes
them; the bot doesn't write to them.

## Environment Variables

See [`.env.example`](.env.example) for the full annotated list —
`BOT_TOKEN`, `OPENAI_API_KEY` / `CLAUDE_API_KEY` / `GEMINI_API_KEY` (+
`LLM_PROVIDER` to pick the active one), `GAS_WEB_APP_URL`,
`GAS_SHARED_SECRET`, `BASE_URL`, `WEBHOOK_SECRET`, `PORT`, `TIMEZONE`,
`DEFAULT_CURRENCY`.

---

Built for clarity and hackability: every layer (handlers → services →
repositories → Apps Script) has one job, so extending FinBot — a new
command, a new LLM provider, a new sheet action — means adding one
function, not touching ten.
