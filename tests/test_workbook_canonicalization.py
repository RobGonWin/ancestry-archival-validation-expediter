"""Only package identifiers and timestamps change; relationship targets survive."""
from pathlib import Path
import zipfile,xml.etree.ElementTree as ET
from canonicalize_workbook import canonicalize
def package(path,identity,year):
    parts={'xl/workbook.xml':f'<workbook xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheet r:id="{identity}"/></workbook>',
        'xl/_rels/workbook.xml.rels':f'<Relationships><Relationship Id="{identity}" Type="worksheet" Target="/xl/worksheets/sheet1.xml"/></Relationships>',
        'xl/worksheets/sheet1.xml':'<worksheet><value>Exact synthetic evidence</value></worksheet>'}
    with zipfile.ZipFile(path,'w') as out:
        for name,content in parts.items():out.writestr(zipfile.ZipInfo(name,(year,1,1,0,0,0)),content)
def test_canonical_package_is_deterministic_and_idempotent(tmp_path):
    a=tmp_path/'a.xlsx';b=tmp_path/'b.xlsx';package(a,'random-a',2024);package(b,'random-b',2026)
    canonicalize(a);canonicalize(b);assert a.read_bytes()==b.read_bytes()
    before=a.read_bytes();canonicalize(a);assert a.read_bytes()==before
def test_relationship_and_cell_content_are_preserved(tmp_path):
    path=tmp_path/'a.xlsx';package(path,'random-id',2026);canonicalize(path)
    with zipfile.ZipFile(path) as archive:
        root=ET.fromstring(archive.read('xl/workbook.xml'));rels=ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        identity=root[0].attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
        assert identity==rels[0].attrib['Id'] and rels[0].attrib['Target']=='/xl/worksheets/sheet1.xml'
        assert b'Exact synthetic evidence' in archive.read('xl/worksheets/sheet1.xml')
def test_alternate_relationship_prefix_is_resolved(tmp_path):
    path=tmp_path/'alias.xlsx';package(path,'random-id',2026)
    with zipfile.ZipFile(path) as archive:parts={n:archive.read(n) for n in archive.namelist()}
    parts['xl/workbook.xml']=parts['xl/workbook.xml'].replace(b'xmlns:r=',b'xmlns:rel=').replace(b'r:id=',b'rel:id=')
    with zipfile.ZipFile(path,'w') as archive:
        for name,content in parts.items():archive.writestr(name,content)
    canonicalize(path)
    with zipfile.ZipFile(path) as archive:
        owner=ET.fromstring(archive.read('xl/workbook.xml'));rels=ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        assert next(iter(owner[0].attrib.values()))==rels[0].attrib['Id']
def test_predictable_sibling_file_is_never_overwritten(tmp_path):
    path=tmp_path/'a.xlsx';package(path,'random-id',2026)
    sibling=path.with_suffix('.canonical.tmp');sibling.write_bytes(b'Unrelated file')
    canonicalize(path);assert sibling.read_bytes()==b'Unrelated file'
def test_single_quoted_relationship_id_is_rewritten(tmp_path):
    path=tmp_path/'single.xlsx';package(path,'random-id',2026)
    with zipfile.ZipFile(path) as archive:parts={n:archive.read(n) for n in archive.namelist()}
    parts['xl/_rels/workbook.xml.rels']=parts['xl/_rels/workbook.xml.rels'].replace(b'Id="random-id"',b"Id = 'random-id'")
    with zipfile.ZipFile(path,'w') as archive:
        for name,content in parts.items():archive.writestr(name,content)
    canonicalize(path)
    with zipfile.ZipFile(path) as archive:
        owner=ET.fromstring(archive.read('xl/workbook.xml'));rels=ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        assert next(iter(owner[0].attrib.values()))==rels[0].attrib['Id']!='random-id'
