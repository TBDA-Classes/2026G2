"""Assemble index.html = template.html + data.json + Plotly (inline, works offline).
Usage: python build_html.py   (needs: pip install plotly, only to read its bundled plotly.min.js)
Optional: put a plotly.min.js next to this file to use that one instead.
Output: ../index.html (package root)."""
from pathlib import Path
here = Path(__file__).resolve().parent
t = (here / "template.html").read_text(encoding="utf-8")
d = (here / "data.json").read_text(encoding="utf-8").replace("</", "<\\/")
loc = here / "plotly.min.js"
if not loc.exists():
    import plotly
    loc = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
lib = loc.read_text(encoding="utf-8").replace("</script", "<\\/script").replace("\ufffd", "\\ufffd")
tag = '<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.35.2/plotly.min.js"></script>'
assert tag in t and "/*__DATA__*/" in t
out = t.replace("/*__DATA__*/", d).replace(tag, "<script>" + lib + "</script>")
(here.parent / "index.html").write_text(out, encoding="utf-8")
print("index.html", round(len(out) / 1e6, 2), "MB")
