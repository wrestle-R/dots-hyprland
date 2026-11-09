"""Read-only charge-cap telemetry. A saved threshold is not necessarily an active cap."""
from pathlib import Path
import json
import re


def snapshot(root=Path('/sys/class/power_supply'),state=Path('/var/lib/rdp-charge-limit/settings.json')):
    batteries=[]
    online=any(p.read_text().strip()=='1' for p in root.glob('*/online'))
    preferred=None
    try:
        value=json.loads(state.read_text()).get('limit')
        if isinstance(value,int) and not isinstance(value,bool) and 55<=value<=95:preferred=value
    except (OSError,ValueError,TypeError):pass
    for directory in sorted(root.glob('BAT*')):
        end=directory/'charge_control_end_threshold';start=directory/'charge_control_start_threshold'
        if not end.exists() or not start.exists():continue
        mode_text=(directory/'charge_types').read_text().strip() if (directory/'charge_types').exists() else ''
        match=re.search(r'\[([^]]+)\]',mode_text)
        mode=match.group(1) if match else mode_text
        required='Custom' in mode_text
        limit=int(end.read_text());capacity=int((directory/'capacity').read_text()) if (directory/'capacity').exists() else None
        status=(directory/'status').read_text().strip() if (directory/'status').exists() else 'Unknown'
        configured=limit<100;enforced=configured and (not required or mode=='Custom')
        above=capacity is not None and capacity>limit
        if configured and not enforced:label='Cap saved · Apply to activate Custom mode'
        elif not online:label=(str(capacity)+'% · On battery') if capacity is not None else 'On battery'
        elif enforced and above and status!='Charging':label=str(capacity)+'% · Above cap, charging paused'
        elif enforced and above and status=='Charging':label=str(capacity)+'% · Still charging above cap'
        elif enforced and capacity is not None and capacity>=limit and status!='Charging':label=str(capacity)+'% · Charge limit reached'
        elif status=='Charging':label=(str(capacity)+'% · Charging') if capacity is not None else 'Charging'
        elif enforced:label=(str(capacity)+'% · Charging paused') if capacity is not None else 'Charging paused'
        else:label=(str(capacity)+'% · Plugged in') if capacity is not None else 'Plugged in'
        explanation='The cap stops further charging; it does not drain a battery already above the limit.' if above and enforced else ('Charging resumes below '+str(int(start.read_text()))+'%.' if enforced else 'Apply a limit to enable battery care.')
        batteries.append({'name':directory.name,'start':int(start.read_text()),'end':limit,'capacity':capacity,'status':status,'online':online,'mode':mode,'enforced':enforced,'above_cap':above,'label':label,'explanation':explanation,'preferred':preferred or (limit if limit<=95 else 95)})
    return {'supported':bool(batteries),'batteries':batteries}
