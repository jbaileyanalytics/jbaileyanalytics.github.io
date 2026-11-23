# Pipeline audit

Operational audit records are separate from the business-facing market data model. The local initial build stores source filenames, SHA-256 hashes and row counts, links each price record to its file and CSV line, and records field-specific quality findings with original values. The acquisition command separately writes a download manifest. The manifest records the observed files but does not independently establish a Kaggle version. A scheduled full rebuild workflow is prepared but has not yet been verified on GitHub.

Run history, source retention, version resolution, and revision handling are not implemented. A hash identifies file content, not the reason it changed. The initial builder refuses to replace an existing database; incremental updates require a correction and audit strategy.
