"""Remove random OOXML relationship IDs and ZIP timestamps without changing cells."""
from pathlib import Path,PurePosixPath
import hashlib,io,re,tempfile,zipfile
import xml.etree.ElementTree as ET

def canonicalize(path):
    path=Path(path)
    if path.is_symlink():raise ValueError('Workbook links are not eligible')
    with zipfile.ZipFile(path) as source:
        if len(set(source.namelist()))!=len(source.namelist()):raise ValueError('Duplicate workbook members')
        members={name:source.read(name) for name in source.namelist()}
    for name in sorted(members):
        if not name.endswith('.rels'):continue
        root=ET.fromstring(members[name]);mapping={}
        for relationship in root:
            old=relationship.attrib['Id']
            identity='|'.join([name,relationship.attrib['Type'],relationship.attrib['Target'],relationship.attrib.get('TargetMode','')])
            mapping[old]='rId'+hashlib.sha256(identity.encode()).hexdigest()[:24]
        if len(set(mapping.values()))!=len(mapping):raise ValueError('Relationship identity collision')
        text=members[name].decode('utf-8')
        text=re.sub(r'(\bId\s*=\s*)([\"\x27])([^\"\x27]+)\2',lambda match:match.group(1)+match.group(2)+mapping.get(match.group(3),match.group(3))+match.group(2),text)
        actual_ids={relationship.attrib['Id'] for relationship in ET.fromstring(text)}
        if len(root)!=len(mapping) or actual_ids!=set(mapping.values()):raise ValueError('Relationship ID rewrite failed')
        members[name]=text.encode('utf-8')
        rel=PurePosixPath(name)
        owner=(rel.parent.parent/rel.name[:-5]).as_posix()
        if owner in members:
            text=members[owner].decode('utf-8')
            namespaces={}
            for _,(prefix,uri) in ET.iterparse(io.BytesIO(members[owner]),events=('start-ns',)):
                namespaces.setdefault(prefix,set()).add(uri)
            if any(len(uris)>1 for uris in namespaces.values()):raise ValueError('Rebound namespace prefixes are not supported')
            relationship_namespace='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
            prefixes=[prefix for prefix,uris in namespaces.items() if prefix and relationship_namespace in uris]
            def replace(match):
                return match.group(1)+match.group(2)+mapping.get(match.group(3),match.group(3))+match.group(2)
            if prefixes:
                pattern=r'(\b(?:'+ '|'.join(re.escape(prefix) for prefix in prefixes)+r'):(?:id|embed|link)\s*=\s*)([\"\x27])([^\"\x27]+)\2'
                text=re.sub(pattern,replace,text)
            for element in ET.fromstring(text).iter():
                for attribute,value in element.attrib.items():
                    if attribute in {'{'+relationship_namespace+'}'+field for field in ('id','embed','link')} and value not in actual_ids:
                        raise ValueError('Unresolved relationship reference after normalization')
            members[owner]=text.encode('utf-8')
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix=path.name+'.',suffix='.tmp',delete=False) as handle:
            temporary=Path(handle.name)
            with zipfile.ZipFile(handle,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as output:
                for name in sorted(members):
                    info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                    info.create_system=3;info.external_attr=0o600<<16
                    output.writestr(info,members[name],compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():temporary.unlink()
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('workbook',type=Path);canonicalize(parser.parse_args().workbook)
