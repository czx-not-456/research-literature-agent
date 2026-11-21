import argparse,datetime,json,pathlib,time,urllib.request,urllib.parse,urllib.error
BASE=pathlib.Path('docs/platform-validation/evidence')
def main():
 parser=argparse.ArgumentParser(description='Single real Crossref search probe; not an AgentArts tool server.')
 parser.add_argument('--query',required=True);a=parser.parse_args();q=a.query.strip()
 if not q or len(q)>200:
  print(json.dumps({'status':'invalid_input','error':'query must contain 1..200 characters'}));return 2
 params=urllib.parse.urlencode({'query.bibliographic':q,'filter':'type:journal-article','rows':2})
 url='https://api.crossref.org/works?'+params
 result={'scope':'local external source only; not a platform call','url':url,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};start=time.monotonic()
 try:
  request=urllib.request.Request(url,headers={'User-Agent':'ResearchLiteratureAgent-PlatformValidation/0.1'})
  with urllib.request.urlopen(request,timeout=20) as r:
   raw=r.read(2000000);(BASE/'crossref-search-raw.json').write_bytes(raw);body=json.loads(raw);items=body['message']['items']
   result.update(http_status=r.status,rate_headers={k:v for k,v in r.headers.items() if 'rate' in k.lower() or 'retry' in k.lower()},items=[{'title':i.get('title',[]),'doi':i.get('DOI'),'type':i.get('type'),'url':i.get('URL')} for i in items])
   result['schema_valid']=body.get('status')=='ok' and all(i.get('type')=='journal-article' and i.get('DOI') and i.get('title') for i in items)
   result['status']='passed_local_probe' if result['schema_valid'] and items else 'no_verified_items'
 except urllib.error.HTTPError as e:result.update(status='http_error',http_status=e.code,error=str(e))
 except Exception as e:result.update(status='error',error=str(e))
 result['elapsed_seconds']=round(time.monotonic()-start,3);BASE.mkdir(parents=True,exist_ok=True);(BASE/'crossref-search-probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False));return 0 if result['status']=='passed_local_probe' else 1
if __name__=='__main__':raise SystemExit(main())
