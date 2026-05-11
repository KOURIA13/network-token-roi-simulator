"""
Data contracts for the simulator.

This file defines every input and output of compute_scenario. Read this first
to understand what the simulator consumes and produces — the logic lives in
compute.py, but the *shape* of the model lives here.

All dataclasses are frozen : the simulator is stateless and side-effect free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Region granularity for v0.5. Going to per-country in v1 would only require
# widening this Literal and the corresponding calibration tables.
Region = Literal["EU", "MENA", "APAC", "NA"]


# ── Inputs ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MarketRow:
    """A single row of the merchant footprint (one per region in v0.5)."""

    region: Region
    monthly_cof_volume_eur: float
    avg_ticket_eur: float
    baseline_auth_rate: float  # 0-1
    cit_share: float           # 0-1 ; mit_share = 1 - cit_share


@dataclass(frozen=True)
class PSPProfile:
    """A PSP's tokenization capability set, cost structure, and optimization layer.

    All cost fields are illustrative — not vendor-quoted. See calibration.py for sources.

    The `optimization_layer_uplift_pp` is the ppt added on top of the regional
    industry baseline (cit_uplift_by_region) — it captures what the PSP's
    optimization stack (e.g. Adyen Personalize, Stripe Adaptive Acceptance,
    CKO Authorization Optimization) brings beyond raw network tokenization.
    """

    name: str
    token_fee_bps: float
    integration_cost_eur: float
    tokenization_coverage_pct: float    # 0-1 : part of eligible CoF the PSP can tokenize
    account_updater_supported: bool     # ABU (Mastercard) / scheme Account Updater (Visa)
    passkey_supported: bool
    optimization_layer_name: str | None = None       # e.g. "Adyen Personalize", or None
    optimization_layer_uplift_pp: float = 0.0        # additive ppt on top of regional baseline
    notes_md: str = ""                                # multi-line markdown : sources + caveats


@dataclass(frozen=True)
class UpliftBand:
    """Low / mid / high values for a regional authorization uplift, in ppt.

    `mid_ppt` is the published reference value (Mastercard × CKO whitepaper) ;
    `low_ppt` and `high_ppt` model the dispersion across issuer participation tiers.
    """

    low_ppt: float
    mid_ppt: float
    high_ppt: float


@dataclass(frozen=True)
class TokenizationAssumptions:
    """Public benchmark values consumed by the compute, plus reserved v1 fields."""

    cit_uplift_by_region: dict[Region, UpliftBand]
    issuer_participation_by_region: dict[Region, float]  # 0-1, CKO whitepaper term
    fraud_reduction_pct: float                            # 0-1
    interchange_savings_bps: float
    orphan_token_dormancy_pct: float                      # 0-1
    involuntary_churn_recovery_pct: float                 # 0-1, MIT path via ABU/MDES
    baseline_chargeback_rate: float                       # 0-1

    # Reserved for v1 — Nuance 4 ("foundation, not roof").
    # Deliberately None in v0.5 : no clean public data isolates passkey × token uplift.
    passkey_stack_uplift_pct: float | None = None


# ── Outputs ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MarketResult:
    """Per-market output of compute_scenario. All € values are annual."""

    region: Region
    tokenized_volume_eur: float
    cit_uplift_eur: float
    mit_uplift_eur: float
    fraud_savings_eur: float
    interchange_savings_eur: float
    variable_cost_eur: float            # fee bps × tokenized volume (integration excluded)
    orphan_token_exposure_eur: float


@dataclass(frozen=True)
class ScenarioResult:
    """Portfolio-level output : per-market detail + aggregates + payback."""

    psp_name: str
    markets: list[MarketResult]

    # Aggregates (annual, €)
    total_tokenized_volume_eur: float
    total_incremental_approved_eur: float   # CIT + MIT
    total_fraud_savings_eur: float
    total_interchange_savings_eur: float
    total_variable_cost_eur: float
    integration_cost_eur: float
    net_roi_eur: float

    # None if the monthly recurring net is <= 0 (i.e. rollout never pays back).
    payback_months: float | None
