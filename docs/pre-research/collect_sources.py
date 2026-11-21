import urllib.request, concurrent.futures, pathlib, json, datetime
sources = {
 'agentarts-help':'https://support.huaweicloud.com/agentarts/index.html',
 'agentarts-product':'https://www.huaweicloud.com/product/agentarts.html',
 'openalex':'https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication',
 'openalex-new':'https://developers.openalex.org/how-to-use-the-api/rate-limits-and-authentication',
 's2':'https://www.semanticscholar.org/product/api',
 's2-license':'https://www.semanticscholar.org/product/api/license',
 'crossref':'https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-metadata-retrieval/',
 'crossref-limits':'https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/',
 'arxiv':'https://info.arxiv.org/help/api/tou.html',
 'deepseek':'https://api-docs.deepseek.com/quick_start/pricing',
 'qwen':'https://help.aliyun.com/zh/model-studio/models',
 'siliconflow':'https://docs.siliconflow.cn/cn/userguide/pricing',
 'huawei-model':'https://support.huaweicloud.com/productdesc-maas/maas_01_0001.html',
}
def fetch(item):
 name,url=item; out={'name':name,'url':url,'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'ResearchLiteratureAgent-PreResearch/0.1'})
  with urllib.request.urlopen(req,timeout=18) as r:
   data=r.read(2500000); out.update(status=r.status,final_url=r.url,bytes=len(data)); pathlib.Path('docs/pre-research/evidence/'+name+'.html').write_bytes(data)
 except Exception as e: out['error']=str(e)
 return out
results=list(concurrent.futures.ThreadPoolExecutor(max_workers=6).map(fetch,sources.items()))
pathlib.Path('docs/pre-research/evidence/official-access.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
for x in results: print(json.dumps(x,ensure_ascii=False))
