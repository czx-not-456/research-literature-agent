from html.parser import HTMLParser
from pathlib import Path
import re
class Text(HTMLParser):
 def __init__(self): super().__init__(); self.skip=0; self.parts=[]
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style'): self.skip+=1
 def handle_endtag(self,tag):
  if tag in ('script','style'): self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip and d.strip(): self.parts.append(d.strip())
for p in Path('docs/pre-research/evidence').glob('*.html'):
 t=Text();t.feed(p.read_text(encoding='utf-8',errors='replace')); p.with_suffix('.txt').write_text('\n'.join(t.parts),encoding='utf-8')
for name in ['openalex','s2','s2-license','crossref-limits','arxiv','deepseek']:
 p=Path('docs/pre-research/evidence')/(name+'.txt'); lines=p.read_text(encoding='utf-8').splitlines()
 print('\nSOURCE',name)
 for i,l in enumerate(lines):
  if re.search(r'price|free|limit|second|requests|license|commercial|attribution|million|token|\$|2026',l,re.I): print(' | '.join(lines[max(0,i-1):i+3])[:1300])
