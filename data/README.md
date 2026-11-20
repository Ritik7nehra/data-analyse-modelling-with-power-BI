# Data

| File | Used by | Rows | Source |
|---|---|---|---|
| `superstore_orders.csv` | `superstore_sales_analysis.ipynb` | 9,994 | Superstore sample dataset, extracted from the Power BI model |
| `nigeria_covid19_by_state.csv` | `nigeria_covid19_analysis.ipynb` | 37 | NCDC Nigeria snapshot embedded in the Power BI dashboard |
| `disney_movies.csv` | `disney_box_office_analysis.ipynb` | 579 | **Not included** (see below) |

The first two files are generated from the `.pbix` files by `scripts/export_pbix_data.py` and can be regenerated at any time.

## `superstore_orders.csv`

One row per order line: the `Orders` fact table joined to `Customers`, `Geography` and `Products` using the same keys as the Power BI relationships.
Customer names are omitted; `Customer ID` is kept. Columns: Order ID, Order Date, Ship Date, Ship Mode, Customer ID, Sales, Quantity, Discount, Profit, Segment, City, State, Postal Code, Region, Category, Sub-Category, Product Name.

## `nigeria_covid19_by_state.csv`

Cumulative cases by state: State, Confirmed Cases, Active Cases, Discharged Cases, Deaths Recorded. A single snapshot, dated to about 31 May 2022 by the source file's metadata.

## `disney_movies.csv` (add this yourself)

The Disney notebook expects a public Disney box-office CSV (commonly distributed on Kaggle) with these columns:

| Column | Description |
|---|---|
| `movie_title` | Film title |
| `release_date` | Release date (`YYYY-MM-DD`) |
| `genre` | Single genre label (may be missing) |
| `mpaa_rating` | MPAA rating (may be missing) |
| `total_gross` | Nominal gross in dollars |
| `inflation_adjusted_gross` | Gross adjusted to today's dollars |

Save it here as `data/disney_movies.csv`. The original dataset has 579 rows, 17 missing genres and 56 missing ratings.
Check the dataset's licence before committing a copy to a public repository.
