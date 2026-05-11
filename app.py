"""
Network Token ROI Simulator — Streamlit UI.

Run: streamlit run app.py
"""

import pandas as pd
import streamlit as st

from calibration import (
    DEFAULT_ASSUMPTIONS,
    DEFAULT_FOOTPRINT,
    PSP_PROFILES,
)
from compute import compute_scenario
from schema import (
    MarketResult,
    MarketRow,
    PSPProfile,
    ScenarioResult,
    TokenizationAssumptions,
)
from viz import (
    cit_mit_decomposition_chart,
    orphan_token_gauge,
    psp_comparison_chart,
    regional_dispersion_chart,
)


def _best_region_by_roi_density(result: ScenarioResult) -> MarketResult | None:
    """Region with the highest € of upside per € of tokenized volume.

    Used by the headline-finding narrative to point the reader at the
    most-profitable market on their footprint.
    """
    def density(m: MarketResult) -> float:
        if m.tokenized_volume_eur == 0:
            return 0.0
        upside = (
            m.cit_uplift_eur + m.mit_uplift_eur
            + m.fraud_savings_eur + m.interchange_savings_eur
        )
        return upside / m.tokenized_volume_eur

    return max(result.markets, key=density) if result.markets else None


def _format_payback(months: float | None) -> str:
    if months is None:
        return "never"
    if months < 1:
        return "less than a month"
    if months > 24:
        return "more than 24 months"
    return f"{months:.1f} months"


def _nuance1_caption(
    result: ScenarioResult,
    assumptions: TokenizationAssumptions,
) -> str:
    """Punchy reading of the regional dispersion chart, using this scenario's numbers."""
    if not result.markets:
        return "No markets defined — add a footprint row above."
    if len(result.markets) < 2:
        return "Add a second region to surface the dispersion effect."

    regions = [m.region for m in result.markets]
    ppts = {r: assumptions.cit_uplift_by_region[r].mid_ppt for r in regions}
    best_region = max(ppts, key=lambda r: ppts[r])
    worst_region = min(ppts, key=lambda r: ppts[r])
    ratio = ppts[best_region] / ppts[worst_region] if ppts[worst_region] > 0 else 1.0
    ratio_str = f"a {ratio:.1f}× difference" if ratio >= 1.2 else "a meaningful gap"

    return (
        f"**Reading →** On the **industry baseline** (token effect alone, before PSP optimization), "
        f"**{best_region} delivers +{ppts[best_region]:.1f} ppt vs {worst_region}'s "
        f"+{ppts[worst_region]:.1f} ppt** — {ratio_str}. Blended industry headlines "
        f"(+3-6 ppt Visa CNP global, +10.3 ppt CKO-measured in their whitepaper) hide this "
        f"issuer-side dispersion. The error bars show the issuer-participation band *within* "
        f"each region — your real ROI depends on which issuer tier your traffic actually routes to. "
        f"The PSP-side optimization layer is shown separately below."
    )


def _nuance2_caption(
    footprint: list[MarketRow],
    result: ScenarioResult,
    psp: PSPProfile,
    assumptions: TokenizationAssumptions,
) -> str:
    """Reading of the CIT/MIT decomposition, with a counterfactual when ABU is missing."""
    cit_total = sum(m.cit_uplift_eur for m in result.markets)
    mit_total = sum(m.mit_uplift_eur for m in result.markets)
    total_uplift = cit_total + mit_total

    if not psp.account_updater_supported:
        # Counterfactual : what the MIT path would unlock if ABU were supported.
        forfeited_mit = sum(
            (1.0 - row.cit_share)
            * m.tokenized_volume_eur
            * assumptions.involuntary_churn_recovery_pct
            for row, m in zip(footprint, result.markets)
        )
        return (
            f"**Reading →** **{psp.name} does not support Account Updater (ABU/MDES)** — "
            f"the entire MIT recovery path is forfeited. With an ABU-capable PSP, this same "
            f"footprint would unlock an additional **€{forfeited_mit / 1_000_000:.2f}M/year** "
            f"in recovered recurring revenue. On a subscription-heavy merchant, this gap dominates "
            f"the PSP decision before pricing is even considered."
        )

    if total_uplift == 0:
        return "**Reading →** No uplift on this footprint — check issuer participation and PSP coverage."

    cit_pct = cit_total / total_uplift * 100
    mit_pct = mit_total / total_uplift * 100
    return (
        f"**Reading →** **{cit_pct:.0f}% of the uplift comes from CIT** "
        f"(cryptogram authentication on customer-initiated payments — the path the whitepaper "
        f"headlines) and **{mit_pct:.0f}% from MIT** (recurring billing recoveries via "
        f"Account Updater). A subscription-heavy merchant would skew further toward MIT — that's "
        f"where ABU/MDES pays off the most. The two paths have different ROI mechanics and need "
        f"to be sized separately, not folded into a single uplift number."
    )


def _nuance3_caption(
    result: ScenarioResult,
    assumptions: TokenizationAssumptions,
) -> str:
    total_exposure = sum(m.orphan_token_exposure_eur for m in result.markets)
    pct = assumptions.orphan_token_dormancy_pct * 100
    return (
        f"**Reading →** On your tokenized volume, **€{total_exposure / 1_000_000:.1f}M is exposed "
        f"to dormant tokens** (~{pct:.0f}% dormant >12 months). This isn't a € loss today — it's "
        f"a liability your legal / compliance team will surface when GDPR auditors ask how you "
        f"manage scheme tokens after customer churn. Most merchants skip lifecycle hygiene "
        f"(provisioning, suspension, deletion) until it becomes an audit finding. Treating it as "
        f"a Day-1 governance KPI is cheaper than reverse-engineering it post-incident."
    )


def _psp_strip_caption(results_by_psp: dict[str, ScenarioResult]) -> str:
    if len(results_by_psp) < 2:
        return ""
    items = list(results_by_psp.items())
    best_name, best_res = max(items, key=lambda kv: kv[1].net_roi_eur)
    worst_name, worst_res = min(items, key=lambda kv: kv[1].net_roi_eur)
    delta = best_res.net_roi_eur - worst_res.net_roi_eur
    return (
        f"**Reading →** On this footprint, **{best_name} wins by "
        f"€{delta / 1_000_000:.1f}M over {worst_name}** in 12-month net ROI. "
        f"The spread comes from two structural drivers : "
        f"**(a) the optimization layer** (CKO +5 ppt sourced from the Mastercard × CKO whitepaper ; "
        f"Adyen +3.5 ppt and Stripe +3.0 ppt illustrative ; in-house +0 by construction), and "
        f"**(b) Account Updater + coverage gaps** (in-house TSP forfeits the MIT path entirely "
        f"and tokenizes ~70% of eligible CoF vs ~95% on major PSPs). PSP fees are illustrative — "
        f"the structural drivers dominate the spread, not the bps. See the methodology expander below "
        f"for sources."
    )


def _build_headline_narrative(
    footprint: list[MarketRow],
    result: ScenarioResult,
    psp_name: str,
    assumptions: TokenizationAssumptions,
) -> str:
    """One-paragraph business conclusion shown above the KPI strip.

    Recomputed every render — reflects the current sidebar inputs.
    """
    if not footprint:
        return "No markets defined — add a footprint row to see the headline finding."

    total_annual_cof = sum(r.monthly_cof_volume_eur for r in footprint) * 12
    best = _best_region_by_roi_density(result)
    payback_str = _format_payback(result.payback_months)

    if best is None:
        return "No tokenizable volume — check issuer participation and PSP coverage."

    selected_psp = PSP_PROFILES[psp_name]
    baseline_ppt = assumptions.cit_uplift_by_region[best.region].mid_ppt
    optim_ppt = selected_psp.optimization_layer_uplift_pp
    total_ppt = baseline_ppt + optim_ppt
    best_participation = assumptions.issuer_participation_by_region[best.region] * 100

    optim_label = selected_psp.optimization_layer_name or "no optimization layer"
    return (
        f"On a **€{total_annual_cof / 1_000_000:.0f}M/year card-on-file footprint**, "
        f"a network token rollout with **{psp_name}** delivers "
        f"**€{result.net_roi_eur / 1_000_000:.1f}M net ROI over 12 months** "
        f"(payback {payback_str}). "
        f"**{best.region}** is the highest-ROI region : "
        f"**+{total_ppt:.1f} ppt total CIT uplift** "
        f"(+{baseline_ppt:.1f} industry baseline + {optim_ppt:.1f} from *{optim_label}*) "
        f"× {best_participation:.0f}% issuer participation. "
        f"Of the upside, **€{result.total_incremental_approved_eur / 1_000_000:.1f}M comes from "
        f"authorization uplift** (CIT cryptogram + MIT Account Updater)."
    )


st.set_page_config(
    page_title="Network Token ROI Simulator",
    page_icon="🔐",
    layout="wide",
)

st.title("🔐 Network Token ROI Simulator")
st.caption(
    "12-month net ROI of network tokenization rollout — calibrated on "
    "Mastercard × Checkout.com (Apr 2026), Visa CNP data, Adyen Personalize. "
    "Built from the merchant side."
)


# ── Sidebar : inputs ───────────────────────────────────────────────────────
with st.sidebar:
    st.header("Merchant footprint")

    default_df = pd.DataFrame([
        {
            "Region": r.region,
            "Monthly CoF (€)": r.monthly_cof_volume_eur,
            "Avg ticket (€)": r.avg_ticket_eur,
            "Baseline auth": r.baseline_auth_rate,
            "CIT share": r.cit_share,
        }
        for r in DEFAULT_FOOTPRINT
    ])
    edited_df = st.data_editor(
        default_df,
        hide_index=True,
        column_config={
            "Region": st.column_config.TextColumn(disabled=True),
            "Monthly CoF (€)": st.column_config.NumberColumn(format="%d", min_value=0),
            "Avg ticket (€)": st.column_config.NumberColumn(format="%d", min_value=1),
            "Baseline auth": st.column_config.NumberColumn(format="%.2f", min_value=0.0, max_value=1.0),
            "CIT share": st.column_config.NumberColumn(format="%.2f", min_value=0.0, max_value=1.0),
        },
        num_rows="fixed",
    )

    st.divider()
    st.header("PSP scenario")
    psp_choice = st.selectbox("PSP", list(PSP_PROFILES.keys()), index=0)
    selected_psp = PSP_PROFILES[psp_choice]
    optim_label = (
        f"{selected_psp.optimization_layer_name} (+{selected_psp.optimization_layer_uplift_pp:.1f} ppt)"
        if selected_psp.optimization_layer_name
        else "None (+0 ppt)"
    )
    st.caption(
        f"Network token fee: {selected_psp.token_fee_bps:.1f} bps · "
        f"Integration: €{selected_psp.integration_cost_eur:,.0f} · "
        f"Account Updater: {'✅' if selected_psp.account_updater_supported else '❌'} · "
        f"Passkey: {'✅' if selected_psp.passkey_supported else '❌'} · "
        f"Optimization layer: {optim_label}"
    )
    with st.expander(f"📋 Sources & notes — {psp_choice}", expanded=False):
        st.markdown(selected_psp.notes_md)

    st.divider()
    st.header("Foundation stack (Nuance 4)")
    passkey_enabled = st.toggle(
        "Pair with passkey + silent verification",
        value=False,
        help=(
            "Layers a directional multiplier on top of the CIT uplift to model "
            "passkey + silent-verification stacking. No public 2026 data isolates "
            "the joint uplift — treat this as a sensitivity dial, not a forecast. "
            "Applied only when the selected PSP supports passkey."
        ),
    )
    if passkey_enabled:
        passkey_multiplier = st.slider(
            "Directional multiplier on CIT uplift",
            min_value=1.00, max_value=1.50, value=1.20, step=0.05,
            format="%.2f×",
            help=(
                "1.00× = no effect. Anchor : Adyen Personalize cites +1.19% conversion "
                "lift on top of optimized payments, partially attributable to passkey. "
                "Range deliberately capped at 1.50× — beyond that becomes speculation."
            ),
        )
        if not selected_psp.passkey_supported:
            st.caption(
                f"⚠️ **{psp_choice}** is set as not supporting passkey in this model — "
                "the multiplier is shown but won't apply. Switch to Stripe or Adyen to see the effect."
            )
    else:
        passkey_multiplier = 1.0

    st.divider()
    st.caption(
        "ℹ️ PSP fees and integration costs are **illustrative** — not vendor-quoted. "
        "See README for calibration sources."
    )


# ── Construire le footprint depuis l'édition ───────────────────────────────
footprint = [
    MarketRow(
        region=row["Region"],
        monthly_cof_volume_eur=float(row["Monthly CoF (€)"]),
        avg_ticket_eur=float(row["Avg ticket (€)"]),
        baseline_auth_rate=float(row["Baseline auth"]),
        cit_share=float(row["CIT share"]),
    )
    for _, row in edited_df.iterrows()
]

result = compute_scenario(
    footprint, selected_psp, DEFAULT_ASSUMPTIONS,
    passkey_cit_multiplier=passkey_multiplier,
)


# ── Block A : Headline finding + KPIs ──────────────────────────────────────
st.subheader(f"12-month projection — {psp_choice}")

st.success(
    "**Headline finding** — "
    + _build_headline_narrative(footprint, result, psp_choice, DEFAULT_ASSUMPTIONS),
    icon="🎯",
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Net 12-mo ROI", f"€{result.net_roi_eur/1_000_000:.2f}M")
k2.metric("Incremental approved volume", f"€{result.total_incremental_approved_eur/1_000_000:.2f}M")
k3.metric("Fraud savings", f"€{result.total_fraud_savings_eur/1_000_000:.2f}M")

if result.payback_months is None:
    payback_display = "Never"
elif result.payback_months > 24:
    payback_display = ">24 mo"
elif result.payback_months < 1:
    payback_display = "<1 mo"
else:
    payback_display = f"{result.payback_months:.1f} mo"
k4.metric("Payback", payback_display)


# ── Block B : Nuance 1 — regional dispersion ───────────────────────────────
st.divider()
st.subheader("Nuance 1 — Regional dispersion of issuer participation")
st.markdown(_nuance1_caption(result, DEFAULT_ASSUMPTIONS))
st.plotly_chart(
    regional_dispersion_chart(result, DEFAULT_ASSUMPTIONS),
    use_container_width=True,
)


# ── Block C : Nuance 2 — CIT vs MIT ────────────────────────────────────────
st.divider()
st.subheader("Nuance 2 — CIT vs MIT mechanics")
st.markdown(_nuance2_caption(footprint, result, selected_psp, DEFAULT_ASSUMPTIONS))
st.plotly_chart(
    cit_mit_decomposition_chart(result),
    use_container_width=True,
)


# ── Block D : Nuances 3 & 4 ─────────────────────────────────────────────────
st.divider()
col_d1, col_d2 = st.columns(2)

with col_d1:
    st.subheader("Nuance 3 — Orphan tokens & lifecycle")
    st.markdown(_nuance3_caption(result, DEFAULT_ASSUMPTIONS))
    st.plotly_chart(
        orphan_token_gauge(result, DEFAULT_ASSUMPTIONS),
        use_container_width=True,
    )

with col_d2:
    st.subheader("Nuance 4 — Foundation, not roof")
    if passkey_enabled and selected_psp.passkey_supported:
        st.markdown(
            f"**Reading →** With **{passkey_multiplier:.2f}× directional multiplier** applied "
            f"on the CIT uplift (passkey + silent verification stacked on top of network tokens), "
            f"net ROI for **{psp_choice}** is **€{result.net_roi_eur / 1_000_000:.2f}M** "
            f"(vs base scenario without passkey).\n\n"
            f"This multiplier is a **sensitivity dial**, not a forecast — neither "
            f"**Adyen Personalize** nor **Stripe Adaptive Acceptance** publicly isolates the "
            f"passkey × token joint uplift, so any number here is directional by construction. "
            f"Treat it the way you'd treat a CFO downside/upside sensitivity, not a vendor quote."
        )
    elif passkey_enabled and not selected_psp.passkey_supported:
        st.markdown(
            f"**Reading →** The **{passkey_multiplier:.2f}× multiplier** is toggled on but "
            f"**{psp_choice}** is modelled as not supporting passkey — the multiplier doesn't apply.\n\n"
            "Switch the PSP to **Stripe** or **Adyen** in the sidebar to see the passkey × token "
            "stacking effect on this same footprint. The lesson : passkey support is a "
            "**PSP selection criterion**, not just a roadmap nice-to-have."
        )
    else:
        st.markdown(
            """
            **Reading →** Tokenization is the foundation. The next-layer uplift comes from
            **passkeys**, **silent verification**, and **device-bound card-on-file**.

            Both **Adyen Personalize** (Feb 2026) and **Stripe Adaptive Acceptance** layer
            optimizations on top of network tokens — but **neither publicly isolates the
            passkey × token joint uplift**.

            → Toggle **"Pair with passkey + silent verification"** in the sidebar to apply a
            directional multiplier (1.00×–1.50×) on the CIT uplift and size the upside case.
            """
        )
        st.info(
            "The multiplier is a sensitivity dial, not a forecast — by design.",
            icon="🎯",
        )


# ── Bottom strip : PSP comparison ──────────────────────────────────────────
st.divider()
st.subheader("PSP comparison — same merchant footprint")
results_by_psp = {
    name: compute_scenario(
        footprint, profile, DEFAULT_ASSUMPTIONS,
        passkey_cit_multiplier=passkey_multiplier,
    )
    for name, profile in PSP_PROFILES.items()
}
st.markdown(_psp_strip_caption(results_by_psp))
st.plotly_chart(
    psp_comparison_chart(results_by_psp),
    use_container_width=True,
)

with st.expander("📐 Methodology — why the spread looks like this", expanded=False):
    st.markdown(
        "The PSP comparison strip is the most contestable panel in this tool. Here is exactly "
        "where each number comes from, so you can argue with it.\n\n"
        "### What's the same across PSPs\n"
        "- **Industry baseline CIT uplift per region** (EU +5, MENA +8, APAC +5, NA +4 ppt) — "
        "the token effect itself, before any PSP-side optimization. Calibration source : "
        "triangulated between Visa CNP global (+4.6 ppt) and the Mastercard × CKO whitepaper "
        "(which measures +10.3 ppt on CKO merchants — that includes the CKO stack, modelled "
        "separately).\n"
        "- **Fraud reduction** (−26%, Visa), **interchange savings** (~10 bps, Visa), "
        "**ABU recovery rate** (~7%, industry).\n\n"
        "### What differs across PSPs — and what's the source\n"
    )
    for psp_name, psp in PSP_PROFILES.items():
        st.markdown(f"#### {psp_name}")
        st.markdown(psp.notes_md)
    st.markdown(
        "### Why the spread between major PSPs is narrower than the headline suggests\n"
        "On vendor-publicly-attested data alone, **Stripe, Adyen and Checkout.com are within "
        "~2 ppt of each other** on the optimization layer. The real differentiation between "
        "major PSPs in production is usually **non-financial** : geographic match (CKO strong in "
        "MENA, Adyen strong in EU enterprise, Stripe strong on US + EU SMB), roadmap fit "
        "(passkey maturity, scheme coverage), and contract terms (volume discounts, MDR). "
        "**This tool sizes the financial floor — the picking criterion sits above it.**"
    )


# ── Footer ──────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Built by Karim Ouriachi — Senior AI PM, Payments & Risk. v0.5 — May 2026. "
    "Calibration: Mastercard × CKO (Apr 2026), Visa CNP data, Adyen Personalize (Feb 2026), Solidgate."
)
