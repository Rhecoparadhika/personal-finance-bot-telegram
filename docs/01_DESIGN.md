# AI Personal Finance Assistant — Design Document

> **⚠️ Architecture note (post-revision):** This document describes the
> *original* design, which used a Google service account + gspread to talk
> to Sheets directly, and a generic category schema. The shipped version
> was revised to (1) use a **Google Apps Script Web App** instead of a
> service account — see [`README.md § Architecture`](../README.md#architecture)
> and [`google-apps-script/Code.gs`](../google-apps-script/Code.gs) — and
> (2) match the exact tab/column layout and category taxonomy of the
> user's own *Personal Finance Template* spreadsheet instead of a generic
> one — see [`README.md § How It Maps to Your Spreadsheet`](../README.md#how-it-maps-to-your-spreadsheet).
> The PRD, roadmap, and diagrams below are still accurate for everything
> *except* the Google Sheets integration and DB Mapping/schema sections.

## 1. Product Requirement Document (PRD)

**Product name:** FinBot — AI Personal Finance Assistant on Telegram
**Owner:** Personal use / live webinar demo
**Problem:** Manually logging expenses into Google Sheets is friction-heavy and gets abandoned within days. Users think in natural language ("makan bakso 25rb"), not in spreadsheet rows.
**Solution:** A Telegram bot that accepts free-form text, photos of receipts, PDF bank statements, CSV exports, and voice notes, uses an LLM to turn them into structured transactions, confirms with the user, and appends to Google Sheets (the single source of truth / "database"). The bot also answers ad-hoc questions about spending, tracks budgets and goals, and generates charts/PDF reports on demand.

**Goals**
- Zero-friction capture: one Telegram message = one logged transaction (or several).
- Google Sheets stays human-readable and remains the only persistence layer (no separate DB to run/host).
- Support Indonesian, English, and mixed-language input.
- Multi-modal input: text, image (OCR), PDF, CSV, voice.
- Conversational analytics ("how much did I spend on food this month?").
- Budgets with threshold alerts, savings/investment goals with progress tracking.
- Deployable in minutes on Railway via webhook.

**Non-goals**
- Multi-tenant SaaS, billing, or user management (single-user / small-group personal tool).
- Bank account linking / Open Banking APIs (out of scope — PDF/CSV import instead).
- Mobile/web app — Telegram is the only UI.

**Primary user story**
> As the sheet owner, I type or forward something to my bot, it replies with a clean confirmation card, and my Google Sheet is updated — I never open Sheets except to look at pretty totals I could've also asked the bot for.

## 2. Folder Structure

```
finance-bot/
├── app/
│   ├── main.py                     # FastAPI app + aiogram webhook wiring
│   ├── bot/
│   │   ├── handlers/                # one file per feature: text, photo, document, voice, commands
│   │   ├── middlewares/             # logging, error-guard, user-context
│   │   └── routers/                 # aiogram Router registration/aggregation
│   ├── services/                    # business logic orchestration (transaction_service, summary_service, budget_service, goal_service, report_service, chart_service)
│   ├── repositories/                 # Google Sheets repository (the only persistence)
│   ├── llm/                         # provider-agnostic LLM parser (OpenAI/Claude/Gemini), prompts, JSON validation
│   ├── ocr/                         # receipt OCR pipeline (OpenCV preprocessing + Tesseract)
│   ├── pdf/                         # bank statement PDF extraction (pdfplumber/PyMuPDF) + PDF report generation
│   ├── schemas/                     # Pydantic v2 models (Transaction, Budget, Goal, LLM I/O)
│   ├── models/                      # enums (TransactionType, Category...)
│   ├── google/                      # Google Sheets API client bootstrap
│   ├── config/                      # Settings (pydantic-settings), category config, constants
│   ├── utils/                       # retry decorators, currency/date normalization, formatting
│   └── prompts/                     # system prompts for the LLM parser (txt/jinja)
├── tests/
├── Dockerfile
├── docker-compose.yml
├── Procfile
├── railway.json
├── requirements.txt
├── .env.example
└── README.md
```

**Why this shape:** handlers are thin (parse Telegram update → call a service). Services hold business rules and are Telegram-agnostic (testable). Repositories are the only code that talks to Google Sheets. LLM/OCR/PDF are isolated adapters behind interfaces so providers can be swapped without touching business logic.

## 3. Database Mapping (Google Sheets)

Spreadsheet = database. Each tab = a table.

### Tab: `Transactions` (append-only ledger)
| Column | Type | Notes |
|---|---|---|
| Date | date (YYYY-MM-DD) | transaction date, not created date |
| Type | enum | Expense / Income / Investment / Transfer / Debt / Loan Payment / Saving |
| Category | string | from category config |
| Sub Category | string | optional |
| Description | string | raw or cleaned description |
| Merchant | string | detected merchant name |
| Amount | number | positive; sign/direction implied by Type |
| Payment Method | string | Cash / Bank Transfer / QRIS / Credit Card / e-Wallet |
| Account | string | e.g. "BCA", "Cash", "OVO" |
| Tags | string | comma-separated |
| Notes | string | free text |
| Created At | datetime | ISO8601, when the row was written |
| Confidence Score | float | 0–1, LLM's confidence |
| Row ID | string | UUID, used for update/delete/search |
| Source | string | text / ocr / pdf / csv / voice |

### Tab: `Budgets`
| Column | Type |
|---|---|
| Category | string |
| Monthly Limit | number |
| Alert 80 Sent | bool (per month, reset monthly) |
| Alert 90 Sent | bool |
| Alert 100 Sent | bool |
| Month | YYYY-MM |

### Tab: `Goals`
| Column | Type |
|---|---|
| Goal ID | string |
| Name | string |
| Type | Emergency Fund / Vacation / Wedding / House / Investment Target / Custom |
| Target Amount | number |
| Current Amount | number (derived from linked category/tag or manually updated) |
| Target Date | date |
| Created At | datetime |

### Tab: `Settings` (key/value)
| Key | Value |
|---|---|
| default_currency | IDR |
| timezone | Asia/Jakarta |
| llm_provider | openai / claude / gemini |

## 4. Application Flow Diagram (text form)

```
Telegram message
   │
   ▼
Webhook (FastAPI) ──▶ aiogram Dispatcher ──▶ Middleware (logging, error guard)
   │
   ▼
Router dispatch by content type
   ├─ text        → TextHandler
   ├─ photo       → PhotoHandler   (OCR service)
   ├─ document    → DocumentHandler(PDF service / CSV parser)
   ├─ voice       → VoiceHandler   (Whisper transcription → text pipeline)
   └─ command     → CommandHandlers (/summary /today /month /report /chart /budget /goals /export /settings)
   │
   ▼
TransactionService.parse_and_stage()
   │  → LLM Parser (provider-agnostic) → Pydantic Transaction(s) + confidence
   │  → Validation layer (category whitelist, amount > 0, date sane)
   │  → Duplicate check (SheetsRepository.search_transaction)
   ▼
Reply: confirmation card + inline keyboard [✅ Save] [✏️ Edit] [❌ Cancel]
   │
   ▼ (on ✅ Save callback)
SheetsRepository.append_transaction()
   │
   ▼
BudgetService.check_thresholds() → alert message if 80/90/100% crossed
   │
   ▼
Confirmation message sent back to user
```

## 5. Sequence Diagram — "Makan bakso 25rb" happy path

```
User        Telegram        FastAPI/aiogram      TransactionService     LLMParser        SheetsRepo        BudgetService
 │  text        │                  │                     │                  │                │                 │
 │──────────────▶                  │                     │                  │                │                 │
 │              │──webhook POST────▶                     │                  │                │                 │
 │              │                  │──parse_and_stage()──▶                  │                │                 │
 │              │                  │                     │──parse(text)────▶│                │                 │
 │              │                  │                     │◀─Transaction(s)──│                │                 │
 │              │                  │                     │──validate()      │                │                 │
 │              │                  │◀─staged tx + card────                  │                │                 │
 │◀─confirmation card + buttons────│                     │                  │                │                 │
 │──tap ✅──────▶                  │                     │                  │                │                 │
 │              │──callback_query──▶                     │                  │                │                 │
 │              │                  │──confirm_save()─────▶                  │                │                 │
 │              │                  │                     │──append_transaction()──────────────▶│               │
 │              │                  │                     │◀────────────────────────────────────│ row written   │
 │              │                  │                     │──check_thresholds()─────────────────────────────────▶│
 │              │                  │                     │◀───────────────────────────────────────────────────│ (alert?)
 │◀─"✅ Saved" + optional alert────│                     │                  │                │                 │
```

## 6. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          Telegram                                  │
└───────────────────────────────┬───────────────────────────────────┘
                                 │ Webhook (HTTPS)
┌───────────────────────────────▼───────────────────────────────────┐
│                     FastAPI (uvicorn, Railway)                     │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │                aiogram v3 Dispatcher + Routers               │    │
│  │  handlers/ ── middlewares/ (logging, error guard, throttle) │    │
│  └───────────────────────┬───────────────────────────────────┘    │
│                           │                                        │
│  ┌────────────────────────▼───────────────────────────────────┐   │
│  │                        services/                             │  │
│  │  transaction_service · summary_service · budget_service      │  │
│  │  goal_service · report_service · chart_service                │  │
│  └───┬───────────┬───────────┬───────────┬───────────┬─────────┘  │
│      │           │           │           │           │            │
│  ┌───▼───┐  ┌────▼────┐ ┌────▼────┐ ┌────▼────┐ ┌────▼────┐       │
│  │ llm/  │  │  ocr/   │ │  pdf/   │ │utils/   │ │repositories/│    │
│  │OpenAI │  │Tesseract│ │pdfplumber│ │retry,   │ │SheetsRepo  │    │
│  │Claude │  │+OpenCV  │ │PyMuPDF  │ │format   │ │(gspread)   │    │
│  │Gemini │  │         │ │         │ │         │ │            │    │
│  └───────┘  └─────────┘ └─────────┘ └─────────┘ └─────┬──────┘    │
└──────────────────────────────────────────────────────────┼────────┘
                                                             │ Google Sheets API
                                                    ┌────────▼────────┐
                                                    │  Google Sheets   │
                                                    │  (the database)  │
                                                    └──────────────────┘
```

## 7. Development Roadmap

**Phase 0 — Foundations**
- Config/settings, logging, project skeleton, Google Sheets auth, health check route.

**Phase 1 — Core text flow (MVP, demo-ready)**
- LLM parser (single provider first, provider-agnostic interface), Pydantic validation, SheetsRepository.append_transaction, text handler, confirmation inline keyboard, /start /help.

**Phase 2 — Analytics**
- /today /month /summary, AI chat Q&A over sheet data, top categories/merchants.

**Phase 3 — Multi-modal input**
- Photo OCR pipeline, PDF bank statement import with preview+confirm, CSV import, voice via Whisper.

**Phase 4 — Budgets & Goals**
- /budget CRUD + threshold alerts, /goals CRUD + progress tracking.

**Phase 5 — Reporting & Visualization**
- /chart (bar/pie/line via matplotlib), /report (PDF via reportlab), /export (CSV/XLSX).

**Phase 6 — Hardening & Deployment**
- Retry/error handling, duplicate detection, rate limiting, Dockerfile/railway.json/webhook auto-registration, README, tests.

This document is followed by the full source tree.
