# STDF Synthetic Fixtures

To ensure continuous parsing robustness without exposing proprietary or confidential client data, YieldScope uses **synthetic STDF V4 binary fixtures**. 

## Why Synthetic Fixtures?
- They are **100% non-confidential**.
- They are guaranteed to be **binary STDF V4 fixtures** containing deterministic test patterns.
- They allow us to write automated regression tests for binary ingestion.

## Supported Records
The synthetic generator utilizes the `Semi-ATE-STDF` library. The following STDF V4 records are targeted:

| Record Type | Description | Status in Generator |
|-------------|-------------|---------------------|
| `FAR`       | File Attributes Record | Supported & Required |
| `MIR`       | Master Information Record | Supported & Required |
| `WIR`       | Wafer Information Record | Supported & Required |
| `PIR`       | Part Information Record | Supported & Required |
| `PTR`       | Parametric Test Record | Supported & Required |
| `PRR`       | Part Results Record | Supported & Required |
| `MRR`       | Master Results Record | Supported & Required |
| `WRR`       | Wafer Results Record | Supported (Optional Summary) |
| `TSR`       | Test Synopsis Record | Supported (Optional Summary) |
| `HBR`       | Hardware Bin Record | Supported (Optional Summary) |
| `SBR`       | Software Bin Record | Supported (Optional Summary) |
| `PCR`       | Part Count Record | Supported (Optional Summary) |

## Limitations
> [!WARNING]
> These synthetic fixtures **do not prove compatibility** with every tester vendor's specific STDF dialect. Testers (like Advantest, Teradyne, or Cohu) often implement custom DTR (Data Type Records) and have varying adherence to the STDF V4 spec.

## Development Setup

The `Semi-ATE-STDF` library is required *only* for fixture generation, not for production runtime of the FastAPI application.

**Install the generation dependency:**
```bash
pip install -r apps/api/requirements-dev.txt
# or directly:
pip install Semi-ATE-STDF>=1.0.0
```

## Commands

### 1. Generate Fixtures
Run the generator script to create the binary `.stdf` files and their expected `.json` metadata counterparts in `samples/stdf-golden/`:
```bash
python scripts/generate_synthetic_stdf.py
```

### 2. Validate Fixtures
Run the automated test suite to ensure the generator produced valid binaries with the expected STDF records and values:
```bash
python -m pytest apps/api/tests/test_synthetic_stdf_fixtures.py -q
```
