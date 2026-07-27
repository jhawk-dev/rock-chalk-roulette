import json, re

full = json.load(open("full_roster_candidates.json", encoding="utf-8"))
curated_decades = json.load(open("era_data_decades_backup.json", encoding="utf-8"))

# The stats book only tags players G/F/C. Curated entries were researched with the
# finer PG/SG/SF/PF/C granularity -- collapse those down to match (roster is 2 Guards,
# 2 Forwards, 1 Center; no need to fabricate a PG/SG or SF/PF split we don't have data for).
POS_COLLAPSE = {"PG": "G", "SG": "G", "SF": "F", "PF": "F", "C": "C"}

def collapse_pos_eligible(posEligible):
    collapsed = []
    for p in posEligible:
        c = POS_COLLAPSE.get(p, p)
        if c not in collapsed:
            collapsed.append(c)
    return collapsed

curated_lookup = {}
curated_list = []
for e in curated_decades:
    for c in e["candidates"]:
        entry = dict(c)
        entry["posEligible"] = collapse_pos_eligible(c["posEligible"])
        entry["pos"] = "/".join(entry["posEligible"])
        curated_list.append(entry)
        curated_lookup[(c["name"], c["season"])] = entry

NAME_ALIASES = {
    ("JoJo White", "1968–69"): ("Jo Jo White", "1968–69"),
    ("Rodger Bohnenstiehl", "1967–68"): ("Roger Bohnenstiehl", "1967–68"),
    ("Rick Suttle", "1972–73"): ("Richard Suttle", "1972–73"),
    ("Ken Koenigs", "1977–78"): ("Kenneth Koenigs", "1977–78"),
    ("Wayne Selden", "2014–15"): ("Wayne Selden Jr.", "2014–15"),
    ("Svi Mykhailiuk", "2017–18"): ("Sviatoslav Mykhailiuk", "2017–18"),
}
for curated_key, full_key in NAME_ALIASES.items():
    if curated_key in curated_lookup:
        curated_lookup[full_key] = curated_lookup[curated_key]

def strip_suffix(name):
    return re.sub(r"\s+(Jr\.?|Sr\.?|II|III|IV|V)$", "", name).strip()

# secondary lookup ignoring suffixes, in case of Jr./III mismatches between sources
curated_lookup_nosuffix = {}
for k, v in curated_lookup.items():
    name, season = k
    curated_lookup_nosuffix.setdefault((strip_suffix(name), season), v)

matched_names = set()
final_candidates = []

for c in full:
    key = (c["name"], c["season"])
    curated = curated_lookup.get(key) or curated_lookup_nosuffix.get((strip_suffix(c["name"]), c["season"]))

    pos_eligible = curated["posEligible"] if curated else c["posEligible"]

    cand = {
        "name": c["name"],
        "season": c["season"],
        "pos": "/".join(pos_eligible),
        "posEligible": pos_eligible,
    }
    for stat in ("ppg", "rpg", "apg", "spg", "bpg", "fg", "tp", "ft"):
        if stat in c:
            cand[stat] = c[stat]

    if curated:
        matched_names.add(key)
        if "blurb" in curated:
            cand["blurb"] = curated["blurb"]
        if curated.get("honor"):
            cand["honor"] = True
    else:
        bits = []
        if c.get("height"):
            bits.append(c["height"])
        if c.get("hometown"):
            bits.append(f"from {c['hometown']}")
        bio = " ".join(bits)
        pos_word = {"G": "guard", "F": "forward", "C": "center", "G/F": "guard/forward"}.get(c["pos"], c["pos"])
        if bio:
            blurb = f"{c['height']} {pos_word}{(' from ' + c['hometown']) if c.get('hometown') else ''}".replace("  ", " ")
            if not blurb.endswith("."):
                blurb += "."
            cand["blurb"] = blurb
        else:
            cand["blurb"] = None
    final_candidates.append(cand)

unmatched_curated = [k for k in curated_lookup if k not in matched_names]
print("Curated entries matched into full dataset:", len(matched_names), "/", len(curated_lookup))
print("Curated entries NOT found in full roster parse (kept separately):")
for k in unmatched_curated:
    print("  ", k)

# Recent seasons the PDF doesn't cover (2024-25, 2025-26) - carry these curated entries forward as-is
recent_extra = [curated_lookup[k] for k in unmatched_curated if int(k[1].split("–")[0]) >= 2024]
still_missing = [k for k in unmatched_curated if int(k[1].split("–")[0]) < 2024]
print()
print("Recent (2024+) curated entries added directly:", len(recent_extra))
print("Other unmatched (older) curated entries -- investigate:", still_missing)

for c in recent_extra:
    cand = {
        "name": c["name"],
        "season": c["season"],
        "pos": c["pos"],
        "posEligible": c["posEligible"],
    }
    for stat in ("ppg", "rpg", "apg", "spg", "bpg", "fg", "tp", "ft"):
        if stat in c:
            cand[stat] = c[stat]
    if "blurb" in c:
        cand["blurb"] = c["blurb"]
    if c.get("honor"):
        cand["honor"] = True
    final_candidates.append(cand)

CANONICAL_ORDER = {"G": 0, "F": 1, "C": 2}
for c in final_candidates:
    c["posEligible"] = sorted(set(c["posEligible"]), key=lambda p: CANONICAL_ORDER.get(p, 9))
    c["pos"] = "/".join(c["posEligible"])

# A starred (honor) player is a starred player everywhere -- carry their accolade
# blurb and gold-star treatment across every season of theirs, not just the one
# where they won the award, so any card of theirs reads as the same recognizable star.
honor_blurb_by_name = {}
for c in final_candidates:
    if c.get("honor") and c["name"] not in honor_blurb_by_name:
        honor_blurb_by_name[c["name"]] = c["blurb"]
for c in final_candidates:
    if c["name"] in honor_blurb_by_name:
        c["honor"] = True
        c["blurb"] = honor_blurb_by_name[c["name"]]

print()
print("Final total candidates:", len(final_candidates))
json.dump(final_candidates, open("final_candidates_flat.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
