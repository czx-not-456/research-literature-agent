import urllib.request, pathlib, json, concurrent.futures
sources={
'openalex-pricing':'https://help.openalex.org/api/pricing/',
'openalex-license':'https://help.openalex.org/overview/legal/',
'crossref-rest':'https://www.crossref.org/documentation/retrieve-metadata/rest-api/',
'qwen-price':'https://help.aliyun.com/zh/model-studio/model-pricing',
'qwen-openai':'https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope',
'deepseek-tools':'https://api-docs.deepseek.com/guides/tool_calls',
'agentarts-docs':'https://docs.huaweicloud.com/agentarts',
'openalex-probe':'https://api.openalex.org/works?search=retrieval%20augmented%20generation&per-page=1',
'crossref-probe':'https://api.crossref.org/works?query.bibliographic=retrieval%20augmented%20generation&rows=1',
'arxiv-probe':'https://export.arxiv.org/api/query?search_query=all:retrieval&max_results=1',
's2-probe':'https://api.semanticscholar.org/graph/v1/paper/search?query=retrieval&limit=1&fields=title,year,url,externalIds'
}
def run(x):
 n,u=x; o={'name':n,'url':u}
 try:
  with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'ResearchLiteratureAgent-PreResearch/0.1'}),timeout=18) as r:
   d=r.read(2500000);o.update(status=r.status,final_url=r.url,bytes=len(d),rate_headers={k:v for k,v in r.headers.items() if 'rate' in k.lower() or 'retry' in k.lower()});pathlib.Path('docs/pre-research/evidence/'+n+('.json' if 'probe' in n and n!='arxiv-probe' else '.html')).write_bytes(d)
 except Exception as e:o['error']=str(e)
 return o
rs=list(concurrent.futures.ThreadPoolExecutor(max_workers=6).map(run,sources.items()));pathlib.Path('docs/pre-research/evidence/official-access-extra.json').write_text(json.dumps(rs,ensure_ascii=False,indent=2),encoding='utf-8')
for r in rs:print(json.dumps(r,ensure_ascii=False))
