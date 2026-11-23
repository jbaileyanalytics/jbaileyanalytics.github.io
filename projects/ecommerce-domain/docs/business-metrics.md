# Business metrics and interpretation

The first business view asks: **Where are cancellations concentrated, and where should the team investigate fulfillment performance?** It uses Amazon source records dated 2022-03-31 through 2022-06-29. March contains only one day and June ends on the 29th; compare incomplete months cautiously.

## Definitions

| Measure | Definition | Use and boundary |
| --- | --- | --- |
| Sales lines | Count of Amazon source rows in the current filters. | A denominator and workload measure, not unique orders. Multiple rows can share an order ID. |
| Cancelled lines | Count of source rows with status exactly `Cancelled`. | Identifies the volume of records carrying that source status. |
| Cancellation rate | Cancelled lines divided by all source lines within the same filters. | A line-level status mix, not a customer-level or order-level cancellation rate. |
| Returned to seller lines | Count of source rows with status exactly `Shipped - Returned to Seller`. | A source-status count, not the complete return population or a return rate. |
| Inventory SKUs | Count of unambiguous accepted inventory rows. | In the inspected snapshot, 106 rows with missing or duplicated SKUs are rejected from the accepted model and counted in reconciliation. |
| Zero-stock SKUs | Inventory rows with recorded stock equal to zero. | An observation in an undated snapshot, not evidence of stockouts during a sales period or today. |
| Zero-stock share | Zero-stock SKUs divided by accepted inventory SKUs. | Describes the snapshot and follows its own filters. |
| Recorded stock units | Sum of accepted inventory stock observations. | Snapshot total; not inventory turnover, historical stock or a sales-weighted measure. |

## Observations from the unfiltered local snapshot

- **18,332 of 128,975 sales lines** carry `Cancelled` status, a **14.2% line-level cancellation rate**.
- **Merchant** fulfillment has 6,861 cancelled lines out of 39,277 (**17.5%**); **Amazon** fulfillment has 11,471 out of 89,698 (**12.8%**). This is a descriptive comparison, not evidence that fulfillment method caused the difference. Product mix and other differences may matter.
- **1,953 lines** carry `Shipped - Returned to Seller` status. Other return-related statuses exist, so this is not a total returns measure.
- Of 9,165 unambiguous inventory SKU rows, **533 show zero recorded stock** (**5.8%**). The snapshot has no reliable date, so treat it as a data exploration rather than a current replenishment queue.

The sales and fulfillment page has sales month, category, and fulfillment dropdowns, a daily sales-activity chart, and visuals for comparing cancellation counts and rates. Sales month is shown as year and month (`YYYY-MM`) so months from different years remain distinct if the dataset is extended. The inventory tab has separate filters because there is no valid time relationship to the sales observations. The data-quality tab records source coverage and parsing issues.

## Financial measures intentionally deferred

The `Amount` field has 7,795 missing values, and some cancelled or zero-quantity rows have positive amounts. Currency and fee/cost linkage are incomplete in the other files. Before displaying revenue, profit, margin, or a fulfillment cost comparison, define recognition and cancellation rules, validate currency and effective dates, and establish defensible transaction-to-cost links. A price-list MRP or quoted warehouse fee is not a realized sale or incurred transaction cost.
