#!/usr/bin/env python3
"""Read only Git objects and author-local XML; bootstrap observations, no QA approval."""
import argparse,hashlib,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path

def git(*args): return subprocess.check_output(['git',*args])
def obj(sha,path): return git('show',sha+':'+path)
def sha(b): return hashlib.sha256(b).hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--author-xml',type=Path);a=p.parse_args()
 main='904ab019dbc31a9a84a00d410b85868c3ddfb9b9'; terrain='9541f62e59e7dbff3c8b3105f4b7c5ecd0723e36'; design='c723048116fd2c36a7c19f2ab6c926f47b78beac'; forest='e7441a2fb9ba04178e806a0675fa584e04ba90e5'
 out={'kind':'bootstrap-source-observation-not-independent-review','main':main,'terrain_head':terrain,'design_head':design,'forest_head':forest}
 base='design/05-visual-design/SW-012/r1/'
 manifest=json.loads(obj(design,base+'design-manifest.json'));checks=[]
 for f in manifest['files']:
  b=obj(design,f['path']);checks.append({'path':f['path'],'bytes':len(b),'sha256':sha(b),'matches':len(b)==f['bytes'] and sha(b)==f['sha256']})
 listed={f['path'] for f in manifest['files']}|{base+'design-manifest.json'}
 actual=set(git('ls-tree','-r','--name-only',design,'--',base).decode().splitlines())
 spec=json.loads(obj(design,base+'design-spec.json'))
 out['design']={'manifest_files':checks,'all_hashes_match':all(x['matches'] for x in checks),'unlisted':sorted(actual-listed),'spec_sha256':sha(obj(design,base+'design-spec.json')),'layers':[{k:l[k] for k in ['id','type','at_meters','to_opacity','fade_meters','parallax']} for l in spec['layers']],'preview_meters':spec['preview_meters'],'status':spec['status']}
 changes=git('diff','--name-only',main+'...'+terrain).decode().splitlines()
 ui_files=git('ls-tree','-r','--name-only',terrain,'--','app/src/main/java/com/sensewalk/app/ui').decode().splitlines()
 ui_hits=[]
 for f in ui_files:
  if not f.endswith('.kt'):continue
  for n,line in enumerate(obj(terrain,f).decode().splitlines(),1):
   if any(term in line for term in ['consumeStabilizeHint','TerrainMotor.Gait','snapshot.gait','snap.gait']):ui_hits.append({'path':f,'line':n,'text':line})
 out['terrain']={'changed_files':changes,'production_changed':[f for f in changes if f.startswith('app/src/main/')],'ui_consumers':ui_hits,'snapshot_compatibility_file':'docs/collaboration/handoffs/zcode/H-SW-005-R1-snapshot-compat.md','author_pending':json.loads(obj(terrain,'docs/collaboration/handoffs/zcode/H-SW-005-R1.json'))['pending']}
 out['forest']={'merge_tree_exit_code':subprocess.run(['git','merge-tree','--write-tree',main,forest],capture_output=True).returncode,'production_delta':git('diff','--name-only',main+'...'+forest,'--','app').decode().splitlines(),'assets':[]}
 for f in ['app/src/main/assets/visual/forest_clearing.webp','app/src/main/assets/visual/forest_light_shows.webp']:
  b=obj(forest,f);out['forest']['assets'].append({'path':f,'bytes':len(b),'sha256':sha(b)})
 old='docs/collaboration/handoffs/zcode/H-SW-010-R1-appendix-sizes.md'
 out['forest']['archived_appendix_modified']=obj(main,old)!=obj(forest,old)
 if a.author_xml:
  suites=[];counts=dict(tests=0,failures=0,errors=0,skipped=0)
  for f in sorted(a.author_xml.glob('TEST-*.xml')):
   b=f.read_bytes();root=ET.fromstring(b);c={k:int(root.get(k,0)) for k in counts};suites.append({'filename':f.name,'sha256':sha(b),'counts':c})
   for k in counts:counts[k]+=c[k]
  out['author_local_xml']={'source':'Read author worktree build/test-results; not downloaded cloud XML and not tests executed by this audit','suites':suites,'counts':counts}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'design_files':len(checks),'hashes_match':out['design']['all_hashes_match'],'unlisted':out['design']['unlisted'],'ui_consumers':ui_hits,'forest_merge_exit':out['forest']['merge_tree_exit_code'],'archived_appendix_modified':out['forest']['archived_appendix_modified'],'author_local_xml':out.get('author_local_xml',{}).get('counts')},ensure_ascii=False))
if __name__=='__main__':main()
