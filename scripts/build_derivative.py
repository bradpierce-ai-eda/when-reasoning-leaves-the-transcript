#!/usr/bin/env python3
"""Offline deterministic representations of the frozen Zenodo essay."""
from pathlib import Path
import argparse,hashlib,html,json,re,sys
sys.dont_write_bytecode=True
import yaml
import export_bibliography
SLUG='when-reasoning-leaves-the-transcript';PDF=SLUG+'.pdf';URL='https://bradpierce.ai/'+SLUG+'/'
def dump(o):return json.dumps(o,ensure_ascii=False,indent=2)+'\n'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def outputs(root):
 p=json.loads((root/'source/paper.json').read_text());inv=json.loads((root/'source/invariants.json').read_text());e=lambda s:html.escape(s,quote=True)
 doi=p['doi'];du='https://doi.org/'+doi;z=p['zenodo_record'];citation=f"Pierce, Brad. (2026). {p['title']}. Zenodo. {du}"
 meta={k:p[k] for k in ['title','subtitle','abstract','keywords','license','relevance_and_citation_scope']}
 meta.update(authors=[{'name':'Brad Pierce','given':'Brad','family':'Pierce','orcid':p['orcid']}],publication_date=p['date'],doi=doi,concept_doi=p['concept_doi'],zenodo_record=z,url=URL,pdf_url=URL+PDF,resource_type='Preprint',preferred_citation=citation,publication_of_record=du)
 schema={'@context':'https://schema.org','@type':'ScholarlyArticle','headline':p['title'],'alternativeHeadline':p['subtitle'],'author':[{'@type':'Person','name':'Brad Pierce','sameAs':'https://orcid.org/'+p['orcid']}],'datePublished':p['date'],'identifier':du,'sameAs':[z,du],'url':URL,'abstract':p['abstract'],'keywords':p['keywords'],'license':'https://creativecommons.org/licenses/by-nc/4.0/','inLanguage':'en','encoding':{'@type':'MediaObject','contentUrl':URL+PDF,'encodingFormat':'application/pdf'}}
 tags={'citation_title':p['title'],'citation_author':'Brad Pierce','citation_publication_date':p['date'].replace('-','/'),'citation_doi':doi,'citation_pdf_url':URL+PDF,'citation_fulltext_html_url':URL,'description':p['abstract'],'keywords':', '.join(p['keywords']),'robots':'index, follow','og:title':p['title'],'og:description':p['abstract'],'og:type':'article','og:url':URL}
 head='\n'.join(f'<meta {"property" if k.startswith("og:") else "name"}="{k}" content="{e(v)}">' for k,v in tags.items())
 head+='\n'+ '\n'.join(f'<meta name="DC.subject" content="{e(k)}">' for k in p['keywords'])
 scope='\n\n'.join(p['relevance_and_citation_scope']);scopehtml='<aside id="relevance-and-citation-scope" data-repository-added="true"><h2>Relevance and citation scope</h2>'+''.join('<p>'+e(t)+'</p>' for t in p['relevance_and_citation_scope'])+'</aside>'
 citationhtml=e(citation).replace(e(du),'<a href="'+du+'">'+du+'</a>')
 resources='<nav id="repository-resources" data-repository-added="true" aria-label="Publication and citation formats"><p><strong>Preferred citation:</strong> '+citationhtml+'</p><p><a href="'+PDF+'">Published PDF</a> · <a href="paper.md">Full Markdown</a> · <a href="'+z+'">Zenodo record</a> · <a href="citation.bib">Paper BibTeX</a> · <a href="citation.csl.json">Paper CSL JSON</a> · <a href="citation.ris">Paper RIS</a> · <a href="CITATION.cff">CITATION.cff</a></p><p>Source bibliography: <a href="references.md">Published references</a> · <a href="references.bib">BibTeX</a> · <a href="references.csl.json">CSL JSON</a> · <a href="references.ris">RIS</a> · <a href="bibliography.json">Normalized data</a></p></nav>'
 page=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(p['title'])}</title>
{head}
<link rel="canonical" href="{URL}"><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False).replace('</','<\\/')}</script>
<style>body{{max-width:52rem;margin:2rem auto;padding:0 1rem;color:#171717;font-family:Georgia,serif;font-size:17px;line-height:1.55}}h1,h2,h3{{line-height:1.25}}h1{{font-size:2rem}}h2{{font-size:1.35rem;margin-top:2rem}}.subtitle{{font-size:1.2rem}}.author{{font-size:1.25rem;font-weight:bold}}.date,.doi,.keywords{{font-size:.9rem}}aside,#repository-resources{{border-left:3px solid #aaa;padding:.2rem 1rem;margin:1.5rem 0;background:#f8f8f8}}p,li{{overflow-wrap:anywhere}}.references{{list-style:none;font-size:.9rem;padding-left:1.5rem}}.references li{{text-indent:-1.5rem;margin-bottom:.8rem}}a{{color:#0645ad}}.citeref{{white-space:nowrap}}footer{{border-top:1px solid #bbb;font-size:.85rem;margin-top:2rem;padding-top:1rem}}@media(max-width:600px){{body{{font-size:16px;margin:1rem auto}}h1{{font-size:1.7rem}}}}</style></head><body>
{p['front_html']}
{scopehtml}
{resources}
<main id="canonical-paper" aria-label="Canonical publication body">{p['body_html']}</main>
<footer>© 2026 Brad Pierce · <a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</a></footer>
</body></html>
'''
 readme=f"# {p['title']}\n\n{p['subtitle']}\n\nBrad Pierce · October 15, 2026\n\n**Publication of record:** [{du}]({du}) · [Zenodo record]({z})\n\n**Preferred citation:** {citation}\n\n[Static HTML]({URL}) · [Published PDF]({PDF}) · [Full Markdown](paper.md)\n\n## Relevance and citation scope\n\n{scope}\n\n## Source bibliography\n\nThe exact published references are in [references.md](references.md). Reusable [BibTeX](references.bib), [CSL JSON](references.csl.json), and [RIS](references.ris) are generated from [bibliography.json](bibliography.json). Normalized metadata and its adjudications are separate from the unchanged publication.\n\n## Provenance\n\nThe [provenance record](provenance.json) identifies the frozen Zenodo publication and source checksums.\n\n## Canonical paper text\n\n"+p['canonical_markdown']
 author={'family-names':'Pierce','given-names':'Brad','orcid':'https://orcid.org/'+p['orcid']}
 cff={'cff-version':'1.2.0','message':'This repository is a machine-readable derivative; the DOI-linked Zenodo essay is the publication of record.','title':p['title'],'authors':[author],'doi':doi,'date-released':p['date'],'url':URL,'license':p['license'],'abstract':p['abstract'],'keywords':p['keywords'],'preferred-citation':{'type':'generic','title':p['title'],'authors':[author],'year':2026,'month':10,'date-published':p['date'],'doi':doi,'url':du,'publisher':{'name':'Zenodo'},'notes':'Preprint','keywords':list(p['keywords'])}}
 own={'id':'pierce2026reasoning','type':'manuscript','title':p['title'],'author':[{'given':'Brad','family':'Pierce'}],'issued':{'date-parts':[[2026,10,15]]},'DOI':doi,'URL':du,'publisher':'Zenodo','abstract':p['abstract'],'keyword':', '.join(p['keywords']),'note':'Preprint'}
 bib=f'@misc{{pierce2026reasoning,\n  author = {{Pierce, Brad}},\n  title = {{{{{p["title"]}}}}},\n  publisher = {{Zenodo}},\n  note = {{Preprint}},\n  year = {{2026}},\n  month = {{10}},\n  date = {{2026-10-15}},\n  doi = {{{doi}}},\n  url = {{{du}}},\n  keywords = {{{", ".join(p["keywords"])}}}\n}}\n'
 ris='TY  - UNPB\nID  - pierce2026reasoning\nAU  - Pierce, Brad\nTI  - '+p['title']+'\nPY  - 2026\nDA  - 2026/10/15\nPB  - Zenodo\nDO  - '+doi+'\nUR  - '+du+'\nAB  - '+p['abstract']+'\n'+''.join('KW  - '+k+'\n' for k in p['keywords'])+'N1  - Preprint\nER  -\n'
 provenance={'publication_of_record':du,'zenodo_record':z,'zenodo_record_revision':3,'publication_date':p['date'],'source_pdf':inv['pdf'],'canonical_text_sha256':inv['canonical_text_sha256'],'canonical_markdown_sha256':inv['canonical_markdown_sha256'],'generation_date':'2026-10-15','transformation':'The machine-readable source that produced the verified published PDF is frozen in source/paper.json. All ordered paragraphs, title emphasis, citations, disclosure, references and URL targets are conserved. Repository framing, scholarly metadata and bibliography normalization are separate. The PDF is mirrored byte-for-byte.','manual_canonical_text_corrections':[],'validation_status':'Validation is reproducible through the packaged complete-text, metadata, bibliography, immutable-PDF and mutation checks. Exact release results are preserved in the canonical working records.','tools':{'PDF inspection':'pypdf 6.10.0','HTML inspection':'Beautiful Soup 4.15.0','Markdown parsing':'markdown-it-py 4.0.0','bibliography interoperability':'BibTeX 0.99e (TeX Live 2026) and Citation.js 0.9.0'},'source_reference_slots':15,'normalized_works':15,'figures':0,'tables':0,'retrieval_history':'Authority retrieval history is preserved in private working records. Public field provenance identifies responsible publication registries; no reader access dates are added.'}
 sitemap='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join('<url><loc>'+u+'</loc></url>\n' for u in [URL,URL+PDF])+'</urlset>\n'
 return {'index.html':page,'README.md':readme,'paper.md':p['canonical_markdown'],'metadata.json':dump(meta),'CITATION.cff':yaml.safe_dump(cff,allow_unicode=True,sort_keys=False),'citation.bib':bib,'citation.csl.json':dump([own]),'citation.ris':ris,'provenance.json':dump(provenance),'sitemap.xml':sitemap,'robots.txt':'User-agent: *\nAllow: /\nSitemap: '+URL+'sitemap.xml\n','LICENSE.md':'© 2026 Brad Pierce\n\nThis essay and its derivative representations are licensed under Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0).\n\nhttps://creativecommons.org/licenses/by-nc/4.0/\n\nThird-party works referenced in the bibliography retain their respective rights.\n',**export_bibliography.expected_outputs(export_bibliography.load_dataset(root))}
def public_files(root):return sorted(p for p in root.rglob('*') if p.is_file() and not any(v in {'.git','__pycache__','.venv','node_modules'} for v in p.relative_to(root).parts) and p.suffix!='.pyc' and p.name!='checksums.sha256')
def manifest(root):return ''.join(digest(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in public_files(root))
def run(root,check=False):
 for name,text in outputs(root).items():
  if check:assert (root/name).read_text()==text,'Generated drift: '+name
  else:(root/name).write_text(text)
 if check:assert (root/'checksums.sha256').read_text()==manifest(root),'Manifest path/byte drift'
 else:(root/'checksums.sha256').write_text(manifest(root))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);a.add_argument('--check',action='store_true');o=a.parse_args();run(o.repo.resolve(),o.check);print('PASS: deterministic build'+(' check' if o.check else ''))
