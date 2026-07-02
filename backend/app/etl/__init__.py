"""Occupation catalog ETL (Wave 2).

Flow: draft (ESCO/O*NET-derived + LLM translate/enrich) → ingest (unpublished)
→ multi-model review → publish approved. Descriptions are gated by the
council; hard facts stay estimates with provenance (DATA_SOURCES §6).
"""
