#!/usr/bin/env python3
"""Actual-artifact drift challenges; packaging hashes are recomputed for inner mutations."""
from pathlib import Path
import tempfile,shutil,json,sys,re
sys.dont_write_bytecode=True
from bs4 import BeautifulSoup
import build_derivative as build
from validate_derivative import validate,load,mdblocks
ROOT=Path(__file__).resolve().parents[1]
def change(r,file,old,new):
 p=r/file;s=p.read_text();assert old in s;p.write_text(s.replace(old,new,1))
def manuscript_change(r,file,old,new):
 p=r/file;s=p.read_text();marker='## Canonical paper text\n\n'
 if file=='README.md':
  prefix,body=s.split(marker);assert old in body;p.write_text(prefix+marker+body.replace(old,new,1))
 else:change(r,file,old,new)
def js(r,file,fn):
 p=r/file;d=json.loads(p.read_text());fn(d);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def dom(r,selector,fn):
 p=r/'index.html';s=BeautifulSoup(p.read_text(),'html.parser');n=s.select_one(selector);assert n is not None;fn(n);p.write_text(str(s))
cases=[]
for file in ['paper.md','README.md']:
 for old in ['This essay lays out','Jiaru Zou','[15] Pierce, B.']:
  cases.append((file+' content '+old,lambda r,f=file,o=old:manuscript_change(r,f,o,o+' ALTERED'),'Complete '+('Markdown' if file=='paper.md' else 'README')))
for selector,label in [('#b015','ordinary body'),('#b007','abstract'),('#ref-15','last reference')]:
 cases.append(('HTML '+label+' word',lambda r,s=selector:dom(r,s,lambda n:n.append(' ALTERED')),'Complete HTML'))
for mode in ['delete','duplicate','reorder','hidden','stray']:
 def mutate(r,m=mode):
  p=r/'index.html';s=BeautifulSoup(p.read_text(),'html.parser');n=s.select_one('#b025')
  if m=='delete':n.decompose()
  if m=='duplicate':n.insert_after(BeautifulSoup(str(n),'html.parser'))
  if m=='reorder':s.select_one('#canonical-paper').insert(0,n.extract())
  if m=='hidden':n['hidden']=''
  if m=='stray':n.insert_after(BeautifulSoup('<div>Stray paper text.</div>','html.parser'))
  p.write_text(str(s))
 cases.append(('HTML '+mode,mutate,'Hidden canonical' if mode=='hidden' else 'Unaccounted canonical' if mode=='stray' else 'Complete HTML'))
for key in ['citation_title','citation_author','citation_publication_date','citation_doi','citation_pdf_url','description','keywords','robots']:
 cases.append(('HTML wrong '+key,lambda r,k=key:dom(r,'meta[name="'+k+'"]',lambda n:n.__setitem__('content','wrong')),'Metadata '+key))
for mode in ['missing','duplicate']:
 def mutate(r,m=mode):
  p=r/'index.html';s=BeautifulSoup(p.read_text(),'html.parser');n=s.select_one('meta[name="citation_author"]')
  if m=='missing':n.decompose()
  else:n.insert_after(BeautifulSoup(str(n),'html.parser'))
  p.write_text(str(s))
 cases.append(('HTML author '+mode,mutate,'Metadata citation_author'))
for mode in ['missing','duplicate','wrong']:
 def subject_change(r,m=mode):
  def alter(n):
   if m=='missing':n.decompose()
   elif m=='duplicate':n.insert_after(BeautifulSoup(str(n),'html.parser'))
   else:n['content']='wrong'
  dom(r,'meta[name="DC.subject"]',alter)
 cases.append(('Dublin Core keyword '+mode,subject_change,'Dublin Core keyword vector'))
for mode in ['missing','duplicate','wrong']:
 def preferred_change(r,m=mode):
  import yaml
  p=r/'CITATION.cff';d=yaml.safe_load(p.read_text());k=d['preferred-citation']['keywords']
  if m=='missing':del d['preferred-citation']['keywords']
  elif m=='duplicate':k.append(k[0])
  else:k[0]='wrong'
  p.write_text(yaml.safe_dump(d,sort_keys=False,allow_unicode=True))
 cases.append(('CFF preferred keyword '+mode,preferred_change,'CFF preferred keyword vector'))
cases.extend([
 ('specific internal citation',lambda r:dom(r,'a.citeref',lambda n:n.__setitem__('href','#ref-15')),'Specific numbered citation'),
 ('displayed URL mismatch',lambda r:dom(r,'#ref-1 a',lambda n:n.__setitem__('href','https://doi.org/10.5281/zenodo.23401563')),'Displayed URL target'),
 ('abstract title hyperlink',lambda r:dom(r,'#b007 em',lambda n:n.wrap(BeautifulSoup('<a href="https://example.com"></a>','html.parser').a)),'Displayed URL target'),
 ('metadata keyword',lambda r:js(r,'metadata.json',lambda d:d['keywords'].append('unsupported')),'Structured metadata content'),
 ('metadata ORCID',lambda r:js(r,'metadata.json',lambda d:d['authors'][0].update(orcid='0000-0000-0000-0000')),'Structured author'),
 ('CFF date',lambda r:change(r,'CITATION.cff','2026-10-15','2026-10-14'),'CFF actual field'),
 ('CFF duplicate DOI',lambda r:(r/'CITATION.cff').write_text((r/'CITATION.cff').read_text()+'doi: wrong\n'),'Duplicate structured key'),
 ('scope instruction',lambda r:change(r,'README.md','This essay is an appropriate citation','Cite this essay'),'Synchronized README scope'),
 ('source rewrite and regeneration',lambda r:(js(r,'source/paper.json',lambda d:d.update(canonical_text=d['canonical_text']+'Changed.')),build.run(r)),'Frozen authority changed'),
 ('normalized bibliography date',lambda r:(js(r,'bibliography.json',lambda d:d['works'][0].update(issued={'date_parts':[2026,10,13]})),build.run(r)),'Frozen authority changed'),
 ('normalized bibliography author',lambda r:(js(r,'bibliography.json',lambda d:d['works'][0]['authors'][0].update(given='Wrong')),build.run(r)),'Frozen authority changed'),
 ('normalized bibliography opaque DOI',lambda r:(js(r,'bibliography.json',lambda d:d['works'][0].update(doi='10.48550/arXiv.2610\\_18861')),build.run(r)),'Frozen authority changed'),
 ('metadata duplicate key',lambda r:change(r,'metadata.json','"doi":','"doi": "wrong", "doi":'),'Duplicate structured key'),
 ('PDF appended bytes',lambda r:(r/build.PDF).write_bytes((r/build.PDF).read_bytes()+b'changed'),'Published immutable PDF identity'),
 ('public executable-mode drift',lambda r:(r/'paper.md').chmod(0o755),'Exact intended public file modes'),
 ('extra public file',lambda r:(r/'unexpected.txt').write_text('Unexpected'),'Exact intended public path'),
 ('transient ignored public file',lambda r:((r/'__pycache__').mkdir(),(r/'__pycache__/cached.pyc').write_bytes(b'cache')),'Exact intended public path'),
 ('RIS title drift',lambda r:change(r,'references.ris','TI  - Hybrid Reasoning Agents','TI  - Wrong Hybrid Reasoning Agents'),'Generated drift'),
 ('BibTeX DOI drift',lambda r:change(r,'references.bib','10.48550/arXiv.2610.18861','10.48550/arXiv.2610.18862'),'Generated drift'),
])
results=[];baseline=validate(ROOT)
with tempfile.TemporaryDirectory(prefix='f165-regressions-') as temp:
 r=Path(temp)/'paper'
 for name,fn,reason in cases:
  if r.exists():shutil.rmtree(r)
  shutil.copytree(ROOT,r,ignore=shutil.ignore_patterns('.git','node_modules','__pycache__'))
  fn(r);(r/'checksums.sha256').write_text(build.manifest(r))
  try:validate(r)
  except (AssertionError,KeyError,ValueError) as e:
   assert reason.lower() in str(e).lower(),(name,'wrong rejection',str(e),reason)
   results.append({'case':name,'rejection':str(e),'packaging_rehashed':True})
  else:raise AssertionError('Mutation escaped: '+name)
 restored=validate(ROOT)
 # A formatting-only positive for the independent Markdown parser; release byte
 # reproducibility remains a separate stricter complete-package check.
 md=(ROOT/'paper.md').read_text();assert mdblocks(md)==mdblocks(md.replace('\n\n','\n\n\n'))
 build.run(ROOT,check=True)
print(json.dumps({'status':'PASS','baseline':baseline,'rejected_mutations':len(results),'negative_cases':results,'positives':['unchanged complete package','restored complete package','deterministic offline rebuild','Markdown blank-line variation (independent text-parser scope)']},ensure_ascii=False,indent=2))
