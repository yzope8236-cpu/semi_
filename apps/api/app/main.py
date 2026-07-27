from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from datetime import datetime, timezone
from hashlib import sha256
import gzip, io, tarfile, zipfile
from .config import settings
from .parsers import parse_atdf
from .stdf_parser import parse_stdf
from .db import client, rows, scalar
from .analytics import router as analytics_router

app=FastAPI(title="YieldScope Analytics API", version="0.1.0", description="Traceable semiconductor tester analytics")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(','), allow_methods=['*'], allow_headers=['*'])
app.include_router(analytics_router)

@app.on_event("startup")
def startup_event():
    try:
        client().query("ALTER TABLE devices ADD COLUMN IF NOT EXISTS is_final_attempt UInt8 DEFAULT 1")
        client().query("ALTER TABLE test_results ADD COLUMN IF NOT EXISTS original_unit String DEFAULT ''")
    except Exception:
        pass

@app.get('/health')
def health():
    try: scalar('SELECT 1'); return {'status':'ok','database':'connected'}
    except Exception as e: return {'status':'degraded','database':str(e)}

def unpack_payload(name: str, data: bytes) -> tuple[str, bytes]:
    """Auto-detect gzip/zip/tar.gz; one test file per archive keeps file lineage unambiguous."""
    lower=name.lower()
    if data[:2] == b'\x1f\x8b' and not lower.endswith(('.tar.gz', '.tgz')):
        return name.removesuffix('.gz'), gzip.decompress(data)
    if zipfile.is_zipfile(io.BytesIO(data)):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            files=[x for x in archive.infolist() if not x.is_dir()]
            if len(files)!=1: raise HTTPException(422,'ZIP must contain exactly one STDF/ATDF payload')
            return files[0].filename, archive.read(files[0])
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as archive:
            files=[x for x in archive.getmembers() if x.isfile()]
            if len(files)!=1: raise HTTPException(422,'TAR archive must contain exactly one STDF/ATDF payload')
            member=archive.extractfile(files[0]); return files[0].name, member.read() if member else b''
    except tarfile.ReadError:
        return name,data

def ingest(name: str, data: bytes):
    digest=sha256(data).hexdigest(); c=client()
    if scalar('SELECT count() FROM ingest_files WHERE sha256={hash:String}', {'hash':digest}): return {'status':'duplicate','sha256':digest}
    payload_name, payload=unpack_payload(name,data)
    
    is_atdf_text = b'FAR:' in payload[:512] or b'# AT' in payload[:512] or b'\nFAR' in payload[:512]
    
    is_binary_stdf = False
    if payload_name.lower().endswith(('.std', '.stdf')) and not is_atdf_text:
        is_binary_stdf = True
    elif not is_atdf_text and len(payload) >= 4 and payload[2] == 0 and payload[3] == 10:
        is_binary_stdf = True

    if is_binary_stdf:
        parsed = parse_stdf(payload, payload_name)
        source_format = "STDF"
        parser_ver = "stdf-parser/0.1"
    elif is_atdf_text:
        parsed = parse_atdf(payload.decode('utf-8',errors='replace'))
        source_format = "ATDF"
        parser_ver = "atdf-parser/0.2"
    else:
        raise HTTPException(422, 'Unrecognized file format; must be valid ATDF or binary STDF V4.')

    fid=uuid4(); now=datetime.now(timezone.utc)
    c.insert('ingest_files', [[fid,digest,name,source_format,'validated' if not any(x.severity=='error' for x in parsed.findings) else 'requires_review',now,parser_ver,'default/1',name,parsed.tester_id,parsed.firmware_version,parsed.lot_id,parsed.part_id,parsed.program_name,parsed.records,len(parsed.findings),[f.code for f in parsed.findings]]], column_names=['file_id','sha256','file_name','source_format','status','received_at','parser_version','mapping_version','source_uri','tester_id','firmware_version','lot_id','part_id','program_name','records_parsed','error_count','warnings'])
    if parsed.raw_records: c.insert('raw_records', [[fid,r['offset'],r['record_type'],r['record_fields'],parser_ver,now] for r in parsed.raw_records], column_names=['file_id','record_offset','record_type','record_fields','parser_version','created_at'])
    if parsed.wafers: c.insert('wafers', [[w['wafer_id'],fid,parsed.lot_id,w['wafer_index'],parsed.tester_id,w['mask_id'],w['start_time'],now,0,0,None,now] for w in parsed.wafers], column_names=['wafer_id','file_id','lot_id','wafer_index','tester_id','mask_id','start_time','end_time','declared_pass_count','declared_fail_count','declared_yield','created_at'])
    if parsed.devices: c.insert('devices', [[d['device_id'],d['wafer_id'],parsed.lot_id,d['site'],d['channel'],d['x_coord'],d['y_coord'],d['hardware_bin'],d['software_bin'],d['passed'],d['retest_count'],d['test_time_ms'],d['tested_at'], int(d.get('is_final_attempt', 1))] for d in parsed.devices], column_names=['device_id','wafer_id','lot_id','site','channel','x_coord','y_coord','hardware_bin','software_bin','passed','retest_count','test_time_ms','tested_at','is_final_attempt'])
    if parsed.results: c.insert('test_results', [[uuid4(),r['device_id'],r['wafer_id'],parsed.lot_id,r['test_num'],r['test_name'],r['pin_name'],r['measured_value'],r['lower_limit'],r['upper_limit'],r['normalized_value'],r['normalized_unit'],r['passed'],r['elapsed_ms'],r['attempt_index'],r['original_unit'],r['tested_at']] for r in parsed.results], column_names=['result_id','device_id','wafer_id','lot_id','test_num','test_name','pin_name','measured_value','lower_limit','upper_limit','normalized_value','normalized_unit','passed','elapsed_ms','attempt_index','original_unit','tested_at'])
    if parsed.findings: c.insert('validation_events', [[uuid4(),fid,f.severity,f.code,f.message,f.line,now] for f in parsed.findings], column_names=['event_id','file_id','severity','code','message','record_number','created_at'])
    return {'status':'ingested','file_id':str(fid),'lot_id':parsed.lot_id,'records':parsed.records,'devices':len(parsed.devices),'results':len(parsed.results),'findings':[f.__dict__ for f in parsed.findings]}

@app.post('/api/v1/ingest/files', status_code=201)
async def upload(file: UploadFile=File(...)):
    return ingest(file.filename or 'upload.atdf',await file.read())
@app.get('/api/v1/dashboard/overview')
def overview():
    k=rows("SELECT count() devices, round(avg(passed)*100,2) yield_pct, sum(passed=0) failed, round(avg(test_time_ms),1) avg_test_ms FROM devices FINAL WHERE is_final_attempt=1")[0]
    trend=rows("SELECT lot_id, round(avg(passed)*100,2) yield_pct, count() devices FROM devices FINAL WHERE is_final_attempt=1 GROUP BY lot_id ORDER BY lot_id DESC LIMIT 12")
    return {'kpis':k,'trend':trend}
@app.get('/api/v1/wafers')
def wafers():
    return rows("SELECT wafer_id, lot_id, count(d.device_id) devices, round(avg(d.passed)*100,2) yield_pct, sum(d.passed=0) failed FROM wafers w LEFT JOIN (SELECT * FROM devices FINAL WHERE is_final_attempt=1) d USING (wafer_id,lot_id) GROUP BY wafer_id,lot_id ORDER BY lot_id DESC,wafer_id")
@app.get('/api/v1/wafers/{wafer_id}/map')
def wafer_map(wafer_id:str):
    data=rows("SELECT device_id,x_coord,y_coord,passed,hardware_bin,site,retest_count FROM devices FINAL WHERE wafer_id={id:String} AND is_final_attempt=1 ORDER BY y_coord,x_coord",{'id':wafer_id})
    if not data: raise HTTPException(404,'Wafer not found')
    return {'wafer_id':wafer_id,'dies':data,'yield_pct':round(sum(x['passed'] for x in data)*100/len(data),2)}
@app.get('/api/v1/analytics/failures')
def failures():
    return rows("SELECT test_num,test_name,pin_name,count() observations,sum(t.passed=0) failures,round(sum(t.passed=0)*100/count(),2) failure_rate FROM test_results t INNER JOIN devices d USING (device_id) WHERE d.is_final_attempt=1 GROUP BY test_num,test_name,pin_name HAVING failures > 0 ORDER BY failures DESC LIMIT 20")

@app.get('/api/v1/analytics/alerts')
def alerts(threshold: float = 95.0):
    """Return wafers below yield threshold; intended as the source for email/Teams alert workers."""
    return rows("SELECT wafer_id, lot_id, count() devices, round(avg(passed)*100,2) yield_pct, "
                "round(sum(passed=0)*1000000/count(),0) dppm FROM devices FINAL "
                "WHERE is_final_attempt=1 GROUP BY wafer_id,lot_id HAVING yield_pct < {threshold:Float64} ORDER BY yield_pct", {'threshold':threshold})

@app.get('/api/v1/devices/{device_id}')
def device_detail(device_id: str):
    device=rows("SELECT device_id,wafer_id,lot_id,site,channel,x_coord,y_coord,hardware_bin,software_bin,passed,retest_count,test_time_ms,tested_at FROM devices FINAL WHERE device_id={id:String} LIMIT 1", {'id':device_id})
    if not device: raise HTTPException(404,'Device not found')
    results=rows("SELECT test_num,test_name,pin_name,measured_value,lower_limit,upper_limit,normalized_value,normalized_unit,passed,elapsed_ms FROM test_results WHERE device_id={id:String} ORDER BY test_num", {'id':device_id})
    return {'device':device[0], 'test_results':results}

@app.get('/api/v1/analytics/spatial/{wafer_id}')
def spatial_summary(wafer_id: str):
    """A deterministic first-pass defect signal: failed die count in edge/corner regions."""
    dies=rows("SELECT x_coord,y_coord,passed FROM devices FINAL WHERE wafer_id={id:String} AND is_final_attempt=1", {'id':wafer_id})
    if not dies: raise HTTPException(404,'Wafer not found')
    xs=[d['x_coord'] for d in dies]; ys=[d['y_coord'] for d in dies]; minx,maxx,miny,maxy=min(xs),max(xs),min(ys),max(ys)
    failed=[d for d in dies if not d['passed']]
    edge=[d for d in failed if d['x_coord'] in (minx,maxx) or d['y_coord'] in (miny,maxy)]
    corner=[d for d in failed if d['x_coord'] in (minx,maxx) and d['y_coord'] in (miny,maxy)]
    return {'wafer_id':wafer_id,'failed_dies':len(failed),'edge_failures':len(edge),'corner_failures':len(corner), 'edge_failure_share_pct':round(100*len(edge)/len(failed),2) if failed else 0, 'interpretation':'edge-dominant pattern' if failed and len(edge)/len(failed)>=0.5 else 'no edge-dominant pattern'}
@app.get('/api/v1/ingest/files')
def get_ingest_files(limit: int = 100):
    safe_limit = min(max(limit, 1), 200)
    return rows("SELECT file_id, file_name, sha256, source_format, status, received_at, parser_version, mapping_version, source_uri, tester_id, firmware_version, lot_id, part_id, program_name, records_parsed, error_count, warnings FROM ingest_files ORDER BY received_at DESC LIMIT {limit:UInt32}", {'limit': safe_limit})

@app.get('/api/v1/quality/files/{file_id}')
def quality(file_id:str): return rows("SELECT severity,code,message,record_number,created_at FROM validation_events WHERE file_id={id:UUID} ORDER BY created_at",{'id':file_id})
@app.post('/api/v1/demo/seed')
def seed():
    lines=['FAR:V4|FW-2026.07|2026-07-27T08:00:00Z|ADV-93K-01','MIR:LOT-DEMO-2407|ASIC-X1|ADV-93K-01|yield_v4.2','WIR:WAFER-DEMO-01|1|MASK-A|2026-07-27T08:00:00Z']
    for y in range(12):
      for x in range(12):
        fail=(x<2 and y<5) or (x==10 and y>8); did=f'D{x:02}{y:02}'; lines += [f'PIR:{did}|{x}|{y}|{(x%4)+1}|CH-{x%8}',f'PTR:101|IDDQ|{1.45 if fail else 0.82}|0.5|1.2|mA|{"FAIL" if fail else "PASS"}|VDD|4.2',f'PTR:202|VTH|{0.61 if fail else 0.72}|0.65|0.85|V|{"FAIL" if fail else "PASS"}|GATE|3.1',f'PRR:{10 if fail else 1}|{10 if fail else 1}|{"FAIL" if fail else "PASS"}|{1 if fail else 0}|18.2']
    return ingest('yieldscope-demo.atdf','\n'.join(lines).encode())
