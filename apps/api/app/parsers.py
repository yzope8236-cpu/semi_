"""Tolerant ATDF parser with explicit traceability and validation findings.
ATDF uses colon-prefixed records and | separated fields; vendor schemas can be supplied
as mappings in a production deployment. This MVP handles the common MIR/WIR/PIR/PTR/PRR flow.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import re

@dataclass
class Finding:
    severity: str; code: str; message: str; line: int
@dataclass
class Parsed:
    lot_id: str = "UNKNOWN"; part_id: str = "UNKNOWN"; tester_id: str = "UNKNOWN"; program_name: str = "UNKNOWN"
    firmware_version: str = "UNKNOWN"; stdf_version: str = "UNKNOWN"; far_seen: bool = False; wir_seen: bool = False
    wafers: list = field(default_factory=list); devices: list = field(default_factory=list); results: list = field(default_factory=list)
    raw_records: list = field(default_factory=list); findings: list[Finding] = field(default_factory=list); records: int = 0

def num(v: str) -> Optional[float]:
    try: return float(v) if v.strip() else None
    except ValueError: return None
def integer(v: str, fallback=0):
    try: return int(float(v))
    except ValueError: return fallback
def timestamp(v: str) -> datetime:
    try: return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except (ValueError, AttributeError): return datetime.now(timezone.utc)
def normalize(value, unit):
    unit=(unit or "").strip(); factors={"mV":(1e-3,"V"),"uV":(1e-6,"V"),"mA":(1e-3,"A"),"uA":(1e-6,"A"),"kOhm":(1e3,"Ohm"),"MOhm":(1e6,"Ohm"),"ms":(1,"ms"),"s":(1000,"ms")}
    factor,target=factors.get(unit,(1,unit))
    return (value * factor if value is not None else None),target

def parse_atdf(content: str) -> Parsed:
    p=Parsed(); current_wafer=""; current_device=None
    for line_no, raw in enumerate(content.splitlines(), 1):
        line=raw.strip()
        if not line or line.startswith("#"): continue
        if ":" not in line:
            p.findings.append(Finding("warning","UNKNOWN_LINE","Line lacks record separator",line_no)); continue
        rec, body=line.split(":",1); rec=rec.upper().strip(); fields=[x.strip() for x in body.split("|")]; p.records+=1
        # Immutable normalized raw stream for source-level provenance. Offsets are line numbers for ATDF.
        p.raw_records.append({"offset":line_no,"record_type":rec,"record_fields":body})
        if rec == "FAR":
            # FAR: stdf_version|firmware_version|creation_ts|tester_id (tolerant vendor form)
            p.far_seen=True; p.stdf_version=fields[0] if fields else "UNKNOWN"; p.firmware_version=fields[1] if len(fields)>1 else "UNKNOWN"
            if len(fields)>3 and fields[3]: p.tester_id=fields[3]
        elif rec == "MIR":
            # MIR tester ID takes precedence when present; otherwise retain FAR tester ID.
            # lot|part|tester|program
            # lot|part|tester|program
            p.lot_id=fields[0] or "UNKNOWN"; p.part_id=fields[1] if len(fields)>1 else "UNKNOWN"; p.tester_id=fields[2] if len(fields)>2 and fields[2] else p.tester_id; p.program_name=fields[3] if len(fields)>3 else "UNKNOWN"
        elif rec == "WIR":
            # wafer_id|index|mask|start_ts
            if not fields[0]: p.findings.append(Finding("error","MISSING_WAFER_ID","WIR needs wafer ID",line_no)); continue
            current_wafer=fields[0]; p.wir_seen=True; p.wafers.append({"wafer_id":current_wafer,"wafer_index":integer(fields[1]) if len(fields)>1 else 0,"mask_id":fields[2] if len(fields)>2 else "","start_time":timestamp(fields[3]) if len(fields)>3 else timestamp("")})
        elif rec == "PIR":
            # device_id|x|y|site|channel
            if not current_wafer: p.findings.append(Finding("error","ORPHAN_DEVICE","PIR precedes WIR",line_no)); continue
            current_device={"device_id":fields[0] or f"{current_wafer}-{line_no}","wafer_id":current_wafer,"x_coord":integer(fields[1]) if len(fields)>1 else 0,"y_coord":integer(fields[2]) if len(fields)>2 else 0,"site":integer(fields[3]) if len(fields)>3 else 0,"channel":fields[4] if len(fields)>4 else "","retest_count":0,"tested_at":datetime.now(timezone.utc)}
        elif rec == "PTR":
            # number|name|value|lo|hi|unit|pass|pin|elapsed_ms
            if not current_device: p.findings.append(Finding("error","ORPHAN_TEST","PTR precedes PIR",line_no)); continue
            if len(fields)<2: p.findings.append(Finding("error","MALFORMED_PTR","PTR requires test number and name",line_no)); continue
            value=num(fields[2]) if len(fields)>2 else None; lo=num(fields[3]) if len(fields)>3 else None; hi=num(fields[4]) if len(fields)>4 else None; unit=fields[5] if len(fields)>5 else ""
            normalized, normalized_unit=normalize(value,unit); declared=fields[6].upper() if len(fields)>6 else ""
            passed=declared in ("P","PASS","1","Y") if declared else (value is not None and (lo is None or value>=lo) and (hi is None or value<=hi))
            p.results.append({**current_device,"test_num":integer(fields[0]),"test_name":fields[1],"measured_value":value,"lower_limit":lo,"upper_limit":hi,"normalized_value":normalized,"normalized_unit":normalized_unit,"original_unit":unit,"attempt_index":current_device.get('retest_count',0),"passed":int(passed),"pin_name":fields[7] if len(fields)>7 else "","elapsed_ms":num(fields[8]) if len(fields)>8 else None})
        elif rec == "PRR":
            # hardware_bin|software_bin|pass|retest|test_ms
            if not current_device: p.findings.append(Finding("warning","ORPHAN_PRR","PRR precedes PIR",line_no)); continue
            current_device.update({"hardware_bin":integer(fields[0]) if fields else 0,"software_bin":integer(fields[1]) if len(fields)>1 else 0,"passed":int(fields[2].upper() in ("P","PASS","1","Y")) if len(fields)>2 else 0,"retest_count":integer(fields[3]) if len(fields)>3 else 0,"test_time_ms":num(fields[4]) if len(fields)>4 else None})
            # PTRs precede PRR, so finalize their attempt sequence once PRR is observed.
            for result in reversed(p.results):
                if result['device_id'] != current_device['device_id']: break
                result['attempt_index']=current_device['retest_count']
            p.devices.append(current_device); current_device=None
        elif rec not in {"FAR","WRR","TSR","MRR"}: p.findings.append(Finding("warning","UNSUPPORTED_RECORD",f"Record {rec} retained in source but not modeled",line_no))
    if not p.far_seen: p.findings.append(Finding("error","MISSING_FAR","Mandatory FAR record is missing",0))
    if p.lot_id=="UNKNOWN": p.findings.append(Finding("error","MISSING_MIR","Mandatory MIR record is missing",0))
    if not p.wir_seen: p.findings.append(Finding("error","MISSING_WIR","Mandatory WIR record is missing",0))
    return p
