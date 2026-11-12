"""Assemble index.html = template.html + data.json + Plotly (inline, works offline).
Usage: python build_html.py   (needs: pip install plotly, only to read its bundled plotly.min.js)
Optional: put a plotly.min.js next to this file to use that one instead."""
import os,sys
here=os.path.dirname(os.path.abspath(__file__))
t=open(os.path.join(here,'template.html'),encoding='utf-8').read()
d=open(os.path.join(here,'data.json'),encoding='utf-8').read().replace('</','<\\/')
loc=os.path.join(here,'plotly.min.js')
if not os.path.exists(loc):
    import plotly
    loc=os.path.join(os.path.dirname(plotly.__file__),'package_data','plotly.min.js')
lib=open(loc,encoding='utf-8').read().replace('</script','<\\/script').replace('\ufffd','\\ufffd')
tag='<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.35.2/plotly.min.js"></script>'
assert tag in t
out=t.replace('/*__DATA__*/',d).replace(tag,'<script>'+lib+'</script>')
open(os.path.join(here,'index.html'),'w',encoding='utf-8').write(out)
print('index.html',round(len(out)/1e6,2),'MB')
