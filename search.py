import json
import os
import time
from generator import generate_system
from formatter import format_system

# ── Search criteria ──────────────────────────────────────────────────────────
# Add, remove, or set criteria here before running.
# Any key set to None is ignored — only active (non-None) keys are evaluated.
# See evaluate_system() below for full documentation of each criterion.

CRITERIA = {
    # ── Life ────────────────────────────────────────────────────────────────
    "min_habitable_bodies":  1,        # int   — minimum total life-bearing bodies (planets + moons)
    "min_biosphere_score":   None,     # float — minimum biosphere score on any single body
    "biochemistry_type":     None,     # str   — required biochemistry e.g. "Chemolithotrophic", "Water/Carbon"
    "habitable_moons":       None,     # bool  — True = at least one habitable moon required

    # ── Giants ──────────────────────────────────────────────────────────────
    "has_giant":             None,     # bool  — True = system must contain at least one giant
    "min_giant_count":       None,     # int   — minimum number of giants
    "giant_subclass":        None,     # str   — "gas_giant" or "ice_giant" — at least one of this subclass
    "giant_has_moons":       None,     # bool  — True = at least one giant must have stable moons

    # ── Rings ───────────────────────────────────────────────────────────────
    "has_rings":             None,     # bool  — True = at least one body must have rings

    # ── Star ────────────────────────────────────────────────────────────────
    "star_class":            None,     # str   — e.g. "G", "M", "F" — exact spectral class match
    "min_metallicity":       None,     # float — minimum star metallicity (FeH)
    "max_metallicity":       None,     # float — maximum star metallicity (FeH)

    # ── Bodies ──────────────────────────────────────────────────────────────
    "min_body_count":        None,     # int   — minimum total main orbital bodies
    "has_super_earth":       None,     # bool  — True = at least one super_earth subclass body
    "goldilocks_inhabited":  None,     # bool  — True = at least one habitable body inside Goldilocks zone
}

# ── Search configuration ──────────────────────────────────────────────────────
KEYS_FILE        = "search_keys.txt"   # One key per line
OUTPUT_FOLDER    = "Search Results"
SEARCH_NAME      = "habitable_systems" # Subfolder name for this search run
PRINT_NO_MATCH   = False               # Set True to print every key, not just matches

# ─────────────────────────────────────────────────────────────────────────────

def load_keys(filepath):
    """Load keys from a text file, one per line. Strips whitespace, skips blanks and # comments."""
    with open(filepath, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

# Biosphere tiers that constitute actual life — prebiotic and lifeless are excluded
LIFE_TIERS = {"microbial", "simple_multicellular", "complex_multicellular", "advanced"}

def collect_habitable(system):
    """Returns list of dicts for all genuinely life-bearing bodies.
    Excludes lifeless and prebiotic — a non-zero score alone is not sufficient,
    the body must reach at least the microbial tier."""
    results = []
    for body in system["bodies"]:
        score   = body["habitability"].get("Biosphere_Score", {}).get("value")
        tier    = body["habitability"].get("Biosphere_Tier", {}).get("value", "lifeless")
        biochem = body["habitability"].get("Biochemistry_Type", {}).get("value", "None")
        gold    = body["orbit"].get("In_Goldilocks", {}).get("value", False)
        if score and score > 0 and tier in LIFE_TIERS:
            results.append({
                "name": body["name"], "score": score, "tier": tier,
                "biochem": biochem, "body_type": "planet", "in_goldilocks": gold
            })
        for moon in body.get("moons", []):
            m_score  = moon["habitability"].get("Biosphere_Score", {}).get("value")
            m_tier   = moon["habitability"].get("Biosphere_Tier", {}).get("value", "lifeless")
            m_biochem = moon["habitability"].get("Biochemistry_Type", {}).get("value", "None")
            if m_score and m_score > 0 and m_tier in LIFE_TIERS:
                results.append({
                    "name": moon["name"], "score": m_score, "tier": m_tier,
                    "biochem": m_biochem, "body_type": "moon", "in_goldilocks": False
                })
    return results

def evaluate_system(system, criteria):
    """Evaluates a generated system against the active criteria.
    Returns (match: bool, reason: str).

    CRITERIA REFERENCE:
    ─────────────────────────────────────────────────────────────────────
    min_habitable_bodies  int   Minimum count of life-bearing bodies (planets + moons combined)
    min_biosphere_score   float At least one body must meet or exceed this biosphere score
    biochemistry_type     str   At least one habitable body must match this biochemistry label
                                e.g. "Water/Carbon", "Chemolithotrophic", "Ammonia/Carbon"
    habitable_moons       bool  If True, at least one moon must be life-bearing

    has_giant             bool  If True, system must have at least one giant body
    min_giant_count       int   System must have at least this many giants
    giant_subclass        str   At least one giant must match "gas_giant" or "ice_giant"
    giant_has_moons       bool  If True, at least one giant must have >= 1 stable moon

    has_rings             bool  If True, at least one body must have rings present

    star_class            str   Star spectral class must match exactly e.g. "G", "M", "F"
    min_metallicity       float Star metallicity (FeH) must be >= this value
    max_metallicity       float Star metallicity (FeH) must be <= this value

    min_body_count        int   System must have at least this many main orbital bodies
    has_super_earth       bool  If True, at least one body must have subclass "super_earth"
    goldilocks_inhabited  bool  If True, at least one habitable body must be in the Goldilocks zone
    ─────────────────────────────────────────────────────────────────────
    """

    star    = system["star"]
    bodies  = system["bodies"]
    giants  = [b for b in bodies if b["type"] == "giant"]
    hab     = collect_habitable(system)

    def active(key):
        return criteria.get(key) is not None

    # ── Life criteria ────────────────────────────────────────────────────────
    if active("min_habitable_bodies"):
        if len(hab) < criteria["min_habitable_bodies"]:
            return False, f"habitable bodies {len(hab)} < {criteria['min_habitable_bodies']}"

    if active("min_biosphere_score"):
        best = max((h["score"] for h in hab), default=0)
        if best < criteria["min_biosphere_score"]:
            return False, f"best score {best:.4f} < {criteria['min_biosphere_score']}"

    if active("biochemistry_type"):
        target = criteria["biochemistry_type"].lower()
        if not any(target in h["biochem"].lower() for h in hab):
            return False, f"no body with biochemistry '{criteria['biochemistry_type']}'"

    if active("habitable_moons"):
        moon_hab = [h for h in hab if h["body_type"] == "moon"]
        if criteria["habitable_moons"] and not moon_hab:
            return False, "no habitable moons"

    # ── Giant criteria ───────────────────────────────────────────────────────
    if active("has_giant"):
        if criteria["has_giant"] and not giants:
            return False, "no giants in system"

    if active("min_giant_count"):
        if len(giants) < criteria["min_giant_count"]:
            return False, f"giant count {len(giants)} < {criteria['min_giant_count']}"

    if active("giant_subclass"):
        target = criteria["giant_subclass"]
        if not any(g.get("subclass") == target for g in giants):
            return False, f"no giant with subclass '{target}'"

    if active("giant_has_moons"):
        if criteria["giant_has_moons"]:
            if not any(len(g.get("moons", [])) > 0 for g in giants):
                return False, "no giant has stable moons"

    # ── Ring criteria ────────────────────────────────────────────────────────
    if active("has_rings"):
        if criteria["has_rings"]:
            if not any(b.get("rings", {}).get("present") for b in bodies):
                return False, "no rings in system"

    # ── Star criteria ────────────────────────────────────────────────────────
    if active("star_class"):
        if star["class"] != criteria["star_class"]:
            return False, f"star class '{star['class']}' != '{criteria['star_class']}'"

    if active("min_metallicity"):
        if star["Star_Metallicity"] < criteria["min_metallicity"]:
            return False, f"metallicity {star['Star_Metallicity']} < {criteria['min_metallicity']}"

    if active("max_metallicity"):
        if star["Star_Metallicity"] > criteria["max_metallicity"]:
            return False, f"metallicity {star['Star_Metallicity']} > {criteria['max_metallicity']}"

    # ── Body criteria ────────────────────────────────────────────────────────
    if active("min_body_count"):
        if len(bodies) < criteria["min_body_count"]:
            return False, f"body count {len(bodies)} < {criteria['min_body_count']}"

    if active("has_super_earth"):
        if criteria["has_super_earth"]:
            if not any(b.get("subclass") == "super_earth" for b in bodies):
                return False, "no super_earth in system"

    if active("goldilocks_inhabited"):
        if criteria["goldilocks_inhabited"]:
            gold_hab = [h for h in hab if h.get("in_goldilocks")]
            if not gold_hab:
                return False, "no habitable body inside Goldilocks zone"

    # All active criteria passed
    best_score = max((h["score"] for h in hab), default=0)
    return True, f"{len(hab)} habitable body/bodies, best score {best_score:.4f}"

def format_match_summary(hab):
    """Returns a compact summary string of habitable bodies for console output."""
    parts = []
    for h in sorted(hab, key=lambda x: x["score"], reverse=True):
        tag = "moon" if h["body_type"] == "moon" else "planet"
        parts.append(f"{h['name']} [{tag}] {h['tier']} {h['score']:.4f} ({h['biochem']})")
    return "  |  ".join(parts)

def run_search(keys, criteria, output_folder, search_name, print_no_match=False):
    """Main search loop. Runs each key through the pipeline and saves matches."""
    save_dir = os.path.join(output_folder, search_name)
    os.makedirs(save_dir, exist_ok=True)

    total   = len(keys)
    matches = 0
    errors  = 0
    t_start = time.time()

    print(f"\n{'=' * 64}")
    print(f"  ASTRA Search — '{search_name}'")
    print(f"  Keys to process: {total}")
    active_criteria = {k: v for k, v in criteria.items() if v is not None}
    print(f"  Active criteria: {len(active_criteria)}")
    for k, v in active_criteria.items():
        print(f"    {k}: {v}")
    print(f"{'=' * 64}\n")

    for i, key in enumerate(keys, 1):
        try:
            system    = generate_system(key)
            formatted = format_system(system)
            match, reason = evaluate_system(system, criteria)

            if match:
                matches += 1
                hab = collect_habitable(system)
                summary = format_match_summary(hab)
                print(f"[{i:>{len(str(total))}}/{total}] {key:<20} MATCH  — {reason}")
                print(f"         {summary}")

                # Save matched system JSON
                filename = os.path.join(save_dir, system["star"]["name"] + ".json")
                with open(filename, "w") as f:
                    json.dump(formatted, f, indent=4)

            elif print_no_match:
                print(f"[{i:>{len(str(total))}}/{total}] {key:<20} no match — {reason}")

        except Exception as e:
            errors += 1
            print(f"[{i:>{len(str(total))}}/{total}] {key:<20} ERROR — {e}")

    elapsed = time.time() - t_start
    print(f"\n{'=' * 64}")
    print(f"  Search complete.")
    print(f"  Keys processed: {total}  |  Matches: {matches}  |  Errors: {errors}")
    print(f"  Time elapsed:   {elapsed:.1f}s  ({elapsed/total:.2f}s per key)")
    print(f"  Results saved:  {save_dir}")
    print(f"{'=' * 64}\n")

if __name__ == "__main__":
    import sys

    # Allow key file override from command line: python search.py my_keys.txt
    keys_file = sys.argv[1] if len(sys.argv) > 1 else KEYS_FILE

    if not os.path.exists(keys_file):
        print(f"Key file not found: '{keys_file}'")
        print("Create a text file with one key per line and set KEYS_FILE at the top of search.py")
        sys.exit(1)

    keys = load_keys(keys_file)
    if not keys:
        print(f"No keys found in '{keys_file}'.")
        sys.exit(1)

    run_search(keys, CRITERIA, OUTPUT_FOLDER, SEARCH_NAME, PRINT_NO_MATCH)
