from pathlib import Path
import importlib.util, tempfile, json, shutil
from unittest.mock import patch
P=Path(__file__).resolve().parent
def load(name):
 spec=importlib.util.spec_from_file_location(name,P/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('customizations');c=load('charge_limit')
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp)/'config'; backups=Path(temp)/'backups'
 for item in json.loads((P/'integration.json').read_text()):
  p=root/item['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(item['before'])
 before={p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}
 saved=m.install(root,backups);assert m.plan(root)==[]
 m.restore(root,saved)
 assert all((root/p).read_bytes()==b for p,b in before.items())
 target=root/'quickshell/ii/shell.qml';target.write_text('unknown newer upstream')
 try:m.plan(root);raise AssertionError('accepted unknown upstream')
 except RuntimeError:pass
 target.write_bytes(before[target.relative_to(root)])
 original_write=m.write;calls=[0]
 def fail(path,data,mode=0o644):
  calls[0]+=1
  if calls[0]==3:raise OSError('injected disk failure')
  original_write(path,data,mode)
 with patch.object(m,'write',fail):
  try:m.transact(m.plan(root));raise AssertionError('write should fail')
  except OSError:pass
 assert all((root/p).read_bytes()==b for p,b in before.items())
 assert not (root/'quickshell/ii/services/Slumber.qml').exists()
 # Config is not modified if a file races the preflight.
 change=m.plan(root)[0];path,old,new=change;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'external edit')
 try:m.transact([change]);raise AssertionError('race should fail')
 except RuntimeError:pass
 assert path.read_bytes()==b'external edit'
 c.SYSFS=Path(temp)/'sys';c.STATE=Path(temp)/'state/settings.json';battery=c.SYSFS/'BAT0';battery.mkdir(parents=True)
 (battery/'charge_control_start_threshold').write_text('50');(battery/'charge_control_end_threshold').write_text('90')
 assert c.apply(95)=={'enabled':True,'limit':95};assert (battery/'charge_control_start_threshold').read_text()=='90'
 assert c.apply(95,False)['limit']==100
 previous=c.STATE.read_bytes()
 with patch.object(c,'atomic',side_effect=OSError('disk full')):
  try:c.apply(80);raise AssertionError('state write should fail')
  except OSError:pass
 assert (battery/'charge_control_end_threshold').read_text()=='100';assert (battery/'charge_control_start_threshold').read_text()=='95';assert c.STATE.read_bytes()==previous
 for invalid in [0,54,101,True,'95']:
  try:c.thresholds(invalid);raise AssertionError('bad threshold accepted')
  except ValueError:pass
 print('PASS: install idempotency, restore, unknown upstream refusal, injected partial-write rollback, concurrent edit refusal, charge apply/off, charge persistence rollback, threshold validation')
