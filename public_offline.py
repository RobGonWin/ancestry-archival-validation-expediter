"""Deterministic, field-allowlisted NEA projection and reviewed delivery contract.

No network requests, Git merges, credentials, private source hashes or media copies.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import io
import ipaddress
import importlib.util
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import unquote, urlsplit, parse_qsl

SCHEMA = 'nea.public-projection.v1'
GENERATOR = '1.0.0'
FIELDS = ['person_id','display_name','fellowship_or_group','fellowship_year','person_role',
    'population_category','cutoff_date','birth_evidence','death_evidence','age_evidence_precision',
    'attained_age_or_bound','exact_lifespan_days','possible_rank_min','possible_rank_max',
    'display_order','evidence_status','assumptions_and_limits','source_ids','public_source_urls',
    'source_publication_date','last_reviewed_at','review_status','public_image_url','image_credit',
    'rights_status','unresolved_reason','age_lower_years','age_lower_days','age_upper_years',
    'age_upper_days','upper_exclusive','evidence_classification','source_quality']
SOURCE_FIELDS=['source_id','public_source_url','source_publication_date','retrieval_date','link_status','rights_status']
UNRESOLVED_FIELDS=['award_id','display_name','public_source_url','unresolved_reason','review_status']
FORBIDDEN = re.compile(r'(?i)(?:(?<![a-z])[a-z]:[\\/]|file://|(?:^|[\\/])\.git(?:[\\/]|$)|'
    r'SHA-?256(?: prefix)?[ :]+[a-f0-9]{8,}|local-vault|private_archive|\.loop/|ancestrydna|genotype|haplotype|haplogroup|'
    r'private_identity|raw_dna|\.ged(?:com)?\b|'
    r'gh[pousr]_[a-z0-9]{20,}|github_pat_|sk-[a-z0-9]{20,}|'
    r'\brs\d{3,}\b|-----BEGIN .*PRIVATE KEY|EXA_API_KEY\s*[:=]\s*\S+)')
AUTH_KEYS = {'token','access_token','auth','authorization','key','api_key','signature','session','sessionid','jwt','code'}
PRIVATE_HOSTS = {'ancestry.com','familysearch.org','myheritage.com','23andme.com','localhost'}

def canonical(value):
    """Return stable UTF-8 bytes with sorted keys and a single trailing newline."""
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':'))+'\n').encode('utf-8')

def sha(value):
    return hashlib.sha256(value).hexdigest()

def assert_public_text(value):
    """Reject unsafe content recursively; never log the offending value."""
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value,str) else value
    for _ in range(3):
        text=unquote(text)
        if FORBIDDEN.search(text):
            raise ValueError('Sensitive or local content detected in projection')

def public_url(url):
    """Accept source links only, excluding credentials and authenticated providers."""
    assert_public_text(url)
    parsed=urlsplit(url)
    host=(parsed.hostname or '').lower()
    if parsed.scheme not in {'https','http'} or not host or parsed.username or parsed.password:
        raise ValueError('Invalid public source URL')
    if host in PRIVATE_HOSTS or any(host.endswith('.'+h) for h in PRIVATE_HOSTS):
        raise ValueError('Authenticated provider is not eligible')
    if host in {'127.0.0.1','0.0.0.0','::1'} or host.endswith('.local') or host in {'github.com','raw.githubusercontent.com'}:
        raise ValueError('Local or repository evidence URL is not a public original source')
    try:
        address=ipaddress.ip_address(host)
    except ValueError:
        address=None
    if address is not None or '.' not in host or host.endswith(('.internal','.corp','.lan','.localhost')):
        raise ValueError('Internal or IP-literal sources are not eligible')
    if any(k.lower() in AUTH_KEYS or k.lower().startswith('x-amz-') for k,_ in parse_qsl(parsed.query)+parse_qsl(parsed.fragment)):
        raise ValueError('Authenticated source URL is not eligible')
    return url

def source_id(url):
    return 'source-'+sha(url.encode())[:20]

def ranks(envelopes):
    """Replay the existing NEA competition-rank envelope rules without rounding."""
    result=[]
    for i,subject in enumerate(envelopes):
        lower,upper=subject['lower'],subject['upper']
        others=[v for j,v in enumerate(envelopes) if i!=j]
        best=1+sum(upper is not None and (tuple(v['lower'])>tuple(upper) or
            (tuple(v['lower'])==tuple(upper) and subject['upper_exclusive'])) for v in others)
        worst=1+sum(v['upper'] is None or tuple(v['upper'])>tuple(lower) for v in others)
        result.append((best,worst))
    return result

def csv_bytes(rows, fields):
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n',extrasaction='raise')
    writer.writeheader()
    for row in rows:
        # CSV formula injection is rejected rather than changing evidence text.
        if any(isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) for v in row.values()):
            raise ValueError('Spreadsheet formula injection')
        writer.writerow(row)
    return stream.getvalue().encode('utf-8')

def validate_payload(folder):
    """Recheck public CSV/JSON/rank parity and inspect all XLSX XML metadata."""
    projection=json.loads((folder/'nea-public-projection.json').read_text(encoding='utf-8'))
    if projection.get('schema_version')!=SCHEMA or projection['record_count']!=len(projection['people']):
        raise ValueError('Invalid projection schema or record count')
    rows=projection['people']
    if len({r['person_id'] for r in rows})!=len(rows): raise ValueError('Duplicate projection IDs')
    for row in rows:
        if set(row)!=set(FIELDS): raise ValueError('Unexpected public row fields')
        for url in row['public_source_urls'].split('; '): public_url(url)
    envelopes=[dict(lower=[r['age_lower_years'],r['age_lower_days']],
        upper=None if r['age_upper_years'] is None else [r['age_upper_years'],r['age_upper_days']],
        upper_exclusive=r['upper_exclusive']) for r in rows]
    if ranks(envelopes)!=[(r['possible_rank_min'],r['possible_rank_max']) for r in rows]:
        raise ValueError('Public rank replay mismatch')
    expected={
        'nea-longevity-comparison.csv':csv_bytes(rows,FIELDS),
        'nea-named-fellows.csv':csv_bytes([r for r in rows if r['person_role']=='named_fellow'],FIELDS),
        'nea-source-index.csv':csv_bytes(projection['sources'],SOURCE_FIELDS),
        'nea-unresolved-collectives.csv':csv_bytes(projection['unresolved_collectives'],UNRESOLVED_FIELDS)}
    for name,content in expected.items():
        if (folder/name).read_bytes()!=content: raise ValueError('CSV/JSON parity mismatch')
    workbook=folder/'nea-longevity-research-workbook.xlsx'
    if not workbook.is_file(): raise ValueError('Research workbook missing')
    with zipfile.ZipFile(workbook) as archive:
        for name in archive.namelist():
            if any(part in name.lower() for part in ['xl/media/','embeddings/','vbaproject','externallinks/','customxml/']):
                raise ValueError('Embedded media, macros and external-workbook payloads are not authorized')
            if name.lower().endswith(('.xml','.rels')):
                assert_public_text(archive.read(name).decode('utf-8'))
        ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        shared=ET.fromstring(archive.read('xl/sharedStrings.xml'))
        strings=[''.join(el.itertext()) for el in shared]
        root=ET.fromstring(archive.read('xl/workbook.xml'))
        rels=ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets={el.attrib['Id']:el.attrib['Target'] for el in rels}
        sheets={el.attrib['name']:el.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'] for el in root.find('m:sheets',ns)}
        for title,source_rows in [('All Identified Subjects',rows),('Named Fellows',[r for r in rows if r['person_role']=='named_fellow'])]:
            target=targets[sheets[title]]
            xml=ET.fromstring(archive.read(target.lstrip('/') if target.startswith('/') else 'xl/'+target))
            actual=[]
            for record in xml.findall('m:sheetData/m:row',ns):
                values={}
                for cell in record.findall('m:c',ns):
                    col=re.match(r'[A-Z]+',cell.attrib['r']).group();index=0
                    for letter in col: index=index*26+ord(letter)-64
                    value=cell.find('m:v',ns);raw=value.text if value is not None else ''
                    kind=cell.attrib.get('t')
                    if kind=='s': raw=strings[int(raw)]
                    elif kind=='inlineStr':raw=''.join(cell.find('m:is',ns).itertext())
                    elif kind=='b':raw=raw=='1'
                    elif kind=='d': raw=date.fromisoformat(raw[:10]).isoformat()
                    elif raw and kind not in {'str','e'}:
                        number=float(raw);raw=int(number) if number.is_integer() else number
                    values[index-1]=raw
                actual.append([values.get(i,'') for i in range(len(FIELDS))])
            if actual[0]!=FIELDS or len(actual)!=len(source_rows)+1: raise ValueError('Workbook row/header parity mismatch')
            for actual_row,expected_row in zip(actual[1:],source_rows):
                for i,key in enumerate(FIELDS):
                    value=actual_row[i]
                    if key=='cutoff_date' and isinstance(value,(int,float)):
                        value=(date(1899,12,30)+timedelta(days=value)).isoformat()
                    if value!=(expected_row[key] if expected_row[key] is not None else ''):
                        raise ValueError('Workbook cell parity mismatch')
    return {'csv_json_parity':True,'spreadsheet_csv_parity':True,'public_xml_metadata_scan':True,'rank_replay':True,'record_count':len(rows)}


def validate(folder):
    result=validate_payload(folder)
    projection=json.loads((folder/'nea-public-projection.json').read_text(encoding='utf-8'))
    assert_public_text(projection)
    rows=projection['people'];counts=projection['counts']
    if counts['identified_subjects']!=len(rows) or counts['named_fellows']!=sum(r['person_role']=='named_fellow' for r in rows):
        raise ValueError('Population counts disagree')
    if counts['open_collective_boundaries']!=len(projection['unresolved_collectives']) or not (counts['fully_resolved_awards']<=counts['resolved_including_conditional_screen']<=counts['inventoried_awards']==counts['official_awards']):
        raise ValueError('Award reconciliation counts disagree')
    if counts['resolved_including_conditional_screen']+counts['open_collective_boundaries']!=counts['official_awards']:
        raise ValueError('Award closure counts disagree')
    for r in rows:
        if r['age_evidence_precision']=='exact_date_completed_lifespan':
            start=date.fromisoformat(r['birth_evidence']);end=date.fromisoformat(r['death_evidence'])
            years=end.year-start.year
            anniversary=date(end.year,start.month,min(start.day,calendar.monthrange(end.year,start.month)[1]))
            if anniversary>end:
                years-=1;anniversary=date(end.year-1,start.month,min(start.day,calendar.monthrange(end.year-1,start.month)[1]))
            envelope=(years,(end-anniversary).days)
            if (end-start).days!=r['exact_lifespan_days'] or end<start or end.isoformat()>projection['research_cutoff'] or envelope!=(r['age_lower_years'],r['age_lower_days']) or envelope!=(r['age_upper_years'],r['age_upper_days']) or r['upper_exclusive']:
                raise ValueError('Exact lifespan does not replay')
        elif r['exact_lifespan_days'] is not None:
            raise ValueError('A bound is not an exact lifespan')
    receipt=json.loads((folder/'publication-receipt.json').read_text(encoding='utf-8'))
    required={'nea-longevity-comparison.csv','nea-named-fellows.csv','nea-source-index.csv','nea-unresolved-collectives.csv','nea-public-projection.json','nea-longevity-research-workbook.xlsx'}
    if set(receipt.get('output_sha256',{}))!=required:raise ValueError('Complete six-artifact checksum set required')
    assert_public_text(receipt)
    for name,digest in receipt['output_sha256'].items():
        if Path(name).name!=name or sha((folder/name).read_bytes())!=digest:raise ValueError('Publication hash mismatch')
    if receipt['record_count']!=len(rows) or receipt['award_count']!=counts['official_awards']:raise ValueError('Receipt counts disagree')
    result['counts']=counts
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data',type=Path,default=Path('data/public'))
    print(json.dumps(validate(parser.parse_args().data)))
