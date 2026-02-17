# Decision Record: Direct BLS API Evaluation

**Date**: 2026-02-16
**Status**: Adopted

## Context
The project initially relied on FRED for all series, including those sourced from BLS. To improve data freshness and bypass FRED-specific rate limits or delays, a Direct BLS API client was implemented and expanded to a 30-series direct BLS footprint (including coexistence aliases for overlapping concepts).

## Evaluation
- **Implementation Status**: Complete and verified.
- **Client**: `src/fred_macro/clients/bls_client.py` handles authentication (optional key), rate limiting, and data transformation.
- **Coverage**: 30 series (core IDs + `_BLS` coexistence aliases across labor, inflation, and compensation concepts).
- **Catalog Strategy**: Coexisting entries use `series_id` as internal storage ID and `source_series_id` as API fetch ID.
- **Performance**:
    - Direct API access works reliably.
    - Latency is acceptable.
    - Data structure matches the project's `observations` schema.

## Decision
**Adopt Direct BLS API for the implemented 30-series baseline and future BLS-sourced indicators.**
- **Rationale**:
    1.  **Freshness**: Eliminates FRED ingestion lag.
    2.  **Reliability**: Diversifies data dependencies (not single-point-of-failure on FRED).
    3.  **Scalability**: BLS API (especially with key) allows higher throughput for bulk data than FRED's free tier if we expand significantly.

## Next Steps
- Continue using `BLSClient`.
- Encourage registration of BLS API Key for production use.
