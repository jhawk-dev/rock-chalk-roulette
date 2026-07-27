import json

with open("ku_frankenstein_template.html", "r", encoding="utf-8") as f:
    html = f.read()

with open("era_data.json", "r", encoding="utf-8") as f:
    era_data = json.load(f)

era_json = json.dumps(era_data, ensure_ascii=False, separators=(",", ": "))

def read_b64(name):
    with open(f"ku-fonts/{name}", "r", encoding="utf-8") as f:
        return f.read().strip()

replacements = {
    "__BEBAS__": read_b64("bebas.b64"),
    "__SPECTRAL400__": read_b64("spectral-400.b64"),
    "__SPECTRAL400I__": read_b64("spectral-400i.b64"),
    "__SPECTRAL500__": read_b64("spectral-500.b64"),
    "__SPECTRAL600__": read_b64("spectral-600.b64"),
    "__JBMONO400__": read_b64("jbmono-400.b64"),
    "__JBMONO600__": read_b64("jbmono-600.b64"),
    "__JBMONO700__": read_b64("jbmono-700.b64"),
    "__ERA_DATA__": era_json,
}

for token, value in replacements.items():
    if token not in html:
        print("MISSING TOKEN:", token)
    html = html.replace(token, value)

with open("ku_frankenstein.html", "w", encoding="utf-8") as f:
    f.write(html)

print("built, size:", len(html))
