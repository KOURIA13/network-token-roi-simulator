"""
Benchmarks publics 2026 utilisés pour seeder le modèle.

Sources :
- Mastercard × Checkout.com whitepaper (avril 2026)
- Visa CNP tokenized authorization data
- Adyen Uplift / Personalize (lancement fév 2026)
- Solidgate (acceptance rate sur tokenized)

Les valeurs PSP-fees sont ILLUSTRATIVES — pas de quote vendor publique.
"""

from schema import (
    MarketRow,
    PSPProfile,
    TokenizationAssumptions,
    UpliftBand,
)


# Industry baseline CIT uplift PAR RÉGION — uplift attendu de la tokenization SEULE,
# avant la couche optimization du PSP (Personalize / Adaptive Acceptance / Auth Optim).
#
# Méthodologie :
# - EU : Visa publie +4.6 ppt CNP global. CKO whitepaper mesure +10.1 ppt sur ses
#        merchants EU → la différence (~5 ppt) est attribuée au stack CKO et capturée
#        séparément dans PSP_PROFILES["Checkout.com"].optimization_layer_uplift_pp.
# - MENA : whitepaper mesure +12.4 ppt sur CKO merchants ; baseline industrie estimée
#          ~8 ppt (UAE Q1 2025 tokenization déjà mature, donc floor plus haut qu'EU).
# - APAC, NA : pas de chiffre whitepaper public ; estimés à partir des trajectoires YoY.
# low/high encadrent la dispersion issuer-band attendue dans chaque région.
CIT_UPLIFT_BY_REGION: dict[str, UpliftBand] = {
    "EU":   UpliftBand(low_ppt=3.0, mid_ppt=5.0, high_ppt=7.0),
    "MENA": UpliftBand(low_ppt=6.0, mid_ppt=8.0, high_ppt=10.0),
    "APAC": UpliftBand(low_ppt=3.0, mid_ppt=5.0, high_ppt=7.0),
    "NA":   UpliftBand(low_ppt=2.0, mid_ppt=4.0, high_ppt=6.0),
}

# Issuer participation rate (terme du whitepaper Mastercard × CKO) :
# part des transactions CoF routables vers un network token côté issuer.
# EU : trajectoire ~78% (CKO Europe 59% tokenized, croissance 77.5% YoY).
# MENA : 85% (chiffre UAE Q1 2025, Mastercard).
# APAC / NA : estimations — pas de chiffre direct dans le whitepaper.
ISSUER_PARTICIPATION_BY_REGION: dict[str, float] = {
    "EU":   0.78,
    "MENA": 0.85,
    "APAC": 0.60,
    "NA":   0.70,
}


DEFAULT_ASSUMPTIONS = TokenizationAssumptions(
    cit_uplift_by_region=CIT_UPLIFT_BY_REGION,
    issuer_participation_by_region=ISSUER_PARTICIPATION_BY_REGION,
    fraud_reduction_pct=0.26,             # Visa : -26% fraude sur tokenized
    interchange_savings_bps=10.0,         # Visa : ~10 bps inférieur vs PAN
    orphan_token_dormancy_pct=0.15,       # Illustratif — pas de chiffre public clean
    involuntary_churn_recovery_pct=0.07,  # ABU/MDES recouvre ~6-8% du décliné récurrent
    baseline_chargeback_rate=0.005,       # 0.5% CNP card-on-file (industrie)
    passkey_stack_uplift_pct=None,        # Réservé v1 — nuance 4
)


# Profils PSP avec sources et caveats explicites.
# Coûts et bps : TOUS ILLUSTRATIFS — pas de quote vendor publique.
# optimization_layer_uplift_pp : ppt additif sur le baseline industrie.
#   - CKO : +5 ppt sourcé du whitepaper (whitepaper-attested, biais CKO assumé)
#   - Adyen / Stripe : illustratifs, triangulés
#   - In-house : 0 (pas de couche optimization)
PSP_PROFILES: dict[str, PSPProfile] = {
    "Stripe": PSPProfile(
        name="Stripe",
        token_fee_bps=2.0,
        integration_cost_eur=15_000,
        tokenization_coverage_pct=0.95,
        account_updater_supported=True,
        passkey_supported=True,
        optimization_layer_name="Adaptive Acceptance",
        optimization_layer_uplift_pp=3.0,
        notes_md=(
            "- **Network tokens** : GA via Stripe Optimized Checkout. "
            "Source: Stripe public docs.\n"
            "- **Optimization layer — *Adaptive Acceptance*** : ML-based retries + routing. "
            "No public attribution to the token layer specifically.\n"
            "- **Account Updater** : supported via Card Updater "
            "(Visa Account Updater + Mastercard ABU).\n"
            "- **Passkey** : via Apple Pay / Google Pay token flow.\n"
            "- **Pricing** : standard CNP 1.5% + €0.25. Network token fee not publicly "
            "itemized — the **2.0 bps** in this model is **illustrative**.\n"
            "- **Optimization uplift +3.0 ppt** : **illustrative**, anchored between "
            "industry baseline and CKO-attested +5 ppt. No public Stripe-isolated uplift."
        ),
    ),
    "Adyen": PSPProfile(
        name="Adyen",
        token_fee_bps=1.5,
        integration_cost_eur=20_000,
        tokenization_coverage_pct=0.95,
        account_updater_supported=True,
        passkey_supported=True,
        optimization_layer_name="Personalize",
        optimization_layer_uplift_pp=3.5,
        notes_md=(
            "- **Network tokens** : GA. Source: Adyen docs.\n"
            "- **Optimization layer — *Personalize*** (Feb 2026 launch) : "
            "−9.4% payment costs, +1.19% conversion lift, −42% false positives. "
            "Source: Adyen Personalize launch announcement, Feb 2026.\n"
            "- **Account Updater** : supported.\n"
            "- **Passkey** : via Adyen Authentication (3DS2 + delegated authentication).\n"
            "- **Pricing** : interchange++ + processing fee. Network token fee not publicly "
            "itemized — the **1.5 bps** in this model is **illustrative**.\n"
            "- **Optimization uplift +3.5 ppt** : **illustrative**, triangulated from "
            "Personalize +1.19% conversion lift (mostly auth-attributable). "
            "Not Adyen-quoted on auth uplift alone."
        ),
    ),
    "Checkout.com": PSPProfile(
        name="Checkout.com",
        token_fee_bps=2.5,
        integration_cost_eur=18_000,
        tokenization_coverage_pct=0.95,
        account_updater_supported=True,
        passkey_supported=False,
        optimization_layer_name="Authorization Optimization",
        optimization_layer_uplift_pp=5.0,
        notes_md=(
            "- **Network tokens** : GA via Vault & Secure Storage. Source: CKO docs.\n"
            "- **Optimization layer — *Authorization Optimization Engine*** : "
            "Issuer Optimization + intelligent retries. Documented in the Mastercard × "
            "Checkout.com whitepaper *\"Network tokenization: powering the e-commerce of "
            "today and tomorrow\"* (April 2026).\n"
            "- **Account Updater** : supported.\n"
            "- **Passkey** : less mature than Adyen Authentication; modelled as "
            "**not supported** in v0.5. Open to revision if a CKO PM corrects this.\n"
            "- **Pricing** : interchange++ + processing fee. The **2.5 bps** is "
            "**illustrative**.\n"
            "- **Optimization uplift +5.0 ppt** : **sourced from the Mastercard × CKO "
            "whitepaper (April 2026)** — CKO merchants measured at +10.3 ppt avg vs "
            "industry +3-6 ppt → ~5 ppt attributable to the CKO stack. "
            "⚠️ **Caveat** : whitepaper is CKO co-authored — biased by construction."
        ),
    ),
    "In-house TSP": PSPProfile(
        name="In-house TSP",
        token_fee_bps=0.5,
        integration_cost_eur=120_000,
        tokenization_coverage_pct=0.70,
        account_updater_supported=False,
        passkey_supported=False,
        optimization_layer_name=None,
        optimization_layer_uplift_pp=0.0,
        notes_md=(
            "- **Network tokens** : direct integration with Visa Token Service (VTS) "
            "and Mastercard Digital Enablement Service (MDES). Source: Visa VTS docs "
            "and Mastercard MDES docs.\n"
            "- **No optimization layer** : retries, routing, smart 3DS need to be built "
            "in-house. Modelled as **+0 ppt** extra on top of baseline.\n"
            "- **No Account Updater** : ABU/MDES Account Updater is a separate lifecycle "
            "project, typically deferred in early in-house builds.\n"
            "- **No passkey integration**.\n"
            "- **Coverage 70%** : only Mastercard/Visa direct — no local schemes "
            "(Bancontact, iDEAL, JCB...) without additional integrations.\n"
            "- **Cost structure** : zero per-tx markup (pass-through MDES/VTS) but "
            "**€120K illustrative integration cost** (6-12 month project, multi-FTE)."
        ),
    ),
}


# Footprint marchand par défaut — marchand mid-market e-commerce multi-pays.
# Ordres de grandeur volontairement réalistes pour qu'un PM payments y reconnaisse
# un profil de merchant qu'il connaît (300M€/an de CoF total, ticket moyen ~65€).
DEFAULT_FOOTPRINT: list[MarketRow] = [
    MarketRow(
        region="EU",
        monthly_cof_volume_eur=12_000_000,
        avg_ticket_eur=65,
        baseline_auth_rate=0.85,
        cit_share=0.70,
    ),
    MarketRow(
        region="MENA",
        monthly_cof_volume_eur=2_500_000,
        avg_ticket_eur=80,
        baseline_auth_rate=0.78,
        cit_share=0.80,
    ),
    MarketRow(
        region="APAC",
        monthly_cof_volume_eur=4_000_000,
        avg_ticket_eur=55,
        baseline_auth_rate=0.83,
        cit_share=0.75,
    ),
    MarketRow(
        region="NA",
        monthly_cof_volume_eur=6_500_000,
        avg_ticket_eur=70,
        baseline_auth_rate=0.88,
        cit_share=0.65,
    ),
]
