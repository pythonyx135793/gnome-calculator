"""Lossless bounded normal log export; includes failures and every evidence file."""
import base64
import hashlib
import json
import os
from pathlib import Path
import zipfile
import zlib

task=Path(os.environ['RUNNER_TEMP']).resolve()/'gnome-r1495'
e=task/'evidence'
e.mkdir(parents=True,exist_ok=True)
for name in ['exact-proof.json','before-source.json','actual-command-result.json','native-date-result.json','after-source.json','result.json']:
    path=e/name
    if path.is_file():
        print('GNOME_VISIBLE_RECORD '+name+' '+json.dumps(json.loads(path.read_text()),separators=(',',':')),flush=True)
cases=e/'native-date-cases.json'
if cases.is_file():
    for case in json.loads(cases.read_text()):
        print('GNOME_NATIVE_DATE_CASE '+json.dumps(case,separators=(',',':')),flush=True)
commands=e/'baseline-commands.json'
if commands.is_file():
    for record in json.loads(commands.read_text()):
        visible={key:record[key] for key in ['name','exit_code','timed_out','started','finished'] if key in record}
        for stream in ['stdout','stderr']:
            path=e/(record['name']+'.'+stream)
            if path.is_file():
                visible[stream+'_bytes']=path.stat().st_size
                visible[stream+'_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        print('GNOME_COMMAND_RESULT '+json.dumps(visible,separators=(',',':')),flush=True)
for name in ['meson-setup','native-build','stock-tests','native-date']:
    for stream in ['stdout','stderr']:
        path=e/(name+'.'+stream)
        if path.is_file():
            lines=path.read_text(errors='replace').splitlines()
            for index,line in enumerate(lines[-50:],max(1,len(lines)-49)):
                visible=line if len(line)<=500 else line[:500]+' [visible tail line truncated; full original retained in archive]'
                print('GNOME_VISIBLE_LOG_TAIL '+name+'.'+stream+' '+str(index)+' '+json.dumps(visible,ensure_ascii=True),flush=True)
members=[dict(path=str(p.relative_to(e)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(e.rglob('*')) if p.is_file()]
(e/'MANIFEST.json').write_text(json.dumps(members,indent=2)+'\n')
archive=task/'evidence.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(e.rglob('*')):
        if p.is_file():
            z.write(p,str(p.relative_to(e)))
data=archive.read_bytes()
encoded=base64.b64encode(data).decode('ascii')
width=700
chunks=[encoded[i:i+width] for i in range(0,len(encoded),width)]
meta=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),chunks=len(chunks),manifest_records=len(members))
print('GNOME_EVIDENCE_META '+json.dumps(meta,separators=(',',':')),flush=True)
for n,chunk in enumerate(chunks,1):
    print('GNOME_CHUNK '+str(n)+'/'+str(len(chunks))+' '+format(zlib.crc32(chunk.encode()),'08x')+' '+hashlib.sha256(chunk.encode()).hexdigest()+' '+chunk,flush=True)
print('GNOME_EVIDENCE_COMPLETE '+meta['sha256'],flush=True)
