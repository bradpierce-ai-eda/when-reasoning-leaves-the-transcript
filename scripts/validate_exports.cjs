const fs=require('fs'),path=require('path'),assert=require('assert');
const {Cite}=require('@citation-js/core');require('@citation-js/plugin-bibtex');require('@citation-js/plugin-csl');require('@citation-js/plugin-ris');
const root=path.resolve(process.argv[2]||path.join(__dirname,'..'));
const data=JSON.parse(fs.readFileSync(path.join(root,'bibliography.json'),'utf8'));
const name=a=>a.literal||[a.given,a['non-dropping-particle'],a.family].filter(Boolean).join(' ');
const norm=s=>(s||'').normalize('NFC');
let assertions=0,workFieldAssertions=0;
const eq=(a,b,label,field=false)=>{assert.deepStrictEqual(a,b,label);assertions++;if(field)workFieldAssertions++;};
for(const file of ['references.bib','references.csl.json','references.ris']){
 const parsed=new Cite(fs.readFileSync(path.join(root,file),'utf8')).data;
 eq(parsed.length,data.works.length,file+' count');
 eq(parsed.map(r=>r.id),data.works.map(w=>w.citekey),file+' ordered IDs');
 for(let i=0;i<parsed.length;i++){
  const r=parsed[i],w=data.works[i],label=file+' '+w.id;
  eq(norm(r.title),norm(w.title),label+' title',true);
  eq(r.URL,w.url,label+' opaque URL',true);
  eq(r.DOI||null,w.doi||null,label+' opaque DOI',true);
  eq(r.author.map(name).map(norm),w.authors.map(name).map(norm),label+' complete authors',true);
  eq(r.issued?.['date-parts']?.[0]||null,w.issued?.date_parts||null,label+' actual full date precision',true);
  eq(r.publisher,w.publisher,label+' publisher',true);
  eq(r['container-title']||null,w.container_title||null,label+' no invented journal',true);
  eq(r.page||null,w.pages||null,label+' no invented pages',true);
 }
}
const paper=JSON.parse(fs.readFileSync(path.join(root,'metadata.json'),'utf8'));
for(const file of ['citation.bib','citation.csl.json','citation.ris']){
 const own=new Cite(fs.readFileSync(path.join(root,file),'utf8')).data;
 eq(own.length,1,file+' single publication');const r=own[0];
 eq(r.title,paper.title,file+' primary publication title');eq(r.DOI,paper.doi,file+' edition DOI');
 eq(r.issued['date-parts'][0],[2026,10,15],file+' publication date');eq(r.URL,'https://doi.org/'+paper.doi,file+' DOI citation URL');
 eq(r.author.map(name),['Brad Pierce'],file+' sole author');eq(r.publisher,'Zenodo',file+' publisher');
}
console.log(JSON.stringify({status:'PASS',processor:'Citation.js0.9.0',reference_formats:3,works:data.works.length,actual_work_field_assertions:workFieldAssertions,actual_total_assertions:assertions,paper_citation_formats:3}));
