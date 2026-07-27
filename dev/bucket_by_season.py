import json, re

data = json.load(open("final_candidates_flat.json", encoding="utf-8"))

def start_year(season_label):
    # "1995–96" -> 1995 ; "1999–2000" -> 1999
    return int(season_label.split("–")[0])

buckets = {}
for c in data:
    y = start_year(c["season"])
    buckets.setdefault(y, []).append(c)

ordered_years = sorted(buckets.keys())

# Drop seasons the career-stats book doesn't cover (only the handful of individually
# researched stars, not a real team roster) -- these are single-candidate outliers;
# the thinnest legitimate historical seasons still have 10+ players.
MIN_ROSTER_SIZE = 5
dropped = [y for y in ordered_years if len(buckets[y]) < MIN_ROSTER_SIZE]
ordered_years = [y for y in ordered_years if len(buckets[y]) >= MIN_ROSTER_SIZE]
if dropped:
    print("Dropping incomplete-roster seasons (fewer than", MIN_ROSTER_SIZE, "candidates):")
    for y in dropped:
        names = [c["name"] for c in buckets[y]]
        print("  ", buckets[y][0]["season"], "-", ", ".join(names))
    print()

new_data = []
for y in ordered_years:
    cands = buckets[y]
    label = cands[0]["season"]
    clean_cands = []
    for c in cands:
        cc = {"name": c["name"], "season": c["season"], "pos": c["pos"], "posEligible": c["posEligible"]}
        for stat in ("ppg", "rpg", "apg", "spg", "bpg", "fg", "tp", "ft"):
            if stat in c:
                cc[stat] = c[stat]
        if c.get("blurb"):
            cc["blurb"] = c["blurb"]
        if c.get("honor"):
            cc["honor"] = True
        clean_cands.append(cc)
    new_data.append({"id": f"season-{y}", "decade": label, "candidates": clean_cands})

POS = ["G", "F", "C"]
print(f"Total season buckets: {len(new_data)}")
print(f"Total candidates: {sum(len(e['candidates']) for e in new_data)}")
print(f"Year range: {ordered_years[0]}-{ordered_years[-1]}")
print()

missing_any = 0
zero_positions = []
for e in new_data:
    cov = {p: 0 for p in POS}
    for c in e["candidates"]:
        for p in c["posEligible"]:
            cov[p] += 1
    missing = [p for p in POS if cov[p] == 0]
    if missing:
        missing_any += 1
        zero_positions.append((e["decade"], missing, len(e["candidates"])))

print("Buckets missing at least one position entirely:", missing_any, "/", len(new_data))
for d, m, n in zero_positions[:15]:
    print(" ", d, "n=" + str(n), "missing:", m)

with open("era_data.json", "w", encoding="utf-8") as f:
    json.dump(new_data, f, indent=2, ensure_ascii=False)
    f.write("\n")
print()
print("Wrote era_data.json")
