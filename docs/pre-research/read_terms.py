from pathlib import Path
for name,terms in [('qwen-price',['qwen-plus','text-embedding-v4','中国内地','免费额度']),('crossref-rest',['license','copyright','free','abstract'])]:
 ls=Path('docs/pre-research/evidence/'+name+'.txt').read_text(encoding='utf-8').splitlines(); print(name)
 for term in terms:
  inds=[i for i,l in enumerate(ls) if term in l][:2]
  for i in inds:print('\n'.join(ls[max(0,i-2):i+28]))
