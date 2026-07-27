from app.parsers import parse_atdf, normalize

def test_atdf_preserves_hierarchy_and_normalizes():
 p=parse_atdf('MIR:L1|P1|T1|Prog\nWIR:W1|1|M|2026-01-01T00:00:00Z\nPIR:D1|1|2|3|C\nPTR:1|VDD|800|500|1000|mV|PASS|P1|2\nPRR:1|1|PASS|0|2')
 assert p.lot_id=='L1' and p.devices[0]['wafer_id']=='W1' and p.results[0]['normalized_value']==0.8 and p.results[0]['normalized_unit']=='V'
def test_missing_mir_is_quality_error(): assert any(x.code=='MISSING_MIR' for x in parse_atdf('WIR:W1').findings)
def test_unit_normalization(): assert normalize(2,'kOhm')==(2000,'Ohm')

def test_current_normalization():
    assert normalize(850, 'mA') == (0.85, 'A')
