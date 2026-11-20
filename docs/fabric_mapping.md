# Microsoft Fabric mapping

How each part of this project corresponds to a Microsoft Fabric item.

> **Status: a mapping, not an implementation.** Nothing here has been run in Fabric. It records how the pieces would move and what would need to change. Product names, features and limits change, so check Microsoft's current documentation before building.

## Component map

| This repo | Fabric item | Notes |
|---|---|---|
| `data/superstore_orders.csv` | **Lakehouse** Files (OneLake) | Land the raw file in the Lakehouse |
| `powerquery/*.pq` | **Dataflow Gen2** | Dataflows Gen2 use Power Query, so the M queries are the natural starting point. The local `SourcePath` would be replaced by a OneLake, SharePoint or Azure source |
| `src/superstore_pipeline` (extract, validate, mask) | **Notebook** (Python or Spark) | The logic is plain pandas. Install the package or paste the modules into a notebook. Secrets belong in Azure Key Vault, not in notebook text |
| `warehouse/duckdb/models/*.sql` | **Warehouse** (T-SQL) or Lakehouse SQL endpoint | See "SQL dialect" below |
| `build/superstore.duckdb` | Lakehouse Delta tables or Warehouse tables | The star schema maps one-to-one |
| `reports/marts/*.csv` | Lakehouse tables (gold layer) | A medallion layout: raw (bronze), masked staging (silver), star schema and marts (gold) |
| `bi/metrics.yml` and `powerbi/proposed_measures.dax` | **Semantic model** | Same measures; Direct Lake mode reads Delta tables without an import step |
| `powerbi/*.pbix` | **Power BI report** in a Fabric workspace | Publish the report on top of the semantic model |
| `superstore_pipeline.runner` (step DAG, run log) | **Data Factory pipeline** | Activities: Dataflow Gen2, Notebook, Warehouse script, semantic model refresh, with failure paths |
| `.github/workflows/*` | **Deployment pipelines** and Git integration | Dev, test and prod workspaces, with Git as the source of truth |
| `docs/data_masking.md` | Dynamic data masking, sensitivity labels, row-level security | See the table in that document |

## SQL dialect

The models were written and tested in DuckDB. Constructs that would need rewriting for T-SQL include `CREATE OR REPLACE TABLE ... AS`, the `FILTER (WHERE ...)` aggregate clause and `ANY_VALUE`. Window functions (`LAG`, `NTILE`, `DENSE_RANK`), `ROLLUP` and CTEs are standard and should carry over, but each model should be re-run and re-checked against the Python results in `tests/` after porting.

## Suggested order to try it

1. Create a free Fabric trial or use an existing capacity (availability and terms change; check Microsoft's site).
2. Create a Lakehouse and upload `data/superstore_orders.csv`.
3. Recreate the staging and dimension queries in a Dataflow Gen2 from `powerquery/`.
4. Build the gold tables, then a semantic model, and rebuild the measures from `powerbi/proposed_measures.dax`.
5. Check the totals against the control totals in `config/pipeline.yml`: 9,994 rows, $2,297,200.86 sales, $286,397.02 profit.
6. Wire the steps into a Data Factory pipeline with a failure path, and note what you learned back into this document.

Only claim Fabric experience once you have done steps 1 to 5 yourself.
