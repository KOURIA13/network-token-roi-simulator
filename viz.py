"""
Plotly chart builders. Toutes les figures sont retournées telles quelles ;
app.py les passe à st.plotly_chart.
"""

from __future__ import annotations

import plotly.graph_objects as go

from schema import ScenarioResult, TokenizationAssumptions


def regional_dispersion_chart(
    result: ScenarioResult,
    assumptions: TokenizationAssumptions,
) -> go.Figure:
    """Nuance 1 : uplift CIT par région + error bars de la dispersion issuer-band."""
    regions = [m.region for m in result.markets]
    mids = [assumptions.cit_uplift_by_region[r].mid_ppt for r in regions]
    lows = [assumptions.cit_uplift_by_region[r].low_ppt for r in regions]
    highs = [assumptions.cit_uplift_by_region[r].high_ppt for r in regions]

    err_minus = [mid - low for mid, low in zip(mids, lows)]
    err_plus = [high - mid for high, mid in zip(highs, mids)]

    fig = go.Figure(
        data=go.Bar(
            x=regions,
            y=mids,
            error_y=dict(
                type="data", symmetric=False,
                array=err_plus, arrayminus=err_minus,
                thickness=2, width=10,
            ),
            marker_color="#1f77b4",
            text=[f"+{m:.1f} ppt" for m in mids],
            textposition="outside",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Mid: +%{y:.1f} ppt<br>"
                "Range: low/high issuer band<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Industry baseline CIT uplift by region (ppt) — before PSP optimization layer",
        yaxis_title="Authorization uplift (ppt)",
        xaxis_title=None,
        showlegend=False,
        height=380,
        margin=dict(t=60, b=40, l=40, r=20),
    )
    return fig


def cit_mit_decomposition_chart(result: ScenarioResult) -> go.Figure:
    """Nuance 2 : stacked bar CIT vs MIT par région."""
    regions = [m.region for m in result.markets]
    cit = [m.cit_uplift_eur for m in result.markets]
    mit = [m.mit_uplift_eur for m in result.markets]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=regions, y=cit,
        name="CIT — cryptogram + issuer trust",
        marker_color="#1f77b4",
        hovertemplate="<b>%{x}</b><br>CIT: €%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=regions, y=mit,
        name="MIT — Account Updater recovery",
        marker_color="#ff7f0e",
        hovertemplate="<b>%{x}</b><br>MIT: €%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        barmode="stack",
        title="Where the incremental approved volume comes from (€/year)",
        yaxis_title="Incremental approved volume (€)",
        xaxis_title=None,
        height=380,
        margin=dict(t=60, b=80, l=40, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.28),
    )
    return fig


def orphan_token_gauge(
    result: ScenarioResult,
    assumptions: TokenizationAssumptions,
) -> go.Figure:
    """Nuance 3 : gouvernance — % de tokens dormants > 12 mois + exposition €."""
    total_exposure = sum(m.orphan_token_exposure_eur for m in result.markets)
    pct = assumptions.orphan_token_dormancy_pct * 100

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number={"suffix": " %"},
        title={
            "text": (
                "Tokens dormant > 12 mo<br>"
                "<span style='font-size:0.75em;color:#888'>GDPR / ops liability</span>"
            )
        },
        gauge={
            "axis": {"range": [0, 30]},
            "bar": {"color": "#d62728"},
            "steps": [
                {"range": [0, 10], "color": "#d4edda"},
                {"range": [10, 20], "color": "#fff3cd"},
                {"range": [20, 30], "color": "#f8d7da"},
            ],
        },
    ))
    fig.add_annotation(
        text=f"Exposure: €{total_exposure/1_000_000:.1f}M of token volume orphaned",
        showarrow=False,
        x=0.5, y=-0.05, xref="paper", yref="paper",
        font=dict(size=12, color="#555"),
    )
    fig.update_layout(height=320, margin=dict(t=60, b=40, l=20, r=20))
    return fig


def psp_comparison_chart(results_by_psp: dict[str, ScenarioResult]) -> go.Figure:
    """Bottom strip : net 12-mo ROI side-by-side, footprint constant."""
    psps = list(results_by_psp.keys())
    net_rois = [r.net_roi_eur for r in results_by_psp.values()]

    fig = go.Figure(go.Bar(
        x=psps,
        y=net_rois,
        marker_color=["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd"],
        text=[f"€{v/1_000_000:.2f}M" for v in net_rois],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Net ROI: €%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title="12-month net ROI by PSP — same merchant footprint",
        yaxis_title="Net ROI (€)",
        xaxis_title=None,
        height=380,
        showlegend=False,
        margin=dict(t=60, b=40, l=40, r=20),
    )
    return fig
