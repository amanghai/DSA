# 📞 Nazakat Telecom — Mobile-Friendly Google Sheets Call Tracker

**Prepared as:** Data & Operations design for the telecalling team
**Primary users:** Telecallers working **exclusively from mobile phones** (Google Sheets app)
**Goal:** Fast, low-typing call logging on a phone + live metrics for the manager

This folder contains two things:

| File | What it is |
|------|-----------|
| **`Nazakat_Call_Tracker_Template.xlsx`** | A ready-to-use template — upload to Google Drive and open as a Google Sheet. Dropdowns, frozen header, tap-to-dial, formulas and the Dashboard are already built. |
| **`README.md`** (this file) | The full design: architecture, mobile setup, formulas and the Google Form option. |

> **Fastest path to live:** Upload the `.xlsx` to Google Drive → *Open with Google Sheets* → *File ▸ Save as Google Sheets* → delete the yellow example row → Share with the team. Then (optionally) add the Google Form from Part 4.

---

## Part 1 — Sheet Architecture

### Recommendation: **one Master Log tab + a Dashboard + a Lists tab**

For a phone-first team, **a single Master "Call Log" tab is the right choice** — not daily tabs and not one tab per category. Reasons:

- **One place to type.** On a phone, hunting for "today's tab" or "the repair tab" costs taps and causes mis-entries. Callers always open the same sheet and add a row.
- **Category is a column, not a tab.** Because *Call Category* is a dropdown field, you can still see "only repairs" instantly with a **Filter view** — without splitting the data.
- **Reporting stays trivial.** Every metric (totals, averages, leads) is one formula over one range. Daily/category tabs would force you to `IMPORTRANGE`/stitch data back together.
- **Daily tabs don't scale.** 30 tabs a month is unmanageable on mobile.

### Tab layout in the template

| Tab | Audience | Purpose |
|-----|----------|---------|
| **Call Log** | Telecallers | One row per call. The only tab the team touches. |
| **Dashboard** | Manager / TL | Live KPIs — calls today, connect rate, avg rating, leads, follow-ups due. Read-only. |
| **Lists** | Manager | The source of every dropdown (categories, statuses, ratings, incentives, caller names). Edit options here. |
| **Guide** | Everyone | One-page in-file quick start. |

> **When to add tabs:** If you ever exceed ~50,000 rows, archive last year into a *"Log 2025"* tab. Keep the current year as the single working `Call Log`.

### Column structure (Call Log)

Columns are grouped exactly as requested — **Basic ▸ Interaction ▸ Upsell/Loyalty** — with a few operational helpers added.

| # | Column | Type | Notes for mobile |
|---|--------|------|------------------|
| A | **Sr.** | Auto | `=IF($B2="","",ROW()-1)` — auto row number. |
| B | **Date & Time** | Timestamp | Auto-filled by the Google Form; or type `24-Jul-2026 10:15`. |
| C | **Customer Name** | Text | |
| D | **Phone Number** | Text | Stored **as text** with country code (`+91 98765 43210`) so the leading `0`/`+` isn't lost. |
| E | **📞 Tap to Call** | Auto link | `HYPERLINK("tel:"&…)` — tap to open the dialer. |
| F | **Call Category** | 🔽 Dropdown | `New Product Purchase • Repair Service • Gadget Purchase` |
| G | **Call Status** | 🔽 Dropdown | `Connected • No Answer • Busy • Callback Requested` |
| H | **Product / Service Details** | Text | What was bought / repaired. |
| I | **Customer Feedback** | Text | Comments / satisfaction summary. |
| J | **Rating** | 🔽 Dropdown | `1 - Poor … 5 - Excellent` |
| K | **Future Purchase Interest** | Text | Any note here = a **lead** (counted on the Dashboard). |
| L | **Incentive Given** | 🔽 Dropdown | `Discount Coupon • Loyalty Points • None` |
| M | **Incentive Code / Value** | Text | e.g. `NAZ10 (10% off)` or `200 pts`. |
| N | **Follow-up Date** | Date | Calendar picker on mobile. |
| O | **Follow-up Done?** | 🔽 Dropdown | `Yes • No • N/A` — operational, drives the "overdue" metric. |
| P | **Telecaller Name** | 🔽 Dropdown | Sourced from the Lists tab. |
| Q | *Rating Score* | Hidden helper | `=IF($J2="","",VALUE(LEFT($J2,1)))` — the number behind the rating, so it can be averaged. **Leave hidden.** |

**Category → mapping** (your A/B/C map to the dropdown values):

- Category A · New Product Buyer → **New Product Purchase**
- Category B · Repair Service Customer → **Repair Service**
- Category C · Accessory & Gadget Buyer → **Gadget Purchase**

---

## Part 2 — Mobile Optimization Setup

Everything below is **already applied** in the template. This is also the checklist to re-apply if you rebuild by hand.

### A. Reduce typing — dropdowns (Data Validation)
The six 🔽 columns above use **Data validation ▸ Dropdown (from a range)** pointing at the **Lists** tab. On the phone this shows a tappable menu instead of a keyboard — the single biggest speed and accuracy win.

*To edit choices:* open the **Lists** tab and change the cells (e.g. add a caller in column G). Every dropdown and the leaderboard update automatically.

### B. Always-visible headers — freeze
- **View ▸ Freeze ▸ 1 row** so column titles stay on screen while scrolling down.
- The template also freezes the **Sr.** column. On a large phone you may also freeze up to **Customer Name** (`View ▸ Freeze ▸ up to column C`) so you always know whose row you're on.

### C. Minimise horizontal scrolling
- **Use the Google Form (Part 4) for data entry** — it's a vertical, one-screen flow with *zero* horizontal scrolling. This is the recommended day-to-day entry method.
- Columns are ordered by how often they're touched, and free-text columns wrap instead of stretching.
- Set sensible column widths (done in the template) so more fits per screen.

### D. Readability / tap targets
- **Font:** Arial **11–12 pt** across the sheet; headers 12 pt bold, white on navy.
- **Row height** is enlarged (~26 px) for easier tapping.
- **Zebra striping** (alternate grey rows) so a row is easy to follow across the screen.
- Gridlines hidden for a cleaner mobile look; colour-coded Dashboard cards (green = good, amber = attention, red = alert).

### E. Tap-to-dial
Column **E** builds `=HYPERLINK("tel:"& <number> ,"📞 Call")`. Tapping it opens the phone dialer. *(If a device's browser blocks `tel:` links, the number in column D is still selectable to copy-and-dial; keeping it as text with the country code is what makes both work.)*

### F. Offline & shortcuts
- In the Sheets app: **⋮ ▸ Make available offline** so logging works with poor signal (syncs later).
- Add the sheet — or better, the Form — to the phone **home screen** for 1-tap access.

### G. Protect the structure
- **Data ▸ Protect sheet/range:** protect the header row, the formula columns (A, E, Q) and the **Lists**/**Dashboard** tabs so callers can't overwrite them. Give callers edit rights only to the data area of **Call Log**.

---

## Part 3 — Formulas & Automation (Dashboard)

The **Dashboard** tab is pre-built with the formulas below. They read the `Call Log` over rows 2–1000 (extend the ranges if you outgrow it). All are standard functions that work identically in Google Sheets and Excel.

### Today
| Metric | Formula |
|--------|---------|
| **Calls Made Today** | `=COUNTIFS('Call Log'!$B$2:$B$1000,">="&TODAY(),'Call Log'!$B$2:$B$1000,"<"&(TODAY()+1))` |
| **Connected Today** | `=COUNTIFS('Call Log'!$B$2:$B$1000,">="&TODAY(),'Call Log'!$B$2:$B$1000,"<"&(TODAY()+1),'Call Log'!$G$2:$G$1000,"Connected")` |
| **Follow-ups Due Today** | `=COUNTIFS('Call Log'!$N$2:$N$1000,TODAY(),'Call Log'!$O$2:$O$1000,"<>Yes")` |
| **Overdue Follow-ups** | `=COUNTIFS('Call Log'!$N$2:$N$1000,"<"&TODAY(),'Call Log'!$N$2:$N$1000,"<>",'Call Log'!$O$2:$O$1000,"<>Yes")` |

### All-time
| Metric | Formula |
|--------|---------|
| **Total Calls Logged** | `=COUNTA('Call Log'!$B$2:$B$1000)` |
| **Average Customer Rating** | `=IFERROR(ROUND(AVERAGE('Call Log'!$Q$2:$Q$1000),2),0)` — uses the hidden numeric *Rating Score* (Q). |
| **Connect Rate** | `=IFERROR(COUNTIF('Call Log'!$G$2:$G$1000,"Connected")/COUNTA('Call Log'!$B$2:$B$1000),0)` (format as %) |
| **Leads Generated (Upsell)** | `=COUNTA('Call Log'!$K$2:$K$1000)` — counts rows where *Future Purchase Interest* is filled. |
| **Incentives Given** | `=COUNTA('Call Log'!$L$2:$L$1000)-COUNTIF('Call Log'!$L$2:$L$1000,"None")` — non-blank minus "None". |

### Breakdowns
- **By status** — `=COUNTIF('Call Log'!$G$2:$G$1000,"Connected")` (repeat for No Answer / Busy / Callback Requested).
- **By category** — `=COUNTIF('Call Log'!$F$2:$F$1000,"New Product Purchase")` (repeat for Repair Service / Gadget Purchase).
- **Telecaller leaderboard** — for each name on the Lists tab:
  - Calls: `=IF(Lists!$G2="","",COUNTIF('Call Log'!$P$2:$P$1000,Lists!$G2))`
  - Avg rating: `=IF(Lists!$G2="","",IFERROR(ROUND(AVERAGEIFS('Call Log'!$Q$2:$Q$1000,'Call Log'!$P$2:$P$1000,Lists!$G2),2),"-"))`

### Why the hidden "Rating Score" column?
The rating dropdown stores readable text like `5 - Excellent`, which can't be averaged directly. Column **Q** extracts the leading number (`VALUE(LEFT(J2,1))`) so `AVERAGE` works — while callers still see the friendly label. Keep Q hidden.

### Optional one-formula report (Google Sheets only)
`QUERY` gives a live pivot without a pivot table — handy for a manager who wants a category summary that grows by itself:
```
=QUERY('Call Log'!B2:P1000,
  "select F, count(F), avg(Q) where B is not null group by F label count(F) 'Calls', avg(Q) 'Avg Rating'",0)
```
*(Put this on a spare area of the Dashboard. It's a Google Sheets function, so add it in Sheets after import — it isn't stored in the `.xlsx`.)*

### Conditional formatting to add in Sheets (2 taps, high value)
- **Follow-up Date (N):** *is before today* **and** Follow-up Done ≠ Yes → red fill (overdue jumps out).
- **Call Status (G):** `No Answer`/`Busy` → light red; `Connected` → light green.
- **Rating (J):** `1 - Poor`/`2 - Fair` → amber (surfaces unhappy customers to call back).

---

## Part 4 — Data Entry Form Option (Google Form → Sheet)

A **Google Form is the recommended day-to-day entry method** on mobile: it's a single vertical screen, every choice is a tap, and it timestamps automatically — no horizontal scrolling, no risk of editing the wrong cell.

### Build it (5 minutes)
1. In your Google Sheet: **Tools ▸ Create a new form** (this links the Form to a new *"Form Responses"* tab automatically).
2. Add these questions **in this order** (matching the Call Log):

   | Question | Form field type | Options |
   |----------|-----------------|---------|
   | Customer Name | Short answer | |
   | Phone Number | Short answer | *(set Response validation ▸ Number/Regex if you want to enforce 10-digit + code)* |
   | Call Category | **Dropdown** / Multiple choice | New Product Purchase · Repair Service · Gadget Purchase |
   | Call Status | **Multiple choice** | Connected · No Answer · Busy · Callback Requested |
   | Product / Service Details | Short answer | |
   | Customer Feedback | Paragraph | |
   | Rating | **Linear scale (1–5)** *or* Dropdown | 1 - Poor … 5 - Excellent |
   | Future Purchase Interest | Paragraph | |
   | Incentive Given | Multiple choice | Discount Coupon · Loyalty Points · None |
   | Incentive Code / Value | Short answer | |
   | Follow-up Date | **Date** | (native mobile calendar picker) |
   | Telecaller Name | **Dropdown** | (the caller picks their own name) |

   > The Form's **Timestamp** column becomes your **Date & Time** — you don't need to ask for it.

3. **Settings ▸** turn on *"Collect email addresses: off"*, *"Limit to 1 response: off"* (callers submit many), and *"Show link to submit another response"* **on** (rapid back-to-back logging).
4. **Put it on the phone home screen:** open the Form's live URL in the phone browser → *Add to Home screen*. Callers now have a **1-tap "Add Call"** icon.

### Make Form responses flow into the clean Call Log
The Form writes to its own *Form Responses* tab (its column order = the question order + a Timestamp). Two ways to feed the polished `Call Log`:

- **Simple:** treat the *Form Responses* tab **as** your log — point the Dashboard formula ranges at it, and drag the Sr./Tap-to-Call/Rating-Score helper formulas down that tab.
- **Cleaner (recommended):** keep `Call Log` as the presentation layer and mirror responses into it with an `ARRAYFORMULA`, mapping each response column to the right Call Log column, e.g.:
  ```
  ='Form Responses 1'!B2   // Customer Name  -> Call Log!C
  ='Form Responses 1'!A2   // Timestamp      -> Call Log!B (Date & Time)
  ```
  Map the remaining fields the same way so the team gets the dropdown/tap-to-dial view while the Form guarantees clean input.

---

## Rollout checklist

- [ ] Upload `.xlsx` → **Save as Google Sheets**
- [ ] Delete the yellow **EXAMPLE** row in Call Log
- [ ] Add real caller names on the **Lists** tab (column G)
- [ ] Add the conditional-formatting rules (Part 3)
- [ ] Create & link the **Google Form** (Part 4); add it to each phone's home screen
- [ ] **Protect** header row, formula columns (A, E, Q), Lists & Dashboard tabs
- [ ] Share the Sheet with the team (Editor); managers view the **Dashboard**
- [ ] On each phone: Sheets app ▸ **Make available offline**
