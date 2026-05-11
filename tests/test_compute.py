"""
Sanity tests for compute_scenario.

Plain assertions — no pytest dependency. Run from the project root :

    python tests/test_compute.py

Exit code is 0 if everything passes, 1 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

# tests/ vit un niveau sous la racine du projet : on ajoute la racine au sys.path
# pour que les imports `schema`, `compute`, `calibration` fonctionnent.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calibration import DEFAULT_ASSUMPTIONS, DEFAULT_FOOTPRINT, PSP_PROFILES  # noqa: E402
from compute import compute_scenario                                          # noqa: E402
from schema import MarketRow                                                   # noqa: E402


def test_empty_footprint_yields_zero_volume() -> None:
    """An empty footprint produces no tokenized volume — only the integration cost remains."""
    result = compute_scenario([], PSP_PROFILES["Stripe"], DEFAULT_ASSUMPTIONS)
    assert result.total_tokenized_volume_eur == 0
    assert result.total_incremental_approved_eur == 0
    assert result.net_roi_eur == -PSP_PROFILES["Stripe"].integration_cost_eur


def test_psp_without_account_updater_yields_no_mit_uplift() -> None:
    """In-house TSP has no ABU/MDES → MIT path must contribute zero per market."""
    in_house = PSP_PROFILES["In-house TSP"]
    assert in_house.account_updater_supported is False
    result = compute_scenario(DEFAULT_FOOTPRINT, in_house, DEFAULT_ASSUMPTIONS)
    assert all(m.mit_uplift_eur == 0 for m in result.markets)


def test_incremental_totals_match_per_market_sum() -> None:
    """The portfolio aggregate equals the sum of per-market CIT + MIT."""
    result = compute_scenario(DEFAULT_FOOTPRINT, PSP_PROFILES["Adyen"], DEFAULT_ASSUMPTIONS)
    per_market = sum(m.cit_uplift_eur + m.mit_uplift_eur for m in result.markets)
    assert abs(per_market - result.total_incremental_approved_eur) < 1e-6


def test_doubling_volume_doubles_tokenized_eur() -> None:
    """tokenized_volume is linear in monthly_cof_volume_eur."""
    base = compute_scenario(DEFAULT_FOOTPRINT, PSP_PROFILES["Stripe"], DEFAULT_ASSUMPTIONS)
    doubled = [
        MarketRow(
            region=r.region,
            monthly_cof_volume_eur=r.monthly_cof_volume_eur * 2,
            avg_ticket_eur=r.avg_ticket_eur,
            baseline_auth_rate=r.baseline_auth_rate,
            cit_share=r.cit_share,
        )
        for r in DEFAULT_FOOTPRINT
    ]
    doubled_result = compute_scenario(doubled, PSP_PROFILES["Stripe"], DEFAULT_ASSUMPTIONS)
    assert abs(doubled_result.total_tokenized_volume_eur - 2 * base.total_tokenized_volume_eur) < 1


def test_a_better_psp_yields_higher_net_roi_than_in_house() -> None:
    """Stripe (full coverage + ABU) beats in-house TSP on the same footprint.

    This guards the narrative shown in the PSP comparison strip.
    """
    stripe = compute_scenario(DEFAULT_FOOTPRINT, PSP_PROFILES["Stripe"], DEFAULT_ASSUMPTIONS)
    in_house = compute_scenario(DEFAULT_FOOTPRINT, PSP_PROFILES["In-house TSP"], DEFAULT_ASSUMPTIONS)
    assert stripe.net_roi_eur > in_house.net_roi_eur


def test_optimization_layer_adds_ppt_only_to_cit() -> None:
    """A PSP's optimization_layer_uplift_pp adds linearly to the CIT path, not to MIT.

    Compares Stripe (optim +3.0 ppt) vs In-house TSP (optim 0 ppt) on a passkey-disabled
    scenario so only the optimization layer differentiates the two on the CIT path.
    """
    stripe = compute_scenario(
        DEFAULT_FOOTPRINT, PSP_PROFILES["Stripe"], DEFAULT_ASSUMPTIONS,
        passkey_cit_multiplier=1.0,
    )
    in_house = compute_scenario(
        DEFAULT_FOOTPRINT, PSP_PROFILES["In-house TSP"], DEFAULT_ASSUMPTIONS,
        passkey_cit_multiplier=1.0,
    )
    # Stripe CIT uplift should be strictly higher than in-house at equal tokenized volume.
    # (Coverage differs, so we can't compare absolute numbers — but at equal coverage the
    # extra ppt would directly increase CIT. We assert directionality here.)
    stripe_cit_per_eur = (
        sum(m.cit_uplift_eur for m in stripe.markets)
        / sum(m.tokenized_volume_eur for m in stripe.markets)
    )
    in_house_cit_per_eur = (
        sum(m.cit_uplift_eur for m in in_house.markets)
        / sum(m.tokenized_volume_eur for m in in_house.markets)
    )
    assert stripe_cit_per_eur > in_house_cit_per_eur, (
        "Stripe optimization layer (+3.0 ppt) must yield higher CIT density than in-house (+0 ppt)."
    )


def test_passkey_multiplier_lifts_cit_only_when_psp_supports_it() -> None:
    """Nuance 4 — the multiplier scales CIT uplift on passkey-capable PSPs, no-op otherwise."""
    # Stripe supports passkey → multiplier should multiply CIT exactly.
    stripe_base = compute_scenario(
        DEFAULT_FOOTPRINT, PSP_PROFILES["Stripe"], DEFAULT_ASSUMPTIONS,
        passkey_cit_multiplier=1.0,
    )
    stripe_lifted = compute_scenario(
        DEFAULT_FOOTPRINT, PSP_PROFILES["Stripe"], DEFAULT_ASSUMPTIONS,
        passkey_cit_multiplier=1.5,
    )
    base_cit = sum(m.cit_uplift_eur for m in stripe_base.markets)
    lifted_cit = sum(m.cit_uplift_eur for m in stripe_lifted.markets)
    assert abs(lifted_cit - 1.5 * base_cit) < 1e-3, (
        f"Stripe (passkey-capable) : 1.5× should lift CIT by 1.5×. Got {lifted_cit / base_cit:.3f}×."
    )

    # MIT should be untouched — passkey acts on customer auth only.
    base_mit = sum(m.mit_uplift_eur for m in stripe_base.markets)
    lifted_mit = sum(m.mit_uplift_eur for m in stripe_lifted.markets)
    assert abs(lifted_mit - base_mit) < 1e-6, "Passkey multiplier must not touch MIT."

    # In-house TSP does NOT support passkey → multiplier must be a no-op.
    in_house_base = compute_scenario(
        DEFAULT_FOOTPRINT, PSP_PROFILES["In-house TSP"], DEFAULT_ASSUMPTIONS,
        passkey_cit_multiplier=1.0,
    )
    in_house_lifted = compute_scenario(
        DEFAULT_FOOTPRINT, PSP_PROFILES["In-house TSP"], DEFAULT_ASSUMPTIONS,
        passkey_cit_multiplier=1.5,
    )
    assert (
        abs(in_house_lifted.net_roi_eur - in_house_base.net_roi_eur) < 1e-6
    ), "In-house TSP doesn't support passkey → multiplier must have zero effect."


def _run_test(fn) -> bool:
    try:
        fn()
        print(f"  PASS  {fn.__name__}")
        return True
    except AssertionError as e:
        print(f"  FAIL  {fn.__name__}: {e or '(no message)'}")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"  ERROR {fn.__name__}: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    print("Running compute sanity tests...\n")
    tests = [
        test_empty_footprint_yields_zero_volume,
        test_psp_without_account_updater_yields_no_mit_uplift,
        test_incremental_totals_match_per_market_sum,
        test_doubling_volume_doubles_tokenized_eur,
        test_a_better_psp_yields_higher_net_roi_than_in_house,
        test_optimization_layer_adds_ppt_only_to_cit,
        test_passkey_multiplier_lifts_cit_only_when_psp_supports_it,
    ]
    passed = sum(_run_test(t) for t in tests)
    total = len(tests)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
