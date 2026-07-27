import json, os, sqlite3

DB_PATH = "roster.db"
JSON_PATH = "era_data.json"

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

con = sqlite3.connect(DB_PATH)
con.executescript(open("schema.sql", encoding="utf-8").read())

data = json.load(open(JSON_PATH, encoding="utf-8"))

for era in data:
    con.execute("INSERT INTO eras (id, decade) VALUES (?, ?)", (era["id"], era["decade"]))
    for i, c in enumerate(era["candidates"]):
        con.execute(
            """INSERT INTO candidates
               (era_id, order_in_era, name, season, pos, posEligible,
                ppg, rpg, apg, spg, bpg, fg, tp, ft, blurb, honor, classYear)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                era["id"], i, c["name"], c["season"], c.get("pos"),
                json.dumps(c["posEligible"], ensure_ascii=False),
                c.get("ppg"), c.get("rpg"), c.get("apg"), c.get("spg"), c.get("bpg"),
                c.get("fg"), c.get("tp"), c.get("ft"),
                c.get("blurb"), 1 if c.get("honor") else 0, c.get("classYear"),
            ),
        )

con.commit()
n_eras = con.execute("SELECT COUNT(*) FROM eras").fetchone()[0]
n_cands = con.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
print(f"Imported {n_eras} eras, {n_cands} candidates into {DB_PATH}")
con.close()
