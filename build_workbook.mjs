import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const candidate=path.resolve(process.argv[2]);
const previewDir=path.resolve(process.argv[3]);
const d=JSON.parse(await fs.readFile(path.join(candidate,'nea-public-projection.json'),'utf8'));
const wb=Workbook.create();
const sheets=[];
const allFields=(await fs.readFile(path.join(candidate,'nea-longevity-comparison.csv'),'utf8')).split('\n')[0].split(',');
const matrix=(rows,fields)=>[fields,...rows.map(r=>fields.map(k=>r[k]??null))];
function table(name,rows,fields){
  const sheet=wb.worksheets.add(name);sheets.push(sheet);sheet.showGridLines=false;
  const values=matrix(rows,fields);
  sheet.getRangeByIndexes(0,0,values.length,fields.length).values=values;
  sheet.getRangeByIndexes(0,0,values.length,fields.length).format.font={name:'Arial',size:10,color:'#243344'};
  sheet.getRangeByIndexes(0,0,1,fields.length).format={fill:'#344B60',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:42,wrapText:true};
  sheet.getRangeByIndexes(1,0,Math.max(rows.length,1),fields.length).format.rowHeight=26;
  sheet.getRangeByIndexes(0,0,values.length,fields.length).format.columnWidth=24;
  sheet.getRangeByIndexes(0,0,values.length,fields.length).format.verticalAlignment='center';
  for(let i=0;i<fields.length;i++){
    if(/name|fellowship_or_group|unresolved_reason|assumptions|source_url|attained_age|age_evidence/.test(fields[i])) sheet.getRangeByIndexes(0,i,values.length,1).format.columnWidth=48;
    if(/^(person|award|source)_id$/.test(fields[i]))sheet.getRangeByIndexes(0,i,values.length,1).format.columnWidth=38;
    if(/unresolved_reason|assumptions|source_url|attained_age|age_evidence/.test(fields[i])) {
      sheet.getRangeByIndexes(1,i,Math.max(rows.length,1),1).format.wrapText=true;
      sheet.getRangeByIndexes(1,0,Math.max(rows.length,1),fields.length).format.rowHeight=52;
    }
  }
  if(rows.length){const t=sheet.tables.add(`A1:${column(fields.length)}${values.length}`,true,'Table'+sheets.length);t.style='TableStyleLight1';t.showFilterButton=true;}
  sheet.freezePanes.freezeRows(1);sheet.freezePanes.freezeColumns(Math.min(fields.length,2));
  return sheet;
}
function column(n){let s='';for(;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;}
const notes=[
 ['Project','National Heritage Fellow Longevity Archiver'],
 ['Research snapshot',d.research_cutoff],
 ['Publication state','Reviewed public research snapshot, published at the owner’s request. Evidence limits and unresolved questions remain.'],
 ['Population','All identified comparison subjects. Unknown ensemble members remain outside the population.'],
 ['Exact dates','Source-reported exact dates support calculated lifespans, not independent vital-record certification.'],
 ['Reported ages','Completed whole-year ages remain intervals. No invented birthdays.'],
 ['Screening bounds','Upper caps are not actual completed lifespans or assertions of current survival.'],
 ['Inferred screens','Keep accepted assumptions visible. Inferred birth intervals are not verified birth dates.'],
 ['Rank intervals','Conservative possible competition-rank intervals among identified subjects only.'],
 ['Display order','Presentation order is not an official or fully verified longevity ranking.'],
 ['Roma comparison','First among current identified subjects under accepted evidence and assumptions.'],
 ['Collective limits','Eight membership boundaries remain open in this checkpoint. No unconditional historical maximum.'],
 ['Dates','Research cutoff is separate from source publication date, event date and later review date. Missing dates stay blank.'],
 ['Images','No image files embedded. Source visibility is not redistribution permission.'],
 ['Private review','Family-specific evidence, private captures, source fingerprints and account data are excluded.'],
 ['Research edits','Source snapshot tables are editable. Recompute rankings and regenerate before publication after any research change.'],
 ['Review decisions','Use Research Review Queue for new decisions. A checked cell alone does not authorize publication.'],
 ['Independence','Independent source-bound archival comparison. No institutional endorsement is asserted.'],
 ['Sheet names','Unresolved Collective Memberships is shortened to Unresolved Collectives to fit Excel’s 31-character limit.'],
 ['Regeneration','python nea_publication.py --source <reviewed-source> --out <empty-directory> --producer-commit <revision>']
];
const readme=table('Read Me - Methodology',notes.map(([field,definition])=>({field,definition})),['field','definition']);
readme.getRange('B1:B21').format.columnWidth=112;
readme.getRange('B2:B21').format.wrapText=true;readme.getRange('A2:B21').format.rowHeight=42;
const all=table('All Identified Subjects',d.people,allFields);
const named=table('Named Fellows',d.people.filter(r=>r.person_role==='named_fellow'),allFields);
const leadingFields=['display_name','fellowship_year','age_evidence_precision','attained_age_or_bound','possible_rank_min','possible_rank_max','evidence_status','assumptions_and_limits','public_source_urls'];
table('Leading Candidates',d.people.filter(r=>r.possible_rank_min<=10||['Ethel Kvalheim','Ella Jenkins'].includes(r.display_name)),leadingFields);
table('Unresolved Collectives',d.unresolved_collectives,['award_id','display_name','public_source_url','review_status','unresolved_reason']);
const sources=table('Source Register',d.sources,['source_id','public_source_url','source_publication_date','retrieval_date','link_status','rights_status']);
const reviews=d.people.map(r=>({person_id:r.person_id,display_name:r.display_name,evidence_classification:r.evidence_classification,
  review_reason:r.unresolved_reason||'Optional follow-up research; retain all evidence limitations.',review_decision:'pending',reviewed_at:null,reviewer:null}));
const queue=table('Research Review Queue',reviews,Object.keys(reviews[0]));
queue.getRange(`E2:E${reviews.length+1}`).dataValidation={rule:{type:'list',values:['pending','approved','rejected','conflict']}};
queue.getRange(`E2:G${reviews.length+1}`).format.fill='#FFF3CD';
const validations=Object.entries(d.counts).map(([check,actual])=>({check,actual,status:'Recomputed from canonical source',notes:''}));
for(const [check,status,notes] of [
 ['Human publication review','Owner authorization recorded','See the hash-bound authorization. Personal cell-by-cell human review is not claimed.'],
 ['Public links revalidated','Status in Source Register','Liveness checks do not verify historical claims. Unavailable, restricted and unchecked links remain explicit.'],
 ['Image rights review','Source links only','No source image bytes are published. Unknown redistribution rights remain unknown.'],
 ['Independent sample review','External review receipt','See the publication review record for reviewed profiles and limitations.'],
 ['CSV and workbook parity','Run public_offline.py','The verifier checks all33population columns and the six output hashes.'],
 ['Deterministic clean replay','Canonical packaging','Verify two independently authored outputs; compare the external replay receipt.']
])validations.push({check,actual:null,status,notes});
table('Publication Validation',validations,['check','actual','status','notes']);
for(const sheet of [all,named]){
  const idx=allFields.indexOf('cutoff_date');const n=sheet===all?d.people.length:d.people.filter(r=>r.person_role==='named_fellow').length;
  const serial=(Date.parse(d.research_cutoff+'T00:00:00Z')-Date.UTC(1899,11,30))/86400000;
  sheet.getRangeByIndexes(1,idx,n,1).values=Array.from({length:n},()=>[serial]);
  sheet.getRangeByIndexes(1,idx,n,1).setNumberFormat('yyyy-mm-dd');
}
wb.recalculate();
await fs.mkdir(previewDir,{recursive:true});
for(const s of sheets){
  const p=await wb.render({sheetName:s.name,range:s.name==='Read Me - Methodology'?'A1:B9':'A1:F7',scale:1,format:'png'});
  await fs.writeFile(path.join(previewDir,s.name.replaceAll(' ','-')+'.png'),new Uint8Array(await p.arrayBuffer()));
}
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:10},maxChars:1500});
await fs.writeFile(path.join(previewDir,'formula-scan.json'),JSON.stringify(errors));
const output=await SpreadsheetFile.exportXlsx(wb);
await output.save(path.join(candidate,'nea-longevity-research-workbook.xlsx'));
const normalization=spawnSync(process.env.PYTHON||'python',[fileURLToPath(new URL('./canonicalize_workbook.py',import.meta.url)),path.join(candidate,'nea-longevity-research-workbook.xlsx')],{encoding:'utf8'});
if(normalization.status!==0)throw Error('Workbook canonicalization failed: '+normalization.stderr);
const sidecar=path.join(candidate,'nea-longevity-research-workbook.xlsx.inspect.ndjson');
try {await fs.rename(sidecar,path.join(previewDir,'workbook.inspect.ndjson'));} catch(e) {if(e.code!=='ENOENT')throw e;}
console.log(JSON.stringify({sheets:sheets.map(s=>s.name),identifiedSubjects:d.people.length}));
