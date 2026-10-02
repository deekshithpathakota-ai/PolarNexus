"""Curated demonstration responses used ONLY when no LLM is configured (or the LLM call fails).

They are clearly labelled 'Demo response' in the API and UI. Each [n] marker is bound to a real
section of a real repository document, so every citation opens an actual passage.
"""
import re

CURATED_ANSWERS = [
    dict(
        doc="antarctic-sea-ice-variability-study",
        scope="any",
        patterns=[r"key factors", r"factors .*(influenc|control|drive|affect)", r"what (influences|controls|drives) .*sea.?ice",
                  r"why does antarctic sea.?ice (vary|change)"],
        sources=[("antarctic-sea-ice-variability-study", "Key Findings"),
                 ("antarctic-sea-ice-variability-study", "Data and Methods"),
                 ("antarctic-sea-ice-variability-study", "Limitations"),
                 ("southern-ocean-oceanographic-observations", "Key Findings")],
        answer=(
            "The study identifies **four interacting factors** behind year-to-year differences in Antarctic sea ice in the "
            "Prydz Bay sector:\n\n"
            "1. **Wind patterns** — persistent offshore winds push the ice edge northward and open coastal polynyas where "
            "new ice forms, while onshore winds compress the pack against the coast [1].\n"
            "2. **Ocean heat below the ice** — when warmer subsurface water is mixed upward, autumn freeze-up is delayed "
            "and the ice season is shorter [1]. Ship-based CTD observations describe this warmer deep water beneath the "
            "cold Winter Water layer [4].\n"
            "3. **Timing of autumn freeze-up** — a late start tends to be followed by thinner, less extensive ice in the "
            "following months [1].\n"
            "4. **Large-scale atmospheric variability** such as the Southern Annular Mode, which modulates regional "
            "winds and explains some, but not all, of the differences [1].\n\n"
            "These conclusions combine satellite sea-ice concentration records with ship observations from Antarctic "
            "Expedition 43 [2]. The authors caution that the relationships are associations for one sector and a "
            "limited number of years, and should not be generalised to all of Antarctica [3]."
        ),
    ),
    dict(
        doc="antarctic-sea-ice-variability-study",
        scope="document",
        patterns=[r"student", r"simple", r"explain (it|this) (to|for)", r"like i'?m", r"kid", r"school"],
        sources=[("antarctic-sea-ice-variability-study", "Background"),
                 ("antarctic-sea-ice-variability-study", "Key Findings"),
                 ("antarctic-sea-ice-variability-study", "Implications and Outreach Relevance")],
        answer=(
            "**In simple terms:** every year the sea around Antarctica freezes in winter and melts back in summer [1]. "
            "This ice is important because its bright surface reflects sunlight and it is home to tiny algae, krill "
            "and penguins [1].\n\n"
            "Scientists in this study wanted to know why there is more ice in some years and less in others. They found "
            "that it depends on several things working together [2]:\n\n"
            "- **Wind** can push the ice out to sea or pile it up against the coast.\n"
            "- **Warm water underneath** can slow down freezing in autumn.\n"
            "- **When freezing starts** matters — a late start usually means less ice later.\n\n"
            "The big lesson: no single cause controls Antarctic sea ice, which is why it can change a lot from one year "
            "to the next [3]."
        ),
    ),
]


def match_curated(question: str, doc_slug: str | None) -> dict | None:
    q = question.lower()
    for entry in CURATED_ANSWERS:
        if entry["scope"] == "document" and doc_slug != entry["doc"]:
            continue
        if entry["scope"] == "any" and doc_slug not in (None, entry["doc"]):
            continue
        if entry["scope"] == "any" and doc_slug is None and "sea" not in q:
            continue
        if any(re.search(p, q) for p in entry["patterns"]):
            return entry
    return None
