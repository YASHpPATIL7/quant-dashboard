# Dashboard Changelog — quant-dashboard

**Latest:** 2026-06-29
Companion to `alpha-core/CODE_AUDIT_LOG.md` (the data/model changes the dashboard
now reflects).

---

## Root cause that started all this

The live dashboard showed a **−2.46% CVaR that never moved** and a **BULL**
regime that was wrong. The dashboard JS was correct — it was reading CSVs from
GitHub `main` that were **frozen in the past**: `vajra_returns.csv` ended
2019-11-29 (so the 95% CVaR computed to −2.46% forever) and `regime_labels.csv`
ended 2022-08-25 labelled "Bull". Fix = regenerate + push fresh `alpha-core`
data; the dashboard cache-busts each load so it self-corrects.

---

## 2026-06-28 — Overview-first tabbed restructure + mobile

**Why:** reviewer feedback — too much on one page, US (Alpaca) live strategy sat
next to the Indian risk engine, not mobile-friendly, "reads like a fancy project".

**What changed (all in `index.html`, single file, all element IDs preserved):**
- Added a sticky **5-tab nav**: Overview · Risk · Signals · Allocation · Live Trading.
- A small load-time script **relocates each existing `.card`** into its tab
  section (whole panels moved, no inner markup/IDs changed) and removes the empty
  zone/row wrappers. Tab switching toggles section visibility + nudges chart resize.
- **Mobile**: media query stacks panels full-width and shrinks canvases.
- **Honest framing** on the Live tab: a banner noting NSE signals are executed via
  US sector-ETF proxies (XLF/XLE/XLV) because Alpaca is US-only — "validates the
  execution pipeline, not the Indian strategy's return."
- CVaR + regime pill live in the always-visible top bar (risk shown on every tab).

**Tab → panels:** Overview = live market, regime+trade log, morning signal ·
Risk = correlation, GARCH vol, report card · Signals = GatiShakti/FinBERT,
cointegration · Allocation = Black-Litterman, backtest, frontier, alpha scores,
tilts, strategy comparison · Live = Alpaca live, alpha-vs-SPY decay.

---

## 2026-06-29 — Regime probabilities display

- Top-bar pill now shows the regime **with confidence** (e.g. "SIDEWAYS 100%")
  from the new `regime_confidence` column.
- Overview regime panel shows the **current state-probability breakdown**
  ("Now: Bear x% · Sideways y% · Bull z%") from `prob_bull/sideways/bear`,
  falling back to the old day-count summary if those columns are absent.

---

## 2026-06-29 — Cointegration panel: factor-neutral + honest empty state

- Subtitle corrected: "Johansen · factor-neutral (FF5 residuals) · same-sector only"
  (was mislabelled "Engle-Granger").
- Each row shows the **economic mechanism**, a **FACTOR-NEUTRAL ✓** marker, and
  the raw-vs-residual trace stat.
- **Empty state**: when nothing is tradeable, the panel says so honestly and then
  renders the **monitored watchlist** (`cointegration_watchlist.csv`) — same-sector
  near-misses tagged "MONITORED", so the panel tells the methodology story instead
  of going blank.

**Backward compatible:** all new reads degrade gracefully on the older CSVs.

---

## 2026-06-29 — CVaR rolling window + two-strategy Live tab + Risk declutter

**CVaR was not stuck — it was correct but static.** −2.46% is the true 95% CVaR
of the *full* 2019→2026 equal-weight series (the 2019-only slice gives −1.60%, so
it was reading fresh data). An all-history figure barely moves. Switched to a
**trailing 252-day (1-year) window = −1.66%**, which reflects current risk and
updates over time. Label now reads "CVaR · 95% · 1d · 1y window".

**Live Trading tab — separated two genuinely distinct live Alpaca strategies**
(they were conflated; the card showed Strategy-1 data with Strategy-2's label and
a hardcoded XLV position):
- **[01] SPY · SMA 20/50 Momentum** — `live-trading-alpha/alpaca_journal.csv`.
  Trades SPY outright on a 10/30 SMA crossover, gated by a 20/50 regime filter;
  benchmark = SPY buy-and-hold. The position card is now populated with the
  **real** last-row SPY position (side/qty/last/P&L), not the fake XLV demo.
  Removed the block that overwrote it with Strategy-2 data.
- **[01b] Alpha-Core · NSE→ETF** — `alpha-core/data/alpaca_order_book.csv`.
  The project's Indian XGB/Kelly engine mapped to US-ETF proxies. Currently
  **FLAT** (all signals neutral, 0% deployed) — shown honestly as the signal scan
  with a "engine is flat, not missing data" note.
- Live-tab header rewritten to describe the two separate books.

**Risk tab declutter** — widened to max 2 columns (min 560px), single column below
1100px, so the three dense panels aren't crammed.

**Known stale data (needs pipeline re-run, not a dashboard fix):** the FinBERT
news feed ends 2026-05-20 — re-run `finbert_sentiment.py` for fresh headlines.

## Build / deploy

```bash
python3 inject_snapshot.py   # pre-renders latest NAV / date / regime / IC into index.html
git add -A && git commit -m "..." && git push origin main   # GitHub Action redeploys
```
Verify locally first: open `index.html`, click every tab, shrink to phone width.
