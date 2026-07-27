import os
import json
import pytest
from unittest.mock import patch, MagicMock

from apps.api.app.stdf_parser import parse_stdf
from apps.api.app.main import ingest

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'samples', 'stdf-golden')
EXPECTED_DIR = os.path.join(SAMPLES_DIR, 'expected')

def get_stdf_files():
    if not os.path.exists(SAMPLES_DIR):
        return []
    return [f for f in os.listdir(SAMPLES_DIR) if f.endswith('.stdf')]

@pytest.mark.parametrize("filename", get_stdf_files())
def test_stdf_parser_fixtures(filename):
    stdf_path = os.path.join(SAMPLES_DIR, filename)
    json_path = os.path.join(EXPECTED_DIR, filename.replace('.stdf', '.json'))
    
    assert os.path.exists(stdf_path), f"Missing {filename}"
    assert os.path.exists(json_path), f"Missing expected JSON for {filename}"
    
    with open(json_path, 'r') as f:
        expected = json.load(f)
        
    with open(stdf_path, 'rb') as f:
        content = f.read()
        
    parsed = parse_stdf(content, filename)
    
    # 1. Assert FAR, MIR, WIR detected
    assert parsed.far_seen, "FAR not seen"
    assert parsed.lot_id == expected["lot_id"], "LOT_ID mismatch"
    assert parsed.wir_seen, "WIR not seen"
    assert parsed.wafers[0]["wafer_id"] == expected["wafer_id"], "WAFER_ID mismatch"
    
    # 2. Assert exact core record extraction
    assert len(parsed.devices) == expected["device_count"], f"Expected {expected['device_count']} devices, got {len(parsed.devices)}"
    
    final_devices = [d for d in parsed.devices if d.get("is_final_attempt", True)]
    expected_final_count = expected.get("final_device_count", expected["device_count"])
    assert len(final_devices) == expected_final_count, f"Expected {expected_final_count} final devices"
    
    pass_cnt = sum(1 for d in parsed.devices if d["passed"] and d.get("is_final_attempt", True))
    assert pass_cnt == expected["pass_count"], f"Pass count mismatch"
    
    # 3. Assert IDDQ and VTH
    found_tests = {r["test_name"] for r in parsed.results}
    for expected_test in expected["test_names"]:
        assert expected_test in found_tests, f"Expected test {expected_test} not in results"
        
    # 4. Assert X/Y coordinates
    for d in parsed.devices:
        assert "x_coord" in d and d["x_coord"] is not None, "Missing X coordinate"
        assert "y_coord" in d and d["y_coord"] is not None, "Missing Y coordinate"
        
    # 5. Assert raw record provenance
    assert len(parsed.raw_records) > 0, "No raw records retained"
    
    # 6. Specific fixture assertions
    if filename == "03_retest_devices.stdf":
        max_retest = max(d["retest_count"] for d in parsed.devices)
        assert max_retest >= expected["expected_retest_devices"], "Retest evidence missing"
        
        # Assert exact failure counts in retests
        failed_non_final = [d for d in parsed.devices if not d["passed"] and not d.get("is_final_attempt", True)]
        assert len(failed_non_final) == 1, "Exactly one failed non-final attempt must exist"
        
        final_passing = [d for d in parsed.devices if d["passed"] and d.get("is_final_attempt", True)]
        assert len(final_passing) == 2, "Final results must contain two passing physical devices"
        
        # Assert no false WRR_COUNT_MISMATCH
        wrr_mismatch_findings = [f for f in parsed.findings if f.code == "WRR_COUNT_MISMATCH"]
        assert len(wrr_mismatch_findings) == 0, "False WRR_COUNT_MISMATCH event generated"
        
    if filename == "02_edge_failure_cluster.stdf":
        failed_dies = [d for d in parsed.devices if not d["passed"]]
        assert len(failed_dies) == expected["fail_count"], "Fail count mismatch"
        edge_failed = [d for d in failed_dies if d["x_coord"] in (0,9) or d["y_coord"] in (0,9)]
        assert len(edge_failed) > 0, "No edge failures found in edge cluster fixture"

@patch('apps.api.app.main.client')
def test_api_upload_stdf(mock_client_factory):
    mock_client = MagicMock()
    mock_client_factory.return_value = mock_client
    
    with patch('apps.api.app.main.scalar', return_value=0):
        stdf_files = get_stdf_files()
        if not stdf_files:
            pytest.skip("No STDF fixtures found for upload test")
            
        filename = stdf_files[0]
        stdf_path = os.path.join(SAMPLES_DIR, filename)
        with open(stdf_path, 'rb') as f:
            content = f.read()
            
        response = ingest(filename, content)
        
        assert response["status"] == "ingested"
        assert mock_client.insert.called
        
        insert_calls = mock_client.insert.call_args_list
        ingest_file_call = [call for call in insert_calls if call[0][0] == 'ingest_files'][0]
        row = ingest_file_call[0][1][0]
        assert row[3] == "STDF", "source_format not correctly saved as STDF"

@patch('apps.api.app.main.client')
def test_api_upload_stdf_duplicate(mock_client_factory):
    mock_client = MagicMock()
    mock_client_factory.return_value = mock_client
    
    with patch('apps.api.app.main.scalar', return_value=1):
        stdf_files = get_stdf_files()
        if not stdf_files:
            pytest.skip("No STDF fixtures found for upload test")
            
        filename = stdf_files[0]
        stdf_path = os.path.join(SAMPLES_DIR, filename)
        with open(stdf_path, 'rb') as f:
            content = f.read()
            
        response = ingest(filename, content)
        assert response["status"] == "duplicate"
