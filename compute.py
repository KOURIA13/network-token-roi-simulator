"""
Compute logic for the Network Token ROI Simulator.

Pure functions. No Streamlit, no Plotly, no IO. The compute can be run headless
to sanity-check the model without spinning up the UI :

    python compute.py

… prints the net ROI for the 4 default PSP profiles against the default footprint.
"""

from __future__ import annotations

from schema import (
    MarketResult,
    MarketRow,
    PSPProfile,
    ScenarioResult,
    TokenizationAssumptions,
)

# Named conversions — clearer than magic numbers in the formulas below.
BPS_PER_UNIT = 10_000      # 1 bps = 1 / 10 000
PPT_PER_UNIT = 100         # 1 ppt = 1 / 100
MONTHS_PER_YEAR = 12


def _market_result(
    row: MarketRow,
    psp: PSPProfile,
    a: TokenizationAssumptions,
    passkey_cit_multiplier: float = 1.0,
) -> MarketResult:
    """Annual contribution of a single market under (PSP, assumptions).

    Compute steps :
      1. tokenized_annual = CoF × 12 × issuer_participation × PSP coverage
      2. CIT path  — cryptogram + issuer trust, additive ppt uplift
                     × passkey_cit_multiplier (Nuance 4 — only when PSP supports passkey)
      3. MIT path  — Account Updater (ABU/MDES) recovery ; 0 if PSP doesn't support it.
                     Passkey/silent-verif does NOT apply to MIT (no customer auth in MIT).
      4. Fraud     — baseline chargeback rate × fraud_reduction on tokenized volume
      5. Interchange — bps savings on tokenized volume (Visa : ~10 bps)
      6. Variable cost — per-tx token fee. Integration cost is charged once at
         scenario level (see compute_scenario), NOT per market.
    """
    participation = a.issuer_participation_by_region[row.region]
    tokenized_annual = (
        row.monthly_cof_volume_eur
        * MONTHS_PER_YEAR
        * participation
        * psp.tokenization_coverage_pct
    )

    # CIT path : cryptogramme + confiance issuer, uplift additif en ppt.
    # Décomposition : industry baseline régional + optimization layer du PSP.
    # Le multiplicateur passkey (Nuance 4) ne s'applique que si le PSP le supporte.
    effective_passkey_multiplier = passkey_cit_multiplier if psp.passkey_supported else 1.0
    industry_baseline_ppt = a.cit_uplift_by_region[row.region].mid_ppt
    cit_uplift_ppt = industry_baseline_ppt + psp.optimization_layer_uplift_pp
    cit_uplift_eur = (
        row.cit_share * tokenized_annual * cit_uplift_ppt / PPT_PER_UNIT
        * effective_passkey_multiplier
    )

    # MIT path : Account Updater. Sans ABU/MDES côté PSP → pas de recovery.
    mit_share = 1.0 - row.cit_share
    mit_recovery_rate = (
        a.involuntary_churn_recovery_pct if psp.account_updater_supported else 0.0
    )
    mit_uplift_eur = mit_share * tokenized_annual * mit_recovery_rate

    fraud_savings_eur = (
        tokenized_annual * a.baseline_chargeback_rate * a.fraud_reduction_pct
    )
    interchange_savings_eur = tokenized_annual * (a.interchange_savings_bps / BPS_PER_UNIT)

    variable_cost_eur = tokenized_annual * (psp.token_fee_bps / BPS_PER_UNIT)
    orphan_token_exposure_eur = tokenized_annual * a.orphan_token_dormancy_pct

    return MarketResult(
        region=row.region,
        tokenized_volume_eur=tokenized_annual,
        cit_uplift_eur=cit_uplift_eur,
        mit_uplift_eur=mit_uplift_eur,
        fraud_savings_eur=fraud_savings_eur,
        interchange_savings_eur=interchange_savings_eur,
        variable_cost_eur=variable_cost_eur,
        orphan_token_exposure_eur=orphan_token_exposure_eur,
    )


def compute_scenario(
    footprint: list[MarketRow],
    psp: PSPProfile,
    assumptions: TokenizationAssumptions,
    passkey_cit_multiplier: float = 1.0,
) -> ScenarioResult:
    """Compute the 12-month portfolio ROI of a tokenization rollout.

    Net ROI = sum of (incremental approved + fraud + interchange)
              − variable cost − one-shot integration cost.

    Payback months = integration_cost / monthly_recurring_net,
                     where monthly_recurring_net excludes the integration cost.
                     Returns None when monthly_recurring_net <= 0
                     (the rollout never pays back under these assumptions).

    `passkey_cit_multiplier` (Nuance 4) layers a directional multiplier on top of
    the CIT uplift to model passkey + silent-verification stacking. Applied only
    when `psp.passkey_supported`. Default 1.0 = no effect.
    """
    markets = [
        _market_result(row, psp, assumptions, passkey_cit_multiplier)
        for row in footprint
    ]

    total_tokenized = sum(m.tokenized_volume_eur for m in markets)
    total_incremental = sum(m.cit_uplift_eur + m.mit_uplift_eur for m in markets)
    total_fraud = sum(m.fraud_savings_eur for m in markets)
    total_interchange = sum(m.interchange_savings_eur for m in markets)
    total_variable_cost = sum(m.variable_cost_eur for m in markets)

    # Intégration : coût fixe au niveau PSP, ajouté UNE fois — pas par marché.
    integration_cost = psp.integration_cost_eur

    net_roi = (
        total_incremental + total_fraud + total_interchange
        - total_variable_cost - integration_cost
    )

    monthly_recurring_net = (
        total_incremental + total_fraud + total_interchange - total_variable_cost
    ) / MONTHS_PER_YEAR
    payback = (
        integration_cost / monthly_recurring_net
        if monthly_recurring_net > 0
        else None
    )

    return ScenarioResult(
        psp_name=psp.name,
        markets=markets,
        total_tokenized_volume_eur=total_tokenized,
        total_incremental_approved_eur=total_incremental,
        total_fraud_savings_eur=total_fraud,
        total_interchange_savings_eur=total_interchange,
        total_variable_cost_eur=total_variable_cost,
        integration_cost_eur=integration_cost,
        net_roi_eur=net_roi,
        payback_months=payback,
    )


if __name__ == "__main__":
    # Sanity check headless : tableau récapitulatif pour les 4 PSPs par défaut.
    from calibration import DEFAULT_ASSUMPTIONS, DEFAULT_FOOTPRINT, PSP_PROFILES

    print(f"{'PSP':<14s} | {'Tokenized':>12s} | {'Net ROI':>12s} | {'Payback':>10s}")
    print("-" * 60)
    for psp_name, psp in PSP_PROFILES.items():
        r = compute_scenario(DEFAULT_FOOTPRINT, psp, DEFAULT_ASSUMPTIONS)
        payback = f"{r.payback_months:.1f} mo" if r.payback_months else "Never"
        print(
            f"{psp_name:<14s} | "
            f"EUR {r.total_tokenized_volume_eur / 1e6:>6.1f}M | "
            f"EUR {r.net_roi_eur / 1e6:>6.2f}M | "
            f"{payback:>10s}"
        )
