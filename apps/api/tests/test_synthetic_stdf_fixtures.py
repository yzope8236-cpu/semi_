import os
import json
import pytest

try:
    from Semi_ATE import STDF
    HAVE_SEMI_ATE = True
except ImportError:
    HAVE_SEMI_ATE = False

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'samples', 'stdf-golden')
EXPECTED_DIR = os.path.join(SAMPLES_DIR, 'expected')

@pytest.fixture
def required_records():
    return ["FAR", "MIR", "WIR", "PIR", "PTR", "PRR", "WRR", "MRR"]

def get_stdf_files():
    if not os.path.exists(SAMPLES_DIR):
        return []
    return [f for f in os.listdir(SAMPLES_DIR) if f.endswith('.stdf')]

@pytest.mark.skipif(not HAVE_SEMI_ATE, reason="Semi-ATE-STDF library not installed")
@pytest.mark.parametrize("filename", get_stdf_files())
def test_synthetic_stdf_fixtures(filename, required_records):
    filepath = os.path.join(SAMPLES_DIR, filename)
    expected_filepath = os.path.join(EXPECTED_DIR, filename.replace('.stdf', '.json'))
    
    assert os.path.exists(expected_filepath), f"Missing expected JSON for {filename}"
    
    with open(expected_filepath, 'r') as f:
        expected = json.load(f)
        
    records = []
    # Read the STDF file back using the same library to validate
    # records_from_file yields each record
    try:
        for rec in STDF.records_from_file(filepath):
            records.append(rec)
    except Exception as e:
        pytest.fail(f"Failed to read STDF file {filename}: {e}")
        
    assert len(records) > 0, "No records found in STDF file"
    
    # 1. First record is FAR
    assert type(records[0]).__name__ == "FAR", "First record is not FAR"
    
    # 2. FAR reports STDF V4
    far_fields = records[0].to_dict()
    assert int(far_fields["STDF_VER"]) == 4, (
        f"STDF version is not 4: {far_fields.get('STDF_VER')}"
    )
    
    # 3. Required record types exist
    found_types = {type(rec).__name__ for rec in records}
    for req in required_records:
        assert req in found_types, f"Required record {req} not found in {filename}"
        
    # Count specific records
    wir_count = sum(1 for r in records if type(r).__name__ == "WIR")
    pir_count = sum(1 for r in records if type(r).__name__ == "PIR")
    prr_count = sum(1 for r in records if type(r).__name__ == "PRR")
    ptr_count = sum(1 for r in records if type(r).__name__ == "PTR")
    
    assert wir_count >= 1, "Expected at least 1 WIR"
    assert pir_count > 0, "Expected at least 1 PIR"
    assert prr_count > 0, "Expected at least 1 PRR"
    
    # Check test names (PTR)
    found_tests = {
        str(r.to_dict().get("TEST_TXT", ""))
        for r in records
        if type(r).__name__ == "PTR"
    }
    for expected_test in expected.get("test_names", []):
        assert expected_test in found_tests, f"Test {expected_test} not found in PTR records"
        
    # Check X/Y coordinates in PRR
    prrs = [r for r in records if type(r).__name__ == "PRR"]
    for prr in prrs:
        prr_fields = prr.to_dict()

        assert prr_fields.get("X_COORD") is not None, (
            f"PRR missing X_COORD: {prr_fields}"
        )

        assert prr_fields.get("Y_COORD") is not None, (
            f"PRR missing Y_COORD: {prr_fields}"
        )
        
    # Validate specific fixtures
    if filename == "03_retest_devices.stdf":
        part_ids = [prr.to_dict().get("PART_ID", "") for prr in prrs]
        retested = len(part_ids) - len(set(part_ids))
        assert retested >= expected["expected_retest_devices"], "Retest devices not found"
        
    if filename == "04_multi_site_bins.stdf":
        sites = {prr.to_dict().get("SITE_NUM", -1) for prr in prrs}
        assert len(sites) == len(expected["site_numbers"]), "Mismatch in expected multi-site values"
