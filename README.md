# SQL practice: dealership database

A hands-on MySQL practice project built around a made-up auto dealership group. There are 12 rooftops across Buffalo, Rochester and Syracuse, with inventory, deals, customers and service repair orders.

**Everything in here is invented.** No real dealership, customer or vehicle data is in this repo, and none should be added to it.

## What's inside

```
sql/
  01_create_schema.sql   builds the database and its 5 tables
  02_seed_data.sql       fills them with ~13,000 rows of fake data
exercises/
  questions.md           20 practice questions, easiest first, with answer checks
  solutions.sql          one answer for each question (try first!)
my_queries/              your own work goes here
scripts/
  generate_seed_data.py  the script that made the fake data (optional)
```

### The tables

| Table | One row per | Rows |
|---|---|---|
| `rooftops` | dealership location | 12 |
| `customers` | person (75 planted duplicates for cleanup practice) | 2,875 |
| `vehicles` | car that's been in stock, sold or still on the lot | 3,000 |
| `deals` | vehicle sale | 2,666 |
| `service_ros` | service repair order | 4,532 |

How they connect: `deals` links a `customer` to a `vehicle` (by `vin`) at a `rooftop`. `service_ros` links a customer and a vehicle to the rooftop that serviced it. The dataset's "today" is **2026-11-01**.

---

## Setup (one time, about 30 minutes)

### 1. Create the MySQL server in Azure

1. In the [Azure portal](https://portal.azure.com), search for **Azure Database for MySQL flexible servers** and click **Create**.
2. **Basics** tab:
   - Resource group: create a new one, e.g. `sql-practice-rg` (it makes cleanup easy later).
   - Server name: anything unique, e.g. `dhass-sql-practice`.
   - Region: **East US** or **East US 2**.
   - MySQL version: **8.0**.
   - Workload type: **For development or hobby projects**.
   - Compute + storage: click **Configure server** and choose **Burstable, B1ms**, 20 GiB storage, high availability **off**.
   - Authentication: **MySQL authentication only**. Pick an admin username and a strong password, and save them in your password manager.
3. **Networking** tab:
   - Connectivity method: **Public access**.
   - Under Firewall rules, click **+ Add current client IP address**. This lets only your current network in.
4. **Review + create**. Check the monthly cost estimate on that page before you click Create, then wait a few minutes for it to deploy.

**To keep costs low:** when you're done practicing, open the server's **Overview** page and click **Stop**. A stopped server doesn't charge for compute (storage still costs a little). Azure automatically restarts a stopped server after 30 days, so stop it again if you take a long break. When you're finished with the project for good, delete the whole `sql-practice-rg` resource group.

If you practice from a different network later (a coffee shop, for example), add that IP under the server's **Networking** page.

### 2. Install MySQL Workbench and connect

1. Download **MySQL Workbench** from [dev.mysql.com/downloads/workbench](https://dev.mysql.com/downloads/workbench/) and install it.
2. Click the **+** next to "MySQL Connections" and fill in:
   - Connection name: `Azure practice`
   - Hostname: your server name from Azure's Overview page, e.g. `dhass-sql-practice.mysql.database.azure.com`
   - Port: `3306`
   - Username: the admin username you picked
   - **SSL** tab: set "Use SSL" to **Require**. Azure only accepts encrypted connections.
3. Click **Test Connection**, enter your password, then **OK**.

### 3. Build and fill the database

In Workbench, open your connection, then:

1. **File → Open SQL Script** → `sql/01_create_schema.sql` → click the lightning bolt to run it.
2. **File → Open SQL Script** → `sql/02_seed_data.sql` → run it. This one takes a little longer.
3. Open a new query tab and run this to check it worked:

```sql
USE dealer_practice;
SELECT COUNT(*) FROM deals;   -- should return 2666
```

To start over at any point, run both scripts again. The first one wipes and rebuilds everything.

---

## How to practice

1. Open `exercises/questions.md`.
2. Write your answer in a new query tab. Save it as `my_queries/q01.sql`, `q02.sql` and so on.
3. Compare your result to the **Check** line under the question.
4. Stuck? Peek at `exercises/solutions.sql`, then close it and write the query yourself.

### Quick reference

```sql
SELECT columns FROM table WHERE condition ORDER BY column;   -- get rows
SELECT col, COUNT(*) FROM table GROUP BY col;               -- summarize
SELECT ... FROM a JOIN b ON a.id = b.id;                    -- combine tables
SELECT ... FROM a LEFT JOIN b ON ... WHERE b.id IS NULL;    -- rows in a with no match in b
WITH step1 AS (SELECT ...) SELECT ... FROM step1;           -- break a problem into steps
```

The order MySQL actually runs a query in (handy when something doesn't work):
`FROM / JOIN` → `WHERE` → `GROUP BY` → `HAVING` → `SELECT` → `ORDER BY` → `LIMIT`

## Regenerating the data (optional)

The fake data comes from `scripts/generate_seed_data.py` with a fixed random seed, so it's identical every time. To change it (more stores, more years), edit the script and run `python scripts/generate_seed_data.py`. That rewrites `sql/02_seed_data.sql`, and the answer checks in `questions.md` will no longer match.
