import json, sqlite3

DB_PATH = "roster.db"
JSON_PATH = "era_data.json"

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row

# Field order must match era_data.json's existing convention exactly (verified
# against the current file): ppg is always present when any stat is; rpg,
# apg, spg, bpg, fg, tp, ft are each independently omitted if NULL (matches
# per-era stat availability -- assists/blocks/steals since 1975, 3PT since
# 1987); honor is omitted entirely when false/0, never written as false.
OPTIONAL_STAT_FIELDS = ["rpg", "apg", "spg", "bpg", "fg", "tp", "ft"]

data = []
for era_row in con.execute("SELECT id, decade FROM eras ORDER BY id"):
    era = {"id": era_row["id"], "decade": era_row["decade"], "candidates": []}
    rows = con.execute(
        """SELECT * FROM candidates WHERE era_id = ? ORDER BY order_in_era""",
        (era_row["id"],),
    ).fetchall()
    for r in rows:
        c = {
            "name": r["name"],
            "season": r["season"],
            "pos": r["pos"],
            "posEligible": json.loads(r["posEligible"]),
            "ppg": r["ppg"],
        }
        for field in OPTIONAL_STAT_FIELDS:
            if r[field] is not None:
                c[field] = r[field]
        c["blurb"] = r["blurb"]
        if r["honor"]:
            c["honor"] = True
        c["classYear"] = r["classYear"]
        era["candidates"].append(c)
    data.append(era)

json.dump(data, open(JSON_PATH, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
n_cands = sum(len(e["candidates"]) for e in data)
print(f"Exported {len(data)} eras, {n_cands} candidates to {JSON_PATH}")
con.close()
