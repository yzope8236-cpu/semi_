import os
import tempfile
from datetime import datetime, timezone

try:
    from Semi_ATE import STDF
    HAVE_SEMI_ATE = True
except ImportError:
    HAVE_SEMI_ATE = False

from .parsers import Parsed, Finding, normalize

def get_bit(bit_array, index, default='0'):
    """Safely get a bit from a B*1 bit array (list of strings)."""
    if isinstance(bit_array, list) and len(bit_array) > index:
        return bit_array[index]
    return default

def parse_stdf(content: bytes, source_name: str) -> Parsed:
    if not HAVE_SEMI_ATE:
        raise RuntimeError("Semi-ATE-STDF library is not installed.")

    p = Parsed()
    
    temp_path = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".stdf") as tf:
        tf.write(content)
        tf.flush()
        temp_path = tf.name

    try:
        active_devices = {}
        current_wafer = "UNKNOWN"
        record_number = 0
        wrr_pass_count = None
        wrr_fail_count = None

        for rec in STDF.records_from_file(temp_path):
            record_number += 1
            rec_id = rec.id
            rec_dict = rec.to_dict()
            
            p.records += 1
            p.raw_records.append({
                "offset": record_number,
                "record_type": rec_id,
                "record_fields": str(rec_dict)
            })

            if rec_id == "FAR":
                p.far_seen = True
                p.stdf_version = str(rec_dict.get("STDF_VER", "UNKNOWN"))
                p.firmware_version = "UNKNOWN"
            
            elif rec_id == "MIR":
                p.lot_id = str(rec_dict.get("LOT_ID", p.lot_id))
                p.part_id = str(rec_dict.get("PART_TYP", p.part_id))
                p.tester_id = str(rec_dict.get("NODE_NAM", p.tester_id))
                p.program_name = str(rec_dict.get("JOB_NAM", p.program_name))
                
            elif rec_id == "WIR":
                p.wir_seen = True
                wafer_id = str(rec_dict.get("WAFER_ID", ""))
                if not wafer_id:
                    p.findings.append(Finding("error", "MISSING_WAFER_ID", "WIR needs wafer ID", record_number))
                current_wafer = wafer_id or current_wafer
                
                start_t = rec_dict.get("START_T")
                if isinstance(start_t, int) and start_t > 0:
                    start_time = datetime.fromtimestamp(start_t, tz=timezone.utc)
                else:
                    start_time = datetime.now(timezone.utc)
                
                p.wafers.append({
                    "wafer_id": current_wafer,
                    "wafer_index": len(p.wafers) + 1,
                    "mask_id": "",
                    "start_time": start_time
                })
                
            elif rec_id == "PIR":
                if not p.wir_seen:
                    p.findings.append(Finding("error", "ORPHAN_PIR", "PIR precedes WIR", record_number))
                
                head = rec_dict.get("HEAD_NUM", 1)
                site = rec_dict.get("SITE_NUM", 1)
                
                active_devices[(head, site)] = {
                    "wafer_id": current_wafer,
                    "head": head,
                    "site": site,
                    "retest_count": 0,
                    "tested_at": datetime.now(timezone.utc),
                    "temp_ptr_results": []
                }
                
            elif rec_id == "PTR":
                head = rec_dict.get("HEAD_NUM", 1)
                site = rec_dict.get("SITE_NUM", 1)
                
                active_dev = active_devices.get((head, site))
                if not active_dev:
                    p.findings.append(Finding("error", "PTR_WITHOUT_ACTIVE_DEVICE", f"PTR found but no active PIR for head {head} site {site}", record_number))
                    continue
                    
                test_num = rec_dict.get("TEST_NUM", 0)
                test_txt = str(rec_dict.get("TEST_TXT", "")).strip()
                test_name = test_txt if test_txt else f"TEST_{test_num}"
                
                value = rec_dict.get("RESULT")
                lo = rec_dict.get("LO_LIMIT")
                hi = rec_dict.get("HI_LIMIT")
                unit = str(rec_dict.get("UNITS", ""))
                
                test_flg = rec_dict.get("TEST_FLG")
                passed = True
                if isinstance(test_flg, list) and len(test_flg) >= 8:
                    if test_flg[7] == '1':
                        passed = False
                else:
                    if value is not None:
                        passed = True
                        if lo is not None and value < lo: passed = False
                        if hi is not None and value > hi: passed = False

                normalized_val, normalized_unit = normalize(value, unit)
                
                active_dev["temp_ptr_results"].append({
                    "test_num": int(test_num) if test_num is not None else 0,
                    "test_name": test_name,
                    "measured_value": value,
                    "lower_limit": lo,
                    "upper_limit": hi,
                    "normalized_value": normalized_val,
                    "normalized_unit": normalized_unit,
                    "original_unit": unit,
                    "passed": int(passed),
                    "pin_name": "",
                    "elapsed_ms": None
                })
                
            elif rec_id == "PRR":
                head = rec_dict.get("HEAD_NUM", 1)
                site = rec_dict.get("SITE_NUM", 1)
                
                active_dev = active_devices.get((head, site))
                if not active_dev:
                    p.findings.append(Finding("error", "ORPHAN_PRR", f"PRR found but no active PIR for head {head} site {site}", record_number))
                    continue
                
                x = rec_dict.get("X_COORD", 0)
                y = rec_dict.get("Y_COORD", 0)
                hbin = rec_dict.get("HARD_BIN", 0)
                sbin = rec_dict.get("SOFT_BIN", 0)
                
                part_flg = rec_dict.get("PART_FLG")
                passed = None
                if isinstance(part_flg, list) and len(part_flg) >= 4:
                    if part_flg[3] == '1':
                        passed = False
                    elif part_flg[3] == '0':
                        if len(part_flg) >= 5 and part_flg[4] == '0':
                            passed = True
                
                if passed is None:
                    passed = all(r["passed"] for r in active_dev["temp_ptr_results"]) if active_dev["temp_ptr_results"] else True
                
                attempt_index = sum(1 for d in p.devices if d['wafer_id'] == active_dev['wafer_id'] and d['x_coord'] == x and d['y_coord'] == y)
                device_id = f"{active_dev['wafer_id']}-{site}-{x}-{y}-{attempt_index}"
                
                test_t = rec_dict.get("TEST_T", None)
                test_time_ms = test_t if isinstance(test_t, (int, float)) else None

                for d in p.devices:
                    if d['wafer_id'] == active_dev['wafer_id'] and d['x_coord'] == x and d['y_coord'] == y:
                        d["is_final_attempt"] = False

                device_entry = {
                    "device_id": device_id,
                    "wafer_id": active_dev["wafer_id"],
                    "site": site,
                    "channel": "",
                    "x_coord": x,
                    "y_coord": y,
                    "hardware_bin": hbin,
                    "software_bin": sbin,
                    "passed": int(passed),
                    "retest_count": attempt_index,
                    "test_time_ms": test_time_ms,
                    "tested_at": active_dev["tested_at"],
                    "is_final_attempt": True
                }
                p.devices.append(device_entry)
                
                for r in active_dev["temp_ptr_results"]:
                    r["device_id"] = device_id
                    r["wafer_id"] = active_dev["wafer_id"]
                    r["attempt_index"] = attempt_index
                    r["tested_at"] = active_dev["tested_at"]
                    p.results.append(r)
                
                del active_devices[(head, site)]
                
            elif rec_id == "WRR":
                good_cnt = rec_dict.get("GOOD_CNT")
                part_cnt = rec_dict.get("PART_CNT")
                if good_cnt is not None and part_cnt is not None:
                    wrr_pass_count = good_cnt
                    wrr_fail_count = part_cnt - good_cnt
                
            elif rec_id == "MRR":
                pass
                
            else:
                p.findings.append(Finding("warning", "UNSUPPORTED_RECORD", f"Unsupported record {rec_id}", record_number))

    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

    if not p.far_seen:
        p.findings.append(Finding("error", "MISSING_FAR", "Mandatory FAR record is missing", 0))
    if p.lot_id == "UNKNOWN":
        p.findings.append(Finding("error", "MISSING_MIR", "Mandatory MIR record is missing", 0))
    if not p.wir_seen:
        p.findings.append(Finding("error", "MISSING_WIR", "Mandatory WIR record is missing", 0))
        
    if wrr_pass_count is not None and wrr_fail_count is not None:
        parsed_pass = sum(1 for d in p.devices if d["passed"] and d.get("is_final_attempt", True))
        parsed_fail = sum(1 for d in p.devices if not d["passed"] and d.get("is_final_attempt", True))
        if parsed_pass != wrr_pass_count or parsed_fail != wrr_fail_count:
            p.findings.append(Finding(
                "warning", 
                "WRR_COUNT_MISMATCH", 
                f"WRR reported {wrr_pass_count} pass / {wrr_fail_count} fail, but parsed {parsed_pass} pass / {parsed_fail} fail", 
                0
            ))
            
    return p
