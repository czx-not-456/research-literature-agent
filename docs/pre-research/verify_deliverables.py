import json,re,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
base=Path('docs/pre-research'); checks=[]
def check(n,ok,d=''):checks.append({'name':n,'passed':bool(ok),'detail':d})
required=['PROJECT_STATUS.md','DEVELOPMENT_LOG.md','TECH_DECISIONS.md','THIRD_PARTY_COMPONENTS.md','ORIGINAL_WORK.md','TODO.md']+[str(base/x) for x in ['github-project-comparison.md','technology-selection.md','model-service-comparison.md','academic-search-api-comparison.md','development-risk-analysis.md']]
sources=[]
for p in sorted((base/'evidence').glob('*__*.txt')):
 t=p.read_text(encoding='utf-8');sources.append({'snapshot':'evidence/'+p.name,'header':t.splitlines()[:4]})
(base/'evidence/source-manifest.json').write_text(json.dumps({'date':'2026-11-16','method':'Read-only GitHub connector; snapshots include partial excerpts as marked; not pinned commits','sources':sources},ensure_ascii=False,indent=2),encoding='utf-8')
for name in required:
 p=Path(name);check('required:'+name,p.is_file() and p.stat().st_size>300)
 if not p.is_file():continue
 t=p.read_text(encoding='utf-8');check('utf8:'+name,'\ufffd' not in t)
 for link in re.findall(r'\]\(([^)]+)\)',t):
  if '://' not in link and not link.startswith('#'):check('link:'+name+':'+link,(p.parent/link.split('#')[0]).exists())
check('github-snapshot-count',len(sources)==43,{'count':len(sources)})
try:
 d=json.loads((base/'evidence/crossref-probe.json').read_text(encoding='utf-8'));a=d['message']['items'];check('crossref-real-schema',d['status']=='ok' and a and a[0].get('DOI') and a[0].get('title'))
except Exception as e:check('crossref-real-schema',False,str(e))
try:
 d=ET.fromstring((base/'evidence/arxiv-probe.html').read_bytes());a=d.findall('{http://www.w3.org/2005/Atom}entry');check('arxiv-real-schema',a and a[0].findtext('{http://www.w3.org/2005/Atom}id'))
except Exception as e:check('arxiv-real-schema',False,str(e))
extra=json.loads((base/'evidence/official-access-extra.json').read_text(encoding='utf-8'))
check('429-recorded-as-failure',all('429' in x.get('error','') for x in extra if x['name'] in ['openalex-probe','s2-probe']))
check('huawei-security-page-detected','Security Verification' in (base/'evidence/agentarts-help.html').read_text(encoding='utf-8'))
check('no-later-phase-artifacts',not Path('docs/design').exists() and not Path('package.json').exists())
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (base/'evidence').iterdir() if p.is_file() and p.name!='SHA256SUMS.json'}
(base/'evidence/SHA256SUMS.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
result={'date':'2026-11-16','scope':'Document integrity and single-response schema checks only; no business, PDF, model or cloud integration tests','passed':sum(x['passed'] for x in checks),'total':len(checks),'checks':checks,'evidence_files_hashed':len(hashes)}
(base/'verification-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False));print('Failures:',json.dumps([x for x in checks if not x['passed']],ensure_ascii=False))
