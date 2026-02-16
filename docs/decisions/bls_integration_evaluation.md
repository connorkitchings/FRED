# Decision Record: Direct BLS API Evaluation

**Date**: 2026-02-16
**Status**: Adopted

## Context
The project initially relied on FRED for all series, including those sourced from BLS. To improve data freshness and bypass FRED-specific rate limits or delays, a Direct BLS API client was implemented for a subset of series (25 indicators).

## Evaluation
- **Implementation Status**: Complete and verified.
- **Client**: `src/fred_macro/clients/bls_client.py` handles authentication (optional key), rate limiting, and data transformation.
- **Coverage**: 25 series (Core, Extended Employment, Price Detail, Regional/Demographics).
- **Performance**:
    - Direct API access works reliably.
    - Latency is acceptable.
    - Data structure matches the project's `observations` schema.

## Decision
**Adopt Direct BLS API for the implemented 25 series and future BLS-sourced indicators.**
- **Rationale**:
    1.  **Freshness**: Eliminates FRED ingestion lag.
    2.  **Reliability**: Diversifies data dependencies (not single-point-of-failure on FRED).
    3.  **Scalability**: BLS API (especially with key) allows higher throughput for bulk data than FRED's free tier if we expand significantly.

## Next Steps
- Continue using `BLSClient`.
- Encourage registration of BLS API Key for production use.
