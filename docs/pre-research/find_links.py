from html.parser import HTMLParser
from pathlib import Path
class P(HTMLParser):
 def handle_starttag(self,t,a):
  if t=='a':
   d=dict(a); u=d.get('href','')
   if any(x in u for x in ['pric','cost','licen','legal','CC0','billing']):print(u)
p=P();p.feed(Path('docs/pre-research/evidence/openalex.html').read_text(encoding='utf-8'))
