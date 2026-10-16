#!/usr/bin/env python3
"""Validate actual files against the frozen published edition and representation contract."""
from pathlib import Path
import argparse,hashlib,json,re,unicodedata,sys,xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
from bs4 import BeautifulSoup,Comment
from markdown_it import MarkdownIt
from pypdf import PdfReader
import yaml
import build_derivative as build
PDF_HASH='8dc68083df17ae51a7b6b8a2ab877bc7fd0814416bf33b5f15eb8142a9353fc8'
FROZEN={"source/invariants.json":"980eda71d5dc09bdf66e39b0d071894dda23fcb13b4a80d5aa54712254ed86d6",'source/paper.json':'529650925e2e6b681bb9670d4fabe153767b7c86fb05486035bf7474b57944ba','bibliography.json':'f6417b5b4575c8019e0046fa160ed898f48e8672cec20a9deb8df603921287a9','source/zenodo-record.json':'2031c00f1f7391185d7cd47e7450ee64ef0b91adf8e329c440e3d84c593e00ab'}
EXPECTED_FILES={'README.md','index.html','paper.md','when-reasoning-leaves-the-transcript.pdf','CITATION.cff','citation.bib','citation.csl.json','citation.ris','metadata.json','provenance.json','sitemap.xml','robots.txt','LICENSE.md','bibliography.json','references.md','references.bib','references.csl.json','references.ris','source/paper.json','source/invariants.json','source/zenodo-record.json','scripts/build_derivative.py','scripts/export_bibliography.py','scripts/validate_derivative.py','scripts/test_regressions.py','scripts/validate_exports.cjs','requirements.txt','package.json','package-lock.json','checksums.sha256'}
def require(ok,msg):
 if not ok:raise AssertionError(msg)
def norm(s):return ' '.join(unicodedata.normalize('NFC',s).replace('\u2060','').split())
def unique(pairs):
 d={}
 for k,v in pairs:require(k not in d,'Duplicate structured key: '+str(k));d[k]=v
 return d
def load(path):return json.loads(path.read_text(),object_pairs_hook=unique)
class YAML(yaml.SafeLoader):pass
def mapping(loader,node,deep=False):return unique([(loader.construct_object(k,deep=deep),loader.construct_object(v,deep=deep)) for k,v in node.value])
YAML.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)
def blocks(soup):
 nodes=soup.select('h1,h2,h3,h4,h5,h6,p,li');selected={id(n) for n in nodes};out=[]
 for n in nodes:
  require(not any(id(p) in selected for p in n.parents),'Nested canonical block')
  require(not n.has_attr('hidden') and not n.get('aria-hidden')=='true','Hidden canonical block')
  require(not re.search(r'display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0(?:\D|$)',n.get('style',''),re.I),'Hidden canonical style')
  out.append(norm(n.get_text()))
 for s in soup.find_all(string=True):
  if not isinstance(s,Comment) and norm(str(s)):require(any(id(p) in selected for p in s.parents),'Unaccounted canonical text')
 return out
def mdblocks(text):return blocks(BeautifulSoup(MarkdownIt('commonmark').render(text),'html.parser'))
def check_json(root):
 for f in root.rglob('*.json'):
  if '.git' not in f.parts and 'node_modules' not in f.parts:load(f)
def validate(root):
 check_json(root)
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts}
 require(actual==EXPECTED_FILES,'Exact intended public path set: '+str(actual^EXPECTED_FILES))
 require(all((root/name).stat().st_mode & 0o111 == 0 for name in actual),'Exact intended public file modes')
 require(all(not p.is_symlink() for p in root.rglob('*') if '.git' not in p.parts),'Unexpected public symlink')
 for name,digest in FROZEN.items():require(build.digest(root/name)==digest,'Frozen authority changed: '+name)
 p=load(root/'source/paper.json');inv=load(root/'source/invariants.json');meta=load(root/'metadata.json');data=load(root/'bibliography.json');z=load(root/'source/zenodo-record.json')
 expected=[norm(b['text']) for b in p['canonical_blocks']];require(len(expected)==len(set(b['id'] for b in p['canonical_blocks']))==98,'Canonical block identity/count')
 for field,value in [('canonical_text',inv['canonical_text_sha256']),('canonical_markdown',inv['canonical_markdown_sha256']),('front_html',inv['front_html_sha256']),('body_html',inv['body_html_sha256'])]:require(hashlib.sha256(p[field].encode()).hexdigest()==value,'Frozen content hash: '+field)
 require(inv['paper_source_sha256']==FROZEN['source/paper.json'] and inv['bibliography_sha256']==FROZEN['bibliography.json'] and inv['zenodo_source_sha256']==FROZEN['source/zenodo-record.json'],'Invariant authority bindings')
 require(mdblocks((root/'paper.md').read_text())==expected,'Complete Markdown text mismatch')
 readme=(root/'README.md').read_text();marker='## Canonical paper text\n\n';require(readme.count(marker)==1,'Unique README manuscript partition')
 prefix,manuscript=readme.split(marker);require(mdblocks(manuscript)==expected,'Complete README manuscript mismatch')
 soup=BeautifulSoup((root/'index.html').read_text(),'html.parser');front=soup.select('#scholarly-front-matter');main=soup.select('#canonical-paper');scope=soup.select('#relevance-and-citation-scope');resources=soup.select('#repository-resources')
 require(len(front)==len(main)==len(scope)==len(resources)==1,'Unique HTML partitions')
 require(blocks(BeautifulSoup(str(front[0])+str(main[0]),'html.parser'))==expected,'Complete HTML manuscript mismatch')
 require([n.get_text() for n in scope[0].select('p')]==p['relevance_and_citation_scope'],'Synchronized HTML scope')
 require(prefix.count('## Relevance and citation scope')==1 and '\n\n'.join(p['relevance_and_citation_scope']) in prefix,'Synchronized README scope')
 rendered=str(soup.body);require(rendered.index('id="scholarly-front-matter"')<rendered.index('id="relevance-and-citation-scope"')<rendered.index('id="canonical-paper"'),'HTML article order')
 require(front[0].select_one('h1').get_text()==p['title'] and front[0].select_one('.subtitle').get_text()==p['subtitle'],'Visible title/subtitle')
 require(front[0].select_one('.author').get_text()=='Brad Pierce' and front[0].select_one('.date').get_text()=='October 15, 2026','Visible author/date')
 require(front[0].select_one('.doi a')['href']==front[0].select_one('.doi a').get_text()=='https://doi.org/'+p['doi'],'Visible DOI identity')
 require(norm(front[0].select_one('.abstract p').get_text())==norm(p['abstract']),'Full visible abstract')
 require(front[0].select_one('.keywords').get_text()=='Keywords: '+', '.join(p['keywords']),'Visible keyword vector')
 require(str(front[0]).index('class="abstract"')<str(front[0]).index('class="keywords"'),'Abstract before keywords')
 for part in [front[0],main[0]]:
  for a in part.select('a[href^="https://"]'):require(a.get_text()==a['href'],'Displayed URL target mismatch')
  require(not part.select('em a,a em'),'Paper title hyperlink')
 for title in p['title_spans']:
  node=front[0].select_one('#'+title['block_id']) or main[0].select_one('#'+title['block_id']);require(node is not None and title['text'] in [e.get_text() for e in node.select('em')],'Published title emphasis')
 headings=[n.get_text() for n in main[0].select('h2')];require(headings[-2:]==[p['disclosure_heading'],'References'],'Disclosure before References')
 ds=main[0].find('h2',string=p['disclosure_heading']);require(ds.find_next_sibling('p').get_text()==p['disclosure'] and ds.find_next_sibling('p').find_next_sibling().get_text()=='References','Exact disclosure and placement')
 tags={'citation_title':p['title'],'citation_author':'Brad Pierce','citation_publication_date':'2026/10/15','citation_doi':p['doi'],'citation_pdf_url':build.URL+build.PDF,'citation_fulltext_html_url':build.URL,'description':p['abstract'],'keywords':', '.join(p['keywords']),'robots':'index, follow'}
 for key,value in tags.items():require([n.get('content') for n in soup.select('meta[name="'+key+'"]')]==[value],'Metadata '+key)
 require([n.get('content') for n in soup.select('meta[name="DC.subject"]')]==p['keywords'],'Dublin Core keyword vector')
 for key,value in [('og:title',p['title']),('og:description',p['abstract']),('og:url',build.URL),('og:type','article')]:require([n.get('content') for n in soup.select('meta[property="'+key+'"]')]==[value],'Metadata '+key)
 require(soup.title.get_text()==p['title'] and [n['href'] for n in soup.select('link[rel="canonical"]')]==[build.URL],'Browser title / self-canonical')
 require(len(soup.select('script[type="application/ld+json"]'))==1 and not soup.select('script[src]'),'One static scholarly schema; no script dependency')
 schema=json.loads(soup.select_one('script[type="application/ld+json"]').string,object_pairs_hook=unique)
 require(schema['@type']=='ScholarlyArticle' and schema['headline']==p['title'] and schema['alternativeHeadline']==p['subtitle'] and schema['abstract']==p['abstract'],'Schema textual fields')
 require(schema['author']==[{'@type':'Person','name':'Brad Pierce','sameAs':'https://orcid.org/'+p['orcid']}],'Schema sole author')
 require(schema['datePublished']==p['date']=='2026-10-15' and schema['identifier']=='https://doi.org/'+p['doi'] and schema['url']==build.URL and schema['encoding']=={'@type':'MediaObject','contentUrl':build.URL+build.PDF,'encodingFormat':'application/pdf'},'Schema date and locators')
 require(schema['sameAs']==[p['zenodo_record'],'https://doi.org/'+p['doi']] and schema['keywords']==p['keywords'] and schema['license']=='https://creativecommons.org/licenses/by-nc/4.0/','Schema DOI linkage, keywords, license')
 require(meta['title']==p['title'] and meta['subtitle']==p['subtitle'] and meta['abstract']==p['abstract'] and meta['keywords']==p['keywords'] and meta['resource_type']=='Preprint','Structured metadata content')
 require(meta['authors']==[{'name':'Brad Pierce','given':'Brad','family':'Pierce','orcid':p['orcid']}] and meta['publication_date']==p['date'] and meta['doi']==p['doi'] and meta['concept_doi']==p['concept_doi'],'Structured author/date/DOI metadata')
 require(meta['url']==build.URL and meta['pdf_url']==build.URL+build.PDF and meta['publication_of_record']=='https://doi.org/'+p['doi'] and meta['zenodo_record']==p['zenodo_record'],'Structured locators')
 require(z['id']=='23401563' and z['is_published'] and not z['is_draft'] and z['metadata']['title']==p['title'] and z['metadata']['publication_date']==p['date'],'Frozen published record')
 require([s['subject'] for s in z['metadata']['subjects'] if not s.get('scheme')]==p['keywords'],'Published keyword vector')
 cff=yaml.load((root/'CITATION.cff').read_text(),Loader=YAML);person={'family-names':'Pierce','given-names':'Brad','orcid':'https://orcid.org/'+p['orcid']}
 require(cff['authors']==[person] and cff['title']==p['title'] and cff['keywords']==p['keywords'] and cff['abstract']==p['abstract'] and cff['doi']==p['doi'] and str(cff['date-released'])==p['date'],'CFF actual field values')
 pref=cff['preferred-citation'];require(pref.get('keywords')==p['keywords'],'CFF preferred keyword vector');require(pref['authors']==[person] and pref['title']==p['title'] and pref['doi']==p['doi'] and str(pref['date-published'])==p['date'] and pref['url']=='https://doi.org/'+p['doi'] and pref['publisher']=={'name':'Zenodo'},'CFF preferred publication citation')
 require(cff['license']==meta['license']==p['license']=='CC-BY-NC-4.0','License consistency')
 refs=main[0].select('li[id^="ref-"]');require(len(refs)==15 and len(data['works'])==15,'15 reference slots and works')
 for n,(node,slot) in enumerate(zip(refs,data['reference_slots']),1):
  require(node.get_text()==slot['raw_reference'] and node['id']=='ref-'+str(n) and slot['number']==n,'Exact reference sequence '+str(n))
  require(hashlib.sha256(slot['raw_reference'].encode()).hexdigest()==slot['raw_reference_sha256'],'Exact published reference hash')
  require([a['href'] for a in node.select('a')]==slot['published_urls'],'Reference URL binding '+str(n))
 refmd=BeautifulSoup(MarkdownIt('commonmark').render((root/'references.md').read_text()),'html.parser');require([n.get_text() for n in refmd.select('p') if re.match(r'^\[\d+\]',n.get_text())]==[s['raw_reference'] for s in data['reference_slots']],'Published references Markdown')
 anchors=main[0].select('a.citeref');require(len(anchors)==22,'Citation destination count')
 for a in anchors:require(a['href']=='#ref-'+a.get_text()[1:-1],'Specific numbered citation destination')
 ids=[n['id'] for n in soup.select('[id]')];require(len(ids)==len(set(ids)),'Unique HTML anchors')
 for a in soup.select('a[href]'):
  h=a['href']
  if h.startswith('#'):require(h[1:] in ids,'Broken internal destination')
  elif not re.match('https?://',h):require((root/h).is_file(),'Missing public resource '+h)
 require(not soup.select('img,table,figure,iframe,form'),'Unexpected object or interaction barrier')
 require(not re.search(r'\baccessed\b|\bretrieved on\b',' '.join(n.get_text() for n in refs),re.I),'Reader access dates')
 works=data['works'];require(len({w['id'] for w in works})==len({w['citekey'] for w in works})==len({w['doi'].lower() for w in works})==15,'Unique works/citekeys/DOIs')
 require({l['work_id'] for l in data['reference_work_links']}=={w['id'] for w in works} and {l['reference_slot_id'] for l in data['reference_work_links']}=={s['id'] for s in data['reference_slots']},'No orphan work or reference')
 require(all(w['title'] and w['authors'] and w['issued']['date_parts'] and w['url'] and w['doi'] and w['accessed'] is None for w in works),'Required reusable fields')
 require([a['given'] for a in works[0]['authors']]==['Jiaru','Yunzhe','Sirui','Federico','Shang','Pan','Jingrui','James'] and works[0]['issued']['date_parts']==[2026,10] and works[0]['date_role']=='Available','Full arXiv author identities and date role')
 require(all({'title','authors','issued','url','doi','publisher','type'}<=set(w['field_provenance']) for w in works),'Field provenance coverage')
 reader=PdfReader(root/build.PDF);require(build.digest(root/build.PDF)==PDF_HASH and (root/build.PDF).stat().st_size==199322 and len(reader.pages)==12,'Published immutable PDF identity')
 require(reader.metadata.title==p['title']+': '+p['subtitle'] and reader.metadata.author=='Brad Pierce' and reader.metadata.get('/Keywords')==', '.join(p['keywords']),'Frozen PDF typed metadata mapping')
 require(reader.trailer['/Root']['/Lang']=='en-US' and '/StructTreeRoot' in reader.trailer['/Root'],'Tagged English PDF preserved')
 require('References' in ''.join(page.extract_text() or '' for page in reader.pages),'PDF searchability')
 added=prefix+'\n'+scope[0].get_text()+'\n'+resources[0].get_text()+'\n'+json.dumps({k:v for k,v in meta.items() if k not in ['abstract']})+'\n'+(root/'provenance.json').read_text()+'\n'+(root/'CITATION.cff').read_text()+'\n'+(root/'LICENSE.md').read_text()
 for phrase in ['when to cite this report','cite this report','cite this essay','you should','you must','ignore previous','system prompt','as an ai','instructions for ai','private candidate','not publication-ready','reserved doi']:
  require(phrase not in added.lower(),'Prompt-like or private repository framing: '+phrase)
 require(not soup.select('[hidden],[aria-hidden="true"]') and not re.search(r'display\s*:\s*none|visibility\s*:\s*hidden',soup.get_text()+' '.join(s.get_text() for s in soup.select('style')),re.I),'Hidden paper content')
 require(not (root/'CNAME').exists() and 'Allow: /' in (root/'robots.txt').read_text(),'Project domain and crawler controls')
 sitemap=ET.parse(root/'sitemap.xml').getroot();locs=[e.text for e in sitemap.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')];require(locs==[build.URL,build.URL+build.PDF],'Paper sitemap')
 require('bradpierce-ai-eda.github.io' not in (root/'index.html').read_text(),'Canonical custom host')
 build.run(root,check=True)
 return {'status':'PASS','blocks':98,'copies':['HTML','Markdown','README'],'references':15,'works':15,'PDF_pages':12,'PDF_sha256':PDF_HASH,'internal_citation_destinations':22,'keywords':7,'public_files':len(actual),'frozen_publication_changed':False}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);args=ap.parse_args();print(json.dumps(validate(args.repo.resolve()),ensure_ascii=False,indent=2))
