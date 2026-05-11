# Network Token ROI Simulator

A Python / Streamlit tool to model **network tokenization rollout ROI** for multi-country merchants — calibrated on public 2026 benchmarks (Mastercard × Checkout.com whitepaper, Visa CNP data, Adyen Uplift / Personalize launch).

Built from the **merchant side**, not the PSP side. The goal is to help payment teams turn a vendor pitch ("+10 ppt approval rate") into a defensible 12-month business case they can take to their CFO.

---

## The problem this tool solves

Most network-tokenization business cases circulating inside merchants today suffer from three problems:

1. **They use a single blended uplift number.** A "+10.3 ppt approval rate uplift" headline from the Mastercard × CKO whitepaper conflates four regions, two issuer maturity tiers, and both CIT and MIT flows. A merchant operating in MENA + Europe + NA cannot use that single number to size investment.
2. **They confuse CIT and MIT ROI mechanics.** Customer-initiated transactions (CIT) gain from cryptogram authentication and issuer trust. Merchant-initiated transactions (MIT, e.g. subscriptions) gain from Account Updater (ABU / MDES) eliminating involuntary churn from card updates. These are **two different ROI engines** — modelling them as one underestimates MIT and over-credits CIT.
3. **They ignore lifecycle and governance cost.** Tokens that survive customer churn become orphan tokens — a GDPR / ops liability that no headline number captures.

This simulator forces the user to confront all three problems before producing a number.

---

## What it does

Models **12-month net ROI** of a network token rollout across:

- **Multiple markets**, with explicit regional dispersion of issuer participation rate (Mastercard × CKO terminology).
- **CIT vs MIT mix** modelled as **two distinct ROI paths** — cryptogram-driven authorization uplift on CIT, Account Updater recovery on MIT.
- **PSP comparison** holding the merchant footprint constant — Stripe, Adyen, Checkout.com, and an in-house Token Service Provider (TSP) profile.
- **Sensitivity** to baseline authorization rate, volume distribution, and PSP tokenization coverage.

It also surfaces two things most vendor calculators omit:

- **Orphan-token exposure** after customer churn — a lifecycle / governance KPI.
- **Foundation-stack placeholder** — flagging that tokens unlock passkey + silent verification, with no faked number on the joint uplift (deliberate model boundary).

---

## The 4 nuances the tool makes explicit

These are the design constraints — every panel in the UI maps to one of them.

| # | Nuance | What it changes in the model |
|---|---|---|
| 1 | **Regional dispersion** | Per-region uplift bands (low / mid / high ppt) with issuer participation rate per region — not a single global number |
| 2 | **CIT vs MIT mechanics** | Two separate compute paths : CIT uplift = `cit_share × tokenized_vol × ppt`, MIT uplift = `mit_share × tokenized_vol × ABU recovery rate` (only when the PSP supports Account Updater) |
| 3 | **Orphan tokens after churn** | Surfaced as a € exposure on the dormant share of the token vault — governance KPI, not a saving |
| 4 | **Tokenization as foundation, not roof** | Reserved slot for passkey × silent verification joint uplift — modeled as **Phase 2** until public data isolates the joint effect |

---

## Inputs

Entered via the Streamlit sidebar — fully editable in-app.

| Input | Granularity | Notes |
|---|---|---|
| Monthly card-on-file volume (€) | Per region (EU, MENA, APAC, NA) | Editable table |
| Average ticket (€) | Per region | |
| Baseline authorization rate | Per region | 0-1, used for context, not in compute today |
| CIT share | Per region | `mit_share = 1 - cit_share` |
| PSP scenario | Global | Stripe / Adyen / Checkout.com / In-house TSP |
| Pair with passkey + silent verif | Global | Reserved for v1 — disabled in v0.5 |

PSP profiles encode: `token_fee_bps`, `integration_cost_eur`, `tokenization_coverage_pct`, `account_updater_supported`, `passkey_supported`. **All PSP fees are illustrative — not vendor-quoted.** See [`calibration.py`](calibration.py).

---

## Outputs

| Output | Panel |
|---|---|
| 12-month net ROI (€) | Headline KPI strip |
| Incremental approved volume (€) | Headline KPI strip |
| Fraud / chargeback savings (€) | Headline KPI strip |
| Payback period (months) | Headline KPI strip |
| Authorization uplift dispersion by region (ppt + issuer-band error bars) | Nuance 1 chart |
| CIT vs MIT decomposition of incremental approved volume | Nuance 2 chart |
| Orphan-token exposure (€ + % dormant) | Nuance 3 gauge |
| Foundation-stack roadmap card | Nuance 4 (qualitative) |
| Net ROI side-by-side across PSPs | PSP comparison strip |

---

## Calibration sources & methodology

The model decomposes the CIT authorization uplift into **two separable layers** so each can be sourced independently :

```
total CIT uplift (ppt) = industry_baseline_by_region   +   PSP_optimization_layer
                         ─────────────────────────         ───────────────────────
                         token effect alone                what the PSP's stack adds
                         (issuer-side)                     on top of raw tokenization
```

### Industry baseline by region (token effect, before PSP optimization)

| Region | Low / Mid / High (ppt) | Calibration |
|---|---|---|
| EU | 3.0 / 5.0 / 7.0 | Visa CNP global +4.6 ppt anchor ; CKO whitepaper measures +10.1 ppt on CKO merchants — the delta (~5 ppt) is attributed to the CKO stack, modelled separately. |
| MENA | 6.0 / 8.0 / 10.0 | CKO whitepaper measures +12.4 ppt on CKO merchants ; baseline ~8 ppt reflects UAE tokenization maturity (85% in Q1 2025). |
| APAC | 3.0 / 5.0 / 7.0 | No whitepaper public figure ; estimated from 77.1% YoY token growth (Mastercard × CKO). |
| NA | 2.0 / 4.0 / 6.0 | No whitepaper public figure ; estimated from 56% YoY token growth. |

### PSP optimization layer (uplift added on top of baseline)

| PSP | Optim layer | Extra (ppt) | Source |
|---|---|---|---|
| **Checkout.com** | Authorization Optimization Engine | **+5.0** | Mastercard × CKO whitepaper (April 2026) — CKO merchants measure +10.3 ppt avg vs industry +3-6 ppt → ~5 ppt attributable to CKO stack. ⚠️ **Whitepaper is CKO co-authored — biased by construction.** |
| **Adyen** | Personalize | **+3.5** | Illustrative — triangulated from Adyen Personalize launch (Feb 2026, +1.19% conversion lift mostly auth-attributable). Not Adyen-quoted on auth alone. |
| **Stripe** | Adaptive Acceptance | **+3.0** | Illustrative — anchored between industry baseline and CKO +5. No public Stripe-isolated uplift number. |
| **In-house TSP** | — | **+0.0** | No optimization layer modelled. Retries / routing / 3DS need to be built in-house. |

### Other public benchmarks used in the model

- **Visa** — −26% fraud reduction on tokenized ; ~10 bps lower interchange vs PAN.
- **Adyen Personalize** (Feb 2026) — −9.4% payment costs, −42% false positives.
- **Solidgate** — up to +15% acceptance on tokenized (sanity-check anchor for high-band).
- **Account Updater recovery** — ~7% of declined recurring transactions recovered via ABU/MDES (industry estimate).
- **Baseline CNP chargeback rate** — 0.5% (industry).

All of these are encoded as **named constants** in [`calibration.py`](calibration.py) and as `notes_md` fields on each `PSPProfile`. The simulator surfaces them in the sidebar (PSP-specific expander) and below the PSP comparison strip (full methodology), so a reviewer can argue with any number directly inside the UI.

---

## Architecture

Five small files, ~600 LOC total. Each file has one responsibility — designed so an engineer joining the project can ramp up in 5 minutes.

```
network-token-roi-simulator/
├── app.py             Streamlit UI + orchestration. No math, no chart drawing.
├── schema.py          Data contracts : every input and output dataclass.
├── compute.py         Pure compute logic. Imports schema, no UI dependency.
├── calibration.py     Public benchmarks, PSP profiles, default footprint.
├── viz.py             Plotly chart builders (4 charts).
├── tests/
│   └── test_compute.py  Sanity tests — plain assertions, no pytest needed.
├── requirements.txt
└── README.md
```

**Dependency graph** (one-way, no cycles) :

```
app.py ──► compute.py ──► schema.py
   │           ▲
   │           │
   ▼           │
viz.py     calibration.py ──► schema.py
```

- **`schema.py`** is the contract — open it first to understand the data model.
- **`compute.py`** is the algorithm — pure functions, no IO, runnable headless via `python compute.py`.
- **`calibration.py`** is pure data — change a benchmark, restart, see the effect. No logic.
- **`viz.py`** is presentation — Plotly figures, returned to `app.py` to render.
- **`app.py`** is glue — wires sidebar inputs → `compute_scenario` → `viz` → Streamlit widgets. Never computes.
- **`tests/test_compute.py`** asserts the load-bearing properties of the model (e.g. no-ABU PSP → MIT path is zero ; doubling volume doubles tokenized €).

---

## Run locally

```powershell
# First time
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Each session
streamlit run app.py
```

Opens at [http://localhost:8501](http://localhost:8501).

To smoke-test the compute without Streamlit :

```powershell
python compute.py
```

Expected output : a 4-row table (one per PSP profile) with tokenized volume, net ROI, and payback period.

To run the sanity tests :

```powershell
python tests/test_compute.py
```

Expected output : `5/5 passed`.

---

## Limitations & v1 roadmap

Honest about what this v0.5 does **not** do — flagged so a reviewer doesn't waste time looking for it.

- **PSP fees are illustrative**, not vendor-quoted. v1 would source from RFP responses or vendor SE conversations.
- **Authorization uplift is taken at the regional `mid_ppt` value**. A v1 sensitivity slider would let the user move along the issuer-band low → high range to size the downside case.
- **MIT recovery uses a single ABU recovery rate (~7%)**. v1 would split between scheme-driven recovery (Visa Account Updater, Mastercard ABU) and issuer-driven recovery, and model PSP-specific implementation gaps.
- **Foundation-stack uplift (passkey × token) is not modelled.** Public 2026 data does not isolate the joint effect. The dataclass field `passkey_stack_uplift_pct` is reserved for when it does.
- **No fraud-cost multiplier.** A chargeback is counted as 1× the transaction value avoided ; real cost typically 2-3× when ops, fees and writeoff are included. Conservative on purpose.
- **No FX, no multi-currency.** Everything in EUR.
- **No persistence.** No save / load scenarios, no CSV export. v1 candidate.

---

## About

Built by **Karim Ouriachi** — Senior AI Product Manager, Payments & Risk. 15+ years across payments, POS, and merchant operations in 23 markets.

This simulator is the practical companion to a LinkedIn series on network tokenization economics from the merchant side. For read-only access, reach out on LinkedIn.

---

*v0.5 — May 2026. Calibrated on Mastercard × Checkout.com (Apr 2026), Visa CNP data, Adyen Personalize (Feb 2026), Solidgate.*
