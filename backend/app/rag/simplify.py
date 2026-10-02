"""Rule-based plain-language helpers used when no LLM is configured.
They only substitute wording; they never add new factual claims."""
import re

GLOSSARY: list[tuple[str, str, str]] = [
    # (pattern, replacement, glossary definition)
    (r"sea-ice concentration", "the share of the ocean surface covered by ice", "Sea-ice concentration: how much of an area of ocean is covered by ice."),
    (r"passive-microwave", "satellite microwave", "Passive microwave: satellite sensors that detect natural microwave signals and can 'see' ice through clouds and darkness."),
    (r"Southern Annular Mode", "Southern Annular Mode (a pattern of westerly winds circling Antarctica)", "Southern Annular Mode: a large-scale pattern of westerly winds around Antarctica that shifts north and south."),
    (r"\bpolynyas\b", "polynyas (areas of open water surrounded by ice)", "Polynya: an area of open water surrounded by sea ice."),
    (r"\bmixed layer\b", "well-mixed top layer of the ocean", "Mixed layer: the top layer of the ocean that is stirred by wind and waves."),
    (r"CTD profiles", "measurements of ocean temperature and saltiness at different depths (CTD profiles)", "CTD: an instrument measuring Conductivity (saltiness), Temperature and Depth."),
    (r"composite analysis", "comparison of groups of similar years", ""),
    (r"\banomalies\b", "unusual departures from normal", ""),
    (r"\bvariability\b", "variation", ""),
    (r"\bmarginal ice zone\b", "marginal ice zone (the broken-up edge of the pack ice)", "Marginal ice zone: the area at the edge of the pack where ice is broken into floes."),
    (r"\bfreeze-up\b", "freeze-up (when the sea starts to freeze)", ""),
    (r"\balbedo\b", "albedo (how much sunlight a surface reflects)", "Albedo: the fraction of sunlight a surface reflects. Ice has a high albedo."),
    (r"\bpCO2\b", "carbon dioxide level in surface water (pCO2)", "pCO2: the partial pressure of carbon dioxide, a measure of how much CO2 is dissolved in water."),
    (r"\bkatabatic\b", "katabatic (downhill, gravity-driven)", "Katabatic wind: cold, dense air flowing downhill off an ice sheet."),
    (r"\bmass balance\b", "mass balance (snow gained minus ice lost)", "Mass balance: the difference between what a glacier gains and loses."),
    (r"\bmetamorphic\b", "metamorphic (transformed by heat and pressure)", ""),
    (r"\bionosphere\b", "ionosphere (an electrically charged layer of the upper atmosphere)", "Ionosphere: the electrically charged part of the upper atmosphere."),
    (r"\bcyanobacteria\b", "cyanobacteria (tiny organisms that make energy from sunlight)", "Cyanobacteria: microorganisms that photosynthesise, like plants."),
    (r"\baerosols?\b", "aerosols (tiny particles in the air)", "Aerosols: tiny solid or liquid particles suspended in air."),
]


def simplify(sentence: str, used_terms: set[str] | None = None) -> str:
    out = sentence
    for pat, rep, _ in GLOSSARY:
        if used_terms is not None and pat in used_terms:
            # only expand a term the first time it appears
            short = re.sub(r"\s*\(.*\)$", "", rep)
            out = re.sub(pat, short if short else rep, out, flags=re.IGNORECASE)
            continue
        if re.search(pat, out, flags=re.IGNORECASE):
            out = re.sub(pat, rep, out, count=1, flags=re.IGNORECASE)
            if used_terms is not None:
                used_terms.add(pat)
    out = re.sub(r"^(First|Second|Third|Fourth|Fifth),\s*", "", out)
    return out[0].upper() + out[1:] if out else out


def glossary_for(text: str, limit: int = 4) -> list[str]:
    found = []
    for pat, _, definition in GLOSSARY:
        if definition and re.search(pat, text, flags=re.IGNORECASE):
            found.append(definition)
    return found[:limit]
