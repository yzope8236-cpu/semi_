# STDF V4 Binary Parser Specification

This document details the binary STDF V4 ingestion adapter for YieldScope.

## Warning: Synthetic Validation Only
**STDF V4 core-record MVP support is validated against synthetic fixtures only. Real tester/vendor golden files are required for production accuracy, record-coverage, and performance acceptance.**

## Supported Records & Mapping
The parser supports the core STDF V4 hierarchy required for wafer/die analytics:

| STDF Record | Mapped Fields / Actions |
|-------------|--------------------------|
| **FAR** | Verified as first record. Extracts `STDF_VER`. `CPU_TYPE` used for endianness implicitly handled by `Semi-ATE-STDF`. |
| **MIR** | Extracts `LOT_ID`, `PART_TYP`, `NODE_NAM` (tester), `JOB_NAM` (program). |
| **WIR** | Extracts `WAFER_ID`. Starts a new wafer context. |
| **PIR** | Starts a new test context for `HEAD_NUM` and `SITE_NUM`. |
| **PTR** | Captures parameter results: `TEST_NUM`, `TEST_TXT`, `RESULT`, `LO_LIMIT`, `HI_LIMIT`, `UNITS`. Test Pass/Fail derived from `TEST_FLG` bit 7 or limit checks. |
| **PRR** | Finalizes the die attempt. Extracts `X_COORD`, `Y_COORD`, `HARD_BIN`, `SOFT_BIN`. Device Pass/Fail derived from `PART_FLG` bit 3 or accumulated PTRs. Generates deterministic `device_id`. |
| **WRR** | Extracts `GOOD_CNT` and `PART_CNT` for final reconciliation against parsed totals. |
| **MRR** | Marks file completion. |

## Unsupported Records
Records such as `TSR`, `HBR`, `SBR`, and `PCR` are currently not fully supported by the analytics engine. 
- They are **not** discarded silently. 
- They generate an `UNSUPPORTED_RECORD` finding.
- The raw record contents are retained in `raw_records` provenance.
- The presence of unsupported records does not fail ingestion.

## Retest Rule and Context
All test attempts are retained. The canonical final device result is the final PRR attempt for a shared wafer, site, X coordinate, and Y coordinate.

## Quality Findings
The parser emits specific deterministic data quality warnings and errors:
- `MISSING_FAR`: Missing mandatory FAR record.
- `MISSING_MIR`: Missing mandatory MIR record.
- `MISSING_WIR`: Missing mandatory WIR record.
- `ORPHAN_PIR`: PIR occurs without an active WIR.
- `PTR_WITHOUT_ACTIVE_DEVICE`: PTR occurs without an active PIR context.
- `ORPHAN_PRR`: PRR occurs without an active PIR context.
- `UNSUPPORTED_RECORD`: Found unmapped record type.
- `WRR_COUNT_MISMATCH`: The WRR summary values do not match the parsed PRR device tally.
