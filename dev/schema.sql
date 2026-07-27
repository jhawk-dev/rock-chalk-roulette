-- Dev-time source of truth for roster/stats data. Not read by the live site --
-- build.py still embeds era_data.json into index.html. Workflow:
--   1. python3 import_to_db.py   (fresh roster.db from the current era_data.json)
--   2. edit via `sqlite3 roster.db` or a script
--   3. python3 export_from_db.py (regenerates era_data.json from roster.db)
--   4. python3 build.py          (rebuilds index.html as usual)

CREATE TABLE eras (
  id     TEXT PRIMARY KEY,   -- e.g. "season-1998"
  decade TEXT NOT NULL       -- display label, e.g. "1998–99" (field name kept
                              -- from era_data.json's existing "decade" key,
                              -- even though it's actually a season label)
);

CREATE TABLE candidates (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  era_id        TEXT NOT NULL REFERENCES eras(id),
  order_in_era  INTEGER NOT NULL,  -- preserves original array order on export
  name          TEXT NOT NULL,
  season        TEXT NOT NULL,
  pos           TEXT,
  posEligible   TEXT NOT NULL,     -- JSON array, e.g. ["G"] or ["G","F"]
  ppg REAL, rpg REAL, apg REAL, spg REAL, bpg REAL,
  fg REAL, tp REAL, ft REAL,
  blurb     TEXT,
  honor     INTEGER NOT NULL DEFAULT 0,
  classYear TEXT,
  UNIQUE (name, season)             -- the constraint that would've caught
                                     -- the John Cleland / Christian Braun
                                     -- duplicate-row bug immediately
);

CREATE INDEX idx_candidates_era ON candidates(era_id);
CREATE INDEX idx_candidates_name ON candidates(name);
