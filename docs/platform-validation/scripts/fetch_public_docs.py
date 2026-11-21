import urllib.request,urllib.error,pathlib,json,datetime,concurrent.futures,hashlib
from html.parser import HTMLParser
BASE=pathlib.Path('docs/platform-validation/evidence')
URLS={'official-guide':'https://support.huaweicloud.com/agentarts/index.html','official-product':'https://www.huaweicloud.com/product/agentarts.html?utm_source=zgcompetition','official-docs':'https://docs.huaweicloud.com/agentarts'}
class Page(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[];self.links=[]
 def handle_starttag(self,t,a):
  d=dict(a)
  if t in ('script','style'):self.skip+=1
  if t=='a' and d.get('href'):self.links.append(d['href'])
 def handle_endtag(self,t):
  if t in ('script','style'):self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip and d.strip():self.parts.append(d.strip())
def fetch(x):
 name,url=x;o={'name':name,'url':url,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ResearchLiteratureAgent-PlatformValidation/0.1'}),timeout=15) as r:
   b=r.read(3000000);o.update(status=r.status,final_url=r.url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest());(BASE/(name+'.html')).write_bytes(b)
   p=Page();p.feed(b.decode('utf-8',errors='replace'));txt='\n'.join(p.parts);(BASE/(name+'.txt')).write_text(txt,encoding='utf-8');(BASE/(name+'-links.json')).write_text(json.dumps(p.links,ensure_ascii=False,indent=2),encoding='utf-8');o['content_status']='security_challenge' if any(t in b.decode('utf-8',errors='replace') for t in ['Security Verification','TencentEOCaptchaWidget','EO_Bot_Ssid']) else 'needs_content_review';o['text_preview']=txt[:1600]
 except Exception as e:o['error']=str(e)
 return o
if __name__=='__main__':
 rs=list(concurrent.futures.ThreadPoolExecutor(max_workers=3).map(fetch,URLS.items()));(BASE/'public-doc-access.json').write_text(json.dumps(rs,ensure_ascii=False,indent=2),encoding='utf-8')
 for r in rs:print(json.dumps(r,ensure_ascii=False))
