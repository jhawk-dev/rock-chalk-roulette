import re, json

raw_lines = open("all_players_career_stats_v2.txt", encoding="utf-8").read().splitlines()
lines = [l.strip() for l in raw_lines]
header_re = re.compile(r"^([A-Z][A-Z .'\-]+?)\s*•\s*([A-Z/\-]+)\s*•\s*([\d\-\/ ]+)\s*•\s*(\d+)\s*•\s*(.+)$")

players = []
current = None
skipped_headers = []
for idx, line in enumerate(lines):
    if not line or line.startswith("===PAGE") or line.startswith("#kubball") or line.startswith("@KU") \
       or line.startswith("YR ") or "ABOUT THE CAREER" in line or line.startswith("The following") \
       or "since 1946" in line or "pointers since" in line:
        continue

    next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
    is_header_by_context = next_line.startswith("YR ")

    ym_check = re.match(r"^\d{4}-\d{2,4}\s", line)
    if is_header_by_context and not ym_check and not line.startswith("Totals"):
        if current:
            players.append(current)
        m = header_re.match(line)
        if m:
            current = {
                "name_raw": m.group(1).strip(),
                "pos_raw": m.group(2).strip().replace("-", "/"),
                "height": m.group(3).strip(),
                "weight": m.group(4).strip(),
                "hometown": m.group(5).strip(),
                "seasons": []
            }
        else:
            # malformed/incomplete bio line -- still a real player, just missing some fields
            skipped_headers.append(line)
            name_only = re.split(r"\s*•\s*", line)[0].strip()
            current = {
                "name_raw": name_only if name_only else line,
                "pos_raw": "",
                "height": "",
                "weight": "",
                "hometown": "",
                "seasons": []
            }
        continue

    if current is None:
        continue
    ym = re.match(r"^(\d{4}-\d{2,4})\s+(.*)$", line)
    if ym:
        current["seasons"].append((ym.group(1), ym.group(2)))
if current: players.append(current)

print("Player headers with incomplete bio info (name-only fallback used):", len(skipped_headers))
for h in skipped_headers[:20]:
    print("  ", h)

def end_year(season):
    parts = season.split("-")
    start = int(parts[0])
    end_part = parts[1]
    if len(end_part) == 4:
        end = int(end_part)
    else:
        prefix = start // 100
        end = prefix * 100 + int(end_part)
        if end < start:
            end += 100
    return end

def season_label(season):
    parts = season.split("-")
    start = int(parts[0])
    end_part = parts[1]
    if len(end_part) == 2:
        return f"{start}–{end_part}"
    else:
        return f"{start}–{str(int(end_part))[-2:]}"

RE_MA = re.compile(r"^\d+-\d*$")         # "115-269" or "4-" (attempts blank)
RE_PCT = re.compile(r"^(\.\d{2,3}|1\.00?0?|-{2,4})$")   # ".483", "1.000", or "---" (no attempts, pct undefined)
RE_AVG = re.compile(r"^\d*\.\d$|^\d+$")  # one decimal place (some rows drop the leading zero, e.g. ".3" for 0.3); some rows also collapse an exact 0.0 to a bare "0"
RE_INT = re.compile(r"^\d+$")

def try_parse_with(tokens, y, want_min, want_3fg, want_reb, adv_mode):
    """Shape-driven sequential parse under one hypothesis of which optional column
    groups are present. Every field is still shape-verified (hyphen pair / percentage /
    average / integer) as it's consumed -- a wrong hypothesis fails via leftover
    unconsumed tokens rather than silently misassigning a value to the wrong field."""
    i = 0
    n = len(tokens)
    out = {}

    def take(name, matcher):
        nonlocal i
        if i < n and matcher.match(tokens[i]):
            out[name] = tokens[i]
            i += 1
            return True
        return False

    if not take("GAMES", RE_MA) and not take("GAMES", RE_INT):
        return None

    if want_min:
        if not take("MIN", RE_INT): return None
        if not take("MPG", RE_AVG): return None

    if not take("FG_MA", RE_MA):
        return None
    take("FG_PCT", RE_PCT)

    if want_3fg:
        if not take("FG3_MA", RE_MA): return None
        take("FG3_PCT", RE_PCT)

    if not take("FT_MA", RE_MA):
        return None
    take("FT_PCT", RE_PCT)

    if want_reb:
        if not take("REB", RE_INT): return None
        if not take("RPG", RE_AVG): return None

    take("PF", RE_INT)

    if adv_mode == "full":
        if not take("AST", RE_INT): return None
        if not take("TO", RE_INT): return None
        if not take("BLK", RE_INT): return None
        if not take("ST", RE_INT): return None
    elif adv_mode == "no_to":
        # turnovers weren't consistently compiled for some early-1980s rows even
        # though assists/blocks/steals were -- the book just omits that one column.
        if not take("AST", RE_INT): return None
        if not take("BLK", RE_INT): return None
        if not take("ST", RE_INT): return None

    if not take("PTS", RE_INT):
        return None
    if not take("PPG", RE_AVG):
        return None

    if i != n:
        return None  # leftover unconsumed tokens -> this hypothesis didn't fully explain the row
    return out

def _clean_tokens(tokens):
    # strip a stray trailing "." off an otherwise-valid made-attempt/int token,
    # e.g. "2-3." -> "2-3" (isolated OCR/extraction typos)
    cleaned = []
    for t in tokens:
        if t.endswith(".") and len(t) > 1:
            stripped = t[:-1]
            if RE_MA.match(stripped) or RE_INT.match(stripped):
                cleaned.append(stripped)
                continue
        cleaned.append(t)
    return cleaned

def _search(tokens, y, min_opts, fg3_opts, reb_opts, adv_opts):
    best = None
    best_len = -1
    for want_min in min_opts:
        for want_3fg in fg3_opts:
            for want_reb in reb_opts:
                for adv_mode in adv_opts:
                    parsed = try_parse_with(tokens, y, want_min, want_3fg, want_reb, adv_mode)
                    if parsed is not None and len(parsed) > best_len:
                        best = parsed
                        best_len = len(parsed)
    return best

def parse_row(tokens, y):
    """Tries hypotheses about which optional column groups (minutes, 3-pointers,
    rebounds, assists/steals/blocks/turnovers) are present for this specific row --
    some rows drop a whole group (usually because the player never attempted a 3, so
    the book omits the column instead of writing "0-0") even in years where that stat
    was generally tracked. Picks whichever hypothesis fully explains the row and
    captures the most fields. The book's own "tracked since" cutoffs are used as the
    primary guide, but a handful of rows have a category recorded slightly outside
    those years (or missing well within them) -- so if nothing fits under the normal
    year-gated hypotheses, retry with every combination regardless of year rather than
    giving up and falling back to points-only."""
    tokens = _clean_tokens(tokens)

    best = _search(
        tokens, y,
        [True, False],
        [True, False] if y >= 1987 else [False],
        [True, False] if y >= 1955 else [False],
        ["full", "no_to", "none"] if y >= 1975 else ["none"],
    )
    if best is not None:
        return best

    return _search(tokens, y, [True, False], [True, False], [True, False], ["full", "no_to", "none"])

def games_played(games_token):
    m = re.match(r"^(\d+)", games_token)
    if not m:
        return None
    return int(m.group(1))

def pct_to_num(tok):
    if tok is None:
        return None
    try:
        val = round(float(tok) * 100, 1)
    except ValueError:
        return None
    if val < 0 or val > 100:
        return None
    return val

def attempts_are_zero(ma_tok):
    # "0-0" -> zero attempts, so any accompanying pct is meaningless (not "0.0%", just N/A)
    if ma_tok is None:
        return False
    m = re.match(r"^\d+-(\d+)$", ma_tok)
    return bool(m) and int(m.group(1)) == 0

SUFFIXES = {"JR", "JR.", "SR", "SR.", "II", "III", "IV", "V"}
VOWELS = set("AEIOU")
NAME_FIXES = {
    "ELAMRKO JACKSON": "Elmarko Jackson",
    "RAEF LAFRENTZ": "Raef LaFrentz",
    "AJ STORR": "AJ Storr",
}

def title_case_name(raw):
    raw = re.sub(r"\s+", " ", raw).strip()
    if raw.upper() in NAME_FIXES:
        return NAME_FIXES[raw.upper()]
    words = raw.split(" ")
    out = []
    for w in words:
        if w.upper() in SUFFIXES:
            out.append(w.upper() if w.upper() in ("II", "III", "IV", "V") else w.capitalize())
            continue
        if "." in w and len(w) <= 5:
            out.append(w.upper())
            continue
        if len(w) == 2 and w.isalpha() and not any(ch in VOWELS for ch in w.upper()):
            out.append(w.upper())
            continue
        pieces = re.split(r"(-|')", w)
        cased = []
        for p in pieces:
            if p in ("-", "'"):
                cased.append(p)
                continue
            if p.upper().startswith("MC") and len(p) > 2:
                cased.append("Mc" + p[2:3].upper() + p[3:].lower())
            elif p.upper().startswith("O'") and len(p) > 2:
                cased.append("O'" + p[2:3].upper() + p[3:].lower())
            elif p:
                cased.append(p[0].upper() + p[1:].lower())
        out.append("".join(cased))
    return " ".join(out)

POS_MAP = {"G": "G", "F": "F", "C": "C", "G/F": "G/F"}

candidates = []
stats = {"full": 0, "fallback": 0, "skip": 0}
sanity_drops = {"rpg": 0, "apg": 0, "spg": 0, "bpg": 0, "fg": 0, "tp": 0, "ft": 0, "ppg": 0}

no_position = 0
for p in players:
    disp_name = title_case_name(p["name_raw"])
    pos_disp = POS_MAP.get(p["pos_raw"], p["pos_raw"])
    valid_positions = {"G", "F", "C"}
    pos_eligible = pos_disp.split("/") if "/" in pos_disp else [pos_disp]
    if not pos_eligible or not all(p_ in valid_positions for p_ in pos_eligible):
        no_position += len(p["seasons"])
        continue

    for yr, rest in p["seasons"]:
        if yr == "Totals":
            continue
        tokens = rest.split()
        y = end_year(yr)
        if len(tokens) < 2:
            stats["skip"] += 1
            continue

        parsed = parse_row(tokens, y)
        cand = {
            "name": disp_name,
            "season": season_label(yr),
            "year": y,
            "pos": pos_disp,
            "posEligible": pos_eligible,
            "hometown": p["hometown"],
            "height": p["height"],
        }

        if parsed is None:
            # fallback: only trust token[0]=games, token[-1]=ppg if it looks like one
            if not re.match(r"^\d*\.\d$", tokens[-1]):
                stats["skip"] += 1
                continue
            gp = games_played(tokens[0])
            if not gp or gp <= 0:
                stats["skip"] += 1
                continue
            cand["ppg"] = float(tokens[-1])
            cand["gp"] = gp
            stats["fallback"] += 1
            candidates.append(cand)
            continue

        gp = games_played(parsed["GAMES"])
        if not gp or gp <= 0:
            stats["skip"] += 1
            continue

        ppg = float(parsed["PPG"])
        if ppg < 0 or ppg > 45:
            sanity_drops["ppg"] += 1
        else:
            cand["ppg"] = ppg

        if "RPG" in parsed:
            v = float(parsed["RPG"])
            if 0 <= v <= 25:
                cand["rpg"] = v
            else:
                sanity_drops["rpg"] += 1

        if "AST" in parsed:
            v = round(int(parsed["AST"]) / gp, 1)
            if 0 <= v <= 15:
                cand["apg"] = v
            else:
                sanity_drops["apg"] += 1

        if "ST" in parsed:
            v = round(int(parsed["ST"]) / gp, 1)
            if 0 <= v <= 8:
                cand["spg"] = v
            else:
                sanity_drops["spg"] += 1

        if "BLK" in parsed:
            v = round(int(parsed["BLK"]) / gp, 1)
            if 0 <= v <= 8:
                cand["bpg"] = v
            else:
                sanity_drops["bpg"] += 1

        if not attempts_are_zero(parsed.get("FG_MA")):
            fgp = pct_to_num(parsed.get("FG_PCT"))
            if fgp is not None:
                cand["fg"] = fgp
            elif parsed.get("FG_PCT") is not None:
                sanity_drops["fg"] += 1

        if not attempts_are_zero(parsed.get("FG3_MA")):
            tpp = pct_to_num(parsed.get("FG3_PCT"))
            if tpp is not None:
                cand["tp"] = tpp
            elif parsed.get("FG3_PCT") is not None:
                sanity_drops["tp"] += 1

        if not attempts_are_zero(parsed.get("FT_MA")):
            ftp = pct_to_num(parsed.get("FT_PCT"))
            if ftp is not None:
                cand["ft"] = ftp
            elif parsed.get("FT_PCT") is not None:
                sanity_drops["ft"] += 1

        if "ppg" not in cand:
            stats["skip"] += 1
            continue

        cand["gp"] = gp
        stats["full"] += 1
        candidates.append(cand)

seen_keys = set()
deduped = []
dupe_count = 0
for c in candidates:
    key = (c["name"], c["season"])
    if key in seen_keys:
        dupe_count += 1
        continue
    seen_keys.add(key)
    deduped.append(c)
candidates = deduped

print("Stats:", stats)
print("Sanity drops (out-of-range values discarded, field omitted):", sanity_drops)
print("Rows skipped for unrecognized/missing position:", no_position)
print("Exact (name, season) duplicates removed:", dupe_count)
print("Total candidates:", len(candidates))
json.dump(candidates, open("full_roster_candidates.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
