# Network Token ROI Simulator

A Python/Streamlit tool to model network tokenization rollout ROI for multi-country merchants, calibrated on public 2026 benchmarks (Mastercard × Checkout.com whitepaper, Visa data, Adyen Uplift).

## What it does

Models the 12-month net ROI of network token rollout across:
- Multiple markets (with regional dispersion of issuer enablement)
- CIT vs MIT transaction mix
- Comparison across PSPs (Stripe, Adyen, Checkout.com, in-house TSP)
- Sensitivity to baseline authorization rate and volume distribution

The goal: help merchant-side payment teams build a realistic business case, not just plug a headline number into a spreadsheet.

## Inputs

- Monthly card-on-file transaction volume (by country)
- Country mix (% volume per market)
- CIT / MIT split (one-shot vs recurring)
- Baseline authorization rate
- PSP option to benchmark

## Outputs

- 12-month net ROI by PSP scenario
- Sensitivity analysis on issuer enablement gap
- Approval rate uplift breakdown (CIT vs MIT)
- Fraud chargeback reduction estimate

## Calibration sources

- Mastercard × Checkout.com whitepaper "Network tokenization: powering the e-commerce of today and tomorrow" (April 2026)
- Visa tokenized CNP authorization data
- Adyen Uplift / Personalize 2026 launch data

## Status

🚧 Work in progress — iterating based on feedback from payments PMs across PSPs and merchant orgs.

Built by Karim Ouriachi — Senior AI Product Manager, Payments & Risk.

For read-only access, reach out on LinkedIn.
