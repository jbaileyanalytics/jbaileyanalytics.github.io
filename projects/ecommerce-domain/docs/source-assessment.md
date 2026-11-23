# Source assessment

The dataset description suggests profitability analyses, but source inspection does not establish the cost definitions, fulfillment-event linkage, currency, complete fee history, effective dates, or revenue recognition needed for actual profit. The following scope reflects observed files, not claims about a real company's outcomes. Row counts are from the local copy inspected on 2026-11-16.

The [read-only assessment notebook](../notebooks/source_assessment.ipynb) demonstrates the aggregate checks behind these findings, including source inventory, missing values, validation rules, SKU comparisons, and price parsing. It includes saved aggregate results from the inspected snapshot; rerunning it requires local source files, and a different file version can produce different counts.

| Source | Rows | Likely grain and use | Quality and decision |
| --- | ---: | --- | --- |
| Amazon Sale Report.csv | 128,975 | One source sales record; order IDs repeat across records. | 91 sale dates from 2022-03-31 through 2022-06-29; 7,795 missing amount/currency values; 12,807 zero-quantity rows, including 5,136 with a positive amount. Order ID + SKU repeats, so preserve each source row. Included in the current lakehouse. |
| Sale Report.csv | 9,271 | Inventory observation, generally per SKU. | 83 missing SKU rows and 23 rows whose normalized SKU appears more than once. Snapshot date is absent. Exclude those 106 rows from the accepted inventory model; do not sum stock by historical order date. Included in the current lakehouse. |
| International sale Report.csv | 37,432 | Appears to contain international sales records mixed with non-record or summary rows. | 18,635 accepted transaction-like rows; 18,797 excluded for invalid date or required measure. Accepted rows include 1,417 with no SKU; currency is unknown. Customer names excluded from modeled output. |
| May-2022.csv | 1,330 | SKU and channel price reference, apparently a named-period sheet. | Included as source rows and unpivoted values. SKU convention differs from the Amazon extract; TP and price semantics and effective dates are unverified. |
| P  L March 2021.csv | 1,330 | SKU pricing and TP1/TP2 reference, apparently a named-period sheet. | Included separately; verify period, units and cost meaning. Do not assume TP is transaction-specific cost. |
| Expense IIGF.csv | 17 | Spreadsheet-style mixed receipts and expenses. | All rows retained as observations; mixed headers and possible summaries retained without classifying them as transactions. Unknown allocation to orders and period. |
| Cloud Warehouse Compersion Chart.csv | 50 | Spreadsheet-style Shiprocket/INCREFF comparison. | All rows retained as source text; possible rate comparisons have not been validated. No confirmed transaction linkage or realized fulfillment volumes. |

## Cross-source findings

In the inspected snapshot, 121,271 Amazon rows matched an unambiguous inventory SKU after trim and uppercase normalization. This is a row-level match count, not a match rate for revenue or a guarantee of common ownership, timing, or causation. None of the 2,660 price-sheet rows matched an Amazon SKU under that same rule. The 30,590 unpivoted price observations include 746 unparsed values, preserved as text. Do not force matches; investigate source ownership and SKU mappings first.

## Decisions and questions

- Separate source rows, SKU references, and inventory observations; avoid joining stock to every sale and summing the repeated quantity.
- Preserve the source status and amount. Define business-approved status and revenue policies before creating revenue measures.
- No channel-profit, warehouse-profit, or profitability ranking will be claimed without trustworthy transaction costs, currency, fees, and effective dates.

**Source:** [E-Commerce Sales Dataset by thedevastator on Kaggle](https://www.kaggle.com/datasets/thedevastator/unlock-profits-with-e-commerce-sales-data).
