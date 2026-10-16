#!/usr/bin/env python3
"""Zero API bootstrap probe against actual accepted design. Images copied unchanged.

All manifests are test-only declarations under a temporary .local-verify directory.
No state, registry, approved design, published image or old record is modified.
"""
import argparse,hashlib,json,shutil,subprocess,sys,tempfile,importlib.util
sys.dont_write_bytecode = True
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.root.resolve()
 rel=Path('design/assets/rainforest/preflight/SW-015/r1');scripts=root/rel/'scripts'
 dr={'task_id':'SW-012','handoff':'docs/collaboration/handoffs/trae-design/H-SW-012-R1.json','spec_file':'design/05-visual-design/SW-012/r1/design-spec.json','spec_sha256':'643e77b1ba7574c9b013dce485fde2797816096181feda91c2fa7920d042c320'}
 report={'kind':'bootstrap-zero-api-observation-not-independent-review','source_head':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),'design_ref':dr,'scripts':{x.name:hashlib.sha256(x.read_bytes()).hexdigest()for x in scripts.glob('*.py')},'cases':[],'actual_api_calls':0}
 tempbase=root/'.local-verify';tempbase.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='production-gate-probe-',dir=tempbase) as tmp:
  tmp=Path(tmp);ref=tmp/'design-ref.json';ref.write_text(json.dumps(dr));candidate=tmp/'wrong-size-sample';shutil.copytree(root/rel/'fixtures/sw015_positive_rainforest_canonical',candidate)
  def run(name,argv,expected,context):
   target=tmp/(name+'.json');cmd=[sys.executable,'-B',*argv,'--out',str(target)]
   proc=subprocess.run(cmd,cwd=root,text=True,capture_output=True)
   result=json.loads(target.read_text())if target.exists()else {'stdout':proc.stdout,'stderr':proc.stderr}
   report['cases'].append({'name':name,'expected_status':expected,'exit_code':proc.returncode,'context':context,'result':result})
  run('real-approved-default-design',['design/assets/rainforest/preflight/SW-015/r1/scripts/dry_run.py','--design-ref-json',str(ref)],'ok','Actual main registry/review/D-009-approved immutable spec, no synthetic approval')
  run('real-approved-strict-design',['design/assets/rainforest/preflight/SW-015/r1/scripts/dry_run.py','--design-ref-json',str(ref),'--strict-design'],'ok','Same accepted spec retained proposed source text by D-009; strict flag should not override actual independent approval')
  m=json.loads((candidate/'manifest.json').read_text());m['design_ref']=dr
  for k in ['_fixture_mode','_expected_registry_status']:m.pop(k,None)
  for name,rev,total in [('wrong-size-default-preflight',0,14),('nine-task-attempts-default-preflight',9,23)]:
   m['api_attempts_this_revision']=rev;m['api_attempts_total']=total;(candidate/'manifest.json').write_text(json.dumps(m))
   run(name,['design/assets/rainforest/preflight/SW-015/r1/scripts/preflight.py',str(candidate/'manifest.json')],'failed',{'fixture_images_copied_unmodified':True,'decoded_source_dimensions':[768,1376],'approved_canvas':[1080,1920],'manifest_api_attempts_this_revision':rev,'manifest_project_attempts_total':total,'task_budget':8,'actual_api_calls':0})
 spec=importlib.util.spec_from_file_location('production_budget_probe',root/'design/assets/rainforest/preflight/SW-014/r3/scripts/preflight.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 checks=[];mod.check_api_budget({'api_attempts_this_revision':9,'api_attempts_total':23,'cost':0},checks)
 report['cases'].append({'name':'budget-only-nine-task-attempts','expected_status':'failed','exit_code':None,'context':'Direct budget function, actual main history14, no images or other failing dimensions, zero real API calls','result':{'status':'ok'if all(c['ok']for c in checks)else'failed','checks':checks}})
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps([{'name':c['name'],'expected':c['expected_status'],'actual':c['result'].get('status',c['result'].get('ok')),'exit_code':c['exit_code']}for c in report['cases']]))
if __name__=='__main__':main()
