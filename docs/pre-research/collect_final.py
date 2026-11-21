import urllib.request,json,pathlib,concurrent.futures
urls={'openalex-price-final':'https://help.openalex.org/access/pricing/','openalex-costs':'https://help.openalex.org/access/example-costs/','openalex-home':'https://help.openalex.org/','openai-pricing':'https://openai.com/api/pricing/'}
def f(x):
 n,u=x;o={'name':n,'url':u}
 try:
  with urllib.request.urlopen(u,timeout=15) as r:
   d=r.read(2000000);pathlib.Path('docs/pre-research/evidence/'+n+'.html').write_bytes(d);o.update(status=r.status,final_url=r.url,bytes=len(d))
 except Exception as e:o['error']=str(e)
 return o
rs=list(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(f,urls.items()));pathlib.Path('docs/pre-research/evidence/official-access-final.json').write_text(json.dumps(rs,indent=2),encoding='utf-8');print(json.dumps(rs))
