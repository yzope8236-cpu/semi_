"""Canonical CSV importer.
Accepted header aliases are intentionally explicit: arbitrary CSV files need a mapping
before they can be treated as semiconductor test data.
"""
import csv
from datetime import datetime, timezone
from io import StringIO
from .parsers import Parsed, Finding, normalize

ALIASES = {
    "lot_id": ("lot_id", "lot", "lotid"), "wafer_id": ("wafer_id", "wafer", "waferid"),
    "device_id": ("device_id", "device", "die_id", "die"), "x_coord": ("x_coord", "x", "x_coordinate"),
    "y_coord": ("y_coord", "y", "y_coordinate"), "site": ("site", "site_num"),
    "hardware_bin": ("hardware_bin", "hard_bin", "hbin"), "software_bin": ("software_bin", "soft_bin", "sbin"),
    "passed": ("passed", "pass_fail", "result", "status"), "test_num": ("test_num", "test_number"),
    "test_name": ("test_name", "test"), "measured_value": ("measured_value", "test_value", "value", "result_value"),
    "lower_limit": ("lower_limit", "lo_limit", "low_limit"), "upper_limit": ("upper_limit", "hi_limit", "high_limit"),
    "unit": ("unit", "units"), "pin_name": ("pin_name", "pin"), "elapsed_ms": ("elapsed_ms", "test_time_ms"),
    "retest_count": ("retest_count", "attempt_index", "retest"), "channel": ("channel",),
}
def as_int(value, default=0):
    try: return int(float(value))
    except (TypeError, ValueError): return default
def as_float(value):
    try: return float(value) if value not in (None, "") else None
    except (TypeError, ValueError): return None
def pass_value(value): return str(value).strip().upper() in {"1", "P", "PASS", "Y", "TRUE"}
def pick(row, key, default=""):
    for alias in ALIASES[key]:
        if alias in row and row[alias] not in (None, ""): return row[alias]
    return default

def parse_csv(content: bytes) -> Parsed:
    text=content.decode("utf-8-sig", errors="replace")
    reader=csv.DictReader(StringIO(text))
    p=Parsed(far_seen=True, stdf_version="CSV-CANONICAL/1", firmware_version="N/A")
    if not reader.fieldnames:
        p.findings.append(Finding("error", "CSV_NO_HEADER", "CSV must include a header row", 0)); return p
    headers={h.strip().lower(): h for h in reader.fieldnames if h}
    rows=[]
    for line, raw in enumerate(reader, 2):
        row={str(k).strip().lower(): (v or "").strip() for k,v in raw.items() if k}
        rows.append((line,row))
    if not rows:
        p.findings.append(Finding("error", "CSV_EMPTY", "CSV has no data rows", 0)); return p
    required=("wafer_id", "x_coord", "y_coord", "passed")
    missing=[key for key in required if not any(alias in headers for alias in ALIASES[key])]
    if missing:
        p.findings.append(Finding("error", "CSV_MAPPING_REQUIRED", "Missing canonical columns: "+", ".join(missing), 0)); return p
    first=rows[0][1]; p.lot_id=pick(first,"lot_id","CSV-LOT"); p.part_id="CSV-PART"; p.tester_id="CSV-UPLOAD"; p.program_name="csv-canonical"
    wafer_ids=[]; devices={}
    for line,row in rows:
        wafer=pick(row,"wafer_id"); lot=pick(row,"lot_id",p.lot_id); p.lot_id=lot or p.lot_id
        if wafer not in wafer_ids: wafer_ids.append(wafer)
        did=pick(row,"device_id", f"{wafer}-{pick(row,'x_coord')}-{pick(row,'y_coord')}")
        key=(wafer,did); now=datetime.now(timezone.utc)
        if key not in devices:
            devices[key]={"device_id":did,"wafer_id":wafer,"x_coord":as_int(pick(row,"x_coord")),"y_coord":as_int(pick(row,"y_coord")),"site":as_int(pick(row,"site")),"channel":pick(row,"channel"),"hardware_bin":as_int(pick(row,"hardware_bin")),"software_bin":as_int(pick(row,"software_bin")),"passed":int(pass_value(pick(row,"passed"))),"retest_count":as_int(pick(row,"retest_count")),"test_time_ms":as_float(pick(row,"elapsed_ms")),"tested_at":now}
        if pick(row,"test_name") or pick(row,"test_num"):
            value=as_float(pick(row,"measured_value")); lo=as_float(pick(row,"lower_limit")); hi=as_float(pick(row,"upper_limit")); unit=pick(row,"unit"); normalized, normalized_unit=normalize(value,unit)
            p.results.append({**devices[key],"test_num":as_int(pick(row,"test_num")),"test_name":pick(row,"test_name",f"TEST_{as_int(pick(row,'test_num'))}"),"measured_value":value,"lower_limit":lo,"upper_limit":hi,"normalized_value":normalized,"normalized_unit":normalized_unit,"original_unit":unit,"attempt_index":devices[key]["retest_count"],"passed":int(pass_value(pick(row,"passed"))),"pin_name":pick(row,"pin_name"),"elapsed_ms":as_float(pick(row,"elapsed_ms"))})
        p.raw_records.append({"offset":line,"record_type":"CSV_ROW","record_fields":str(row)})
    p.wir_seen=True
    p.wafers=[{"wafer_id":w,"wafer_index":i+1,"mask_id":"CSV","start_time":datetime.now(timezone.utc)} for i,w in enumerate(wafer_ids)]
    p.devices=list(devices.values()); p.records=len(rows)
    return p
