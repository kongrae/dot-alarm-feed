#!/usr/bin/env python3
"""Collect KASI named public holidays. Keep service credentials out of output/errors."""
import argparse, datetime as dt, json, os, pathlib, tempfile, urllib.parse, urllib.request, xml.etree.ElementTree as ET
ENDPOINT='https://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo'
ANCHORS=('01-01','03-01','05-05','06-06','08-15','10-03','10-09','12-25')

def parse_year(xml, year):
    root=ET.fromstring(xml)
    if root.findtext('./header/resultCode') != '00': raise ValueError('KASI returned an unsuccessful result')
    items=root.findall('./body/items/item')
    if int(root.findtext('./body/totalCount','-1')) != len(items): raise ValueError('Incomplete API response')
    rows={}
    for item in items:
        if item.findtext('isHoliday') != 'Y': continue
        name=(item.findtext('dateName') or '').strip()
        if name=='일요일': continue # Weekends remain a separate repeat-weekday choice.
        raw=item.findtext('locdate','')
        date=dt.datetime.strptime(raw,'%Y%m%d').date()
        if date.year != year or not name or len(name)>100: raise ValueError('Invalid API holiday')
        rows.setdefault(date.isoformat(),set()).add(name)
    return [dict(date=d,name=' · '.join(sorted(names))) for d,names in sorted(rows.items())]

def require(value):
    if not value: raise ValueError("Invalid or incomplete holiday dataset")

def validate(data, previous=None):
    require(data['schemaVersion']==1 and data['datasetVersion']>0)
    years=data['years']; require(0<len(years)<=10 and len(set(years))==len(years))
    require(all(1970<=y<=2100 for y in years))
    require(data['sourceName'] and data['sourceURLs'] and all(urllib.parse.urlparse(u).scheme=='https' and urllib.parse.urlparse(u).hostname for u in data['sourceURLs']))
    dt.datetime.fromisoformat(data['checkedAt'].replace('Z','+00:00'))
    rows=data['holidays']; dates={r['date'] for r in rows}; require(len(dates)==len(rows))
    require(all(dt.date.fromisoformat(r['date']).isoformat()==r['date'] and dt.date.fromisoformat(r['date']).year in years and 0<len(r['name'])<=100 for r in rows))
    for year in years:
        require(15<=sum(d.startswith(f'{year}-') for d in dates)<=100)
        require(all(f'{year}-{anchor}' in dates for anchor in ANCHORS+(('05-01','07-17') if year>=2026 else ())))
    if previous:
        require(data['datasetVersion']>=previous['datasetVersion'])
        require(data['datasetVersion']!=previous['datasetVersion'] or data==previous)
        for year in previous['years']:
            require(year in years)
            require(sum(d.startswith(f'{year}-') for d in dates)*100>=sum(r['date'].startswith(f'{year}-') for r in previous['holidays'])*80)

def supplement(rows, years, path):
    """Adds announced holidays the API does not list yet (a new holiday, a temporary one). A date the API already has
    keeps the API's name. Returns the rows and the supplement's source URLs (empty when nothing was added)."""
    if not path or not path.exists(): return rows,[]
    extra=json.loads(path.read_text(encoding='utf-8'))
    have={r['date'] for r in rows}
    added=[dict(date=r['date'],name=r['name']) for r in extra.get('holidays',[]) if int(r['date'][:4]) in years and r['date'] not in have]
    if not added: return rows,[]
    return sorted(rows+added,key=lambda r:r['date']),[u for u in extra.get('sourceURLs',[]) if u]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--years',nargs='+',type=int,required=True); p.add_argument('--output',type=pathlib.Path,required=True)
    p.add_argument('--supplement',type=pathlib.Path,help='announced holidays the API may still lack: {"sourceURLs":[...],"holidays":[{"date","name"}]}')
    args=p.parse_args()
    key=os.environ.get('KASI_SERVICE_KEY')
    if not key: raise SystemExit('KASI_SERVICE_KEY is not configured; existing data was not changed')
    previous=json.loads(args.output.read_text()) if args.output.exists() else None
    years=sorted(set(args.years) | set(previous['years'] if previous else []))
    rows=[]
    try:
        for year in years:
            query=urllib.parse.urlencode(dict(serviceKey=urllib.parse.unquote(key),solYear=year,numOfRows=1000,pageNo=1))
            with urllib.request.urlopen(ENDPOINT+'?'+query,timeout=20) as r:
                raw=r.read(1_000_001)
                if len(raw)>1_000_000: raise ValueError('Response too large')
                rows.extend(parse_year(raw,year))
        rows,extra_sources=supplement(rows,years,args.supplement)
        now=dt.datetime.now(dt.timezone.utc)
        data=dict(schemaVersion=1,datasetVersion=int(now.strftime('%Y%m%d%H%M%S')),checkedAt=now.strftime('%Y-%m-%dT%H:%M:%SZ'),years=years,sourceName='한국천문연구원 특일 정보 · 공휴일'+(' · 정부 발표 보충' if extra_sources else ''),sourceURLs=['https://www.data.go.kr/data/15012690/openapi.do']+extra_sources,holidays=rows)
        validate(data,previous)
    except Exception:
        # urllib errors may contain serviceKey in the URL. Do not log raw exceptions.
        raise SystemExit('Holiday collection/validation failed; existing data was not changed') from None
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',dir=args.output.parent,delete=False,encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');tmp=pathlib.Path(f.name)
    tmp.replace(args.output)
    print(f'Validated {len(rows)} named holidays for {years}')
if __name__=='__main__':main()
