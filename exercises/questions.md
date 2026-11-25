# Practice questions

Twenty questions, easiest first. Each one is something a dealership group would actually ask.

**How to use this:** write your answer in a new file under `my_queries/` (for example `my_queries/q01.sql`), run it, and compare your result to the **Check** line. Only open `solutions.sql` once you've tried. If your numbers match, your query is right, even when it looks different from mine.

**The dataset's "today" is 2026-11-01.** Use that date instead of `CURDATE()`, so your answers match the checks.

Every query starts with `USE dealer_practice;` (or pick the database in Workbench's left panel once).

---

## Level 1: Getting data out (`SELECT`, `WHERE`, `ORDER BY`)

**Q1.** List every rooftop in the Rochester market.
*Check: 4 rows.*

**Q2.** Show the used vehicles currently in stock at Genesee Ford (rooftop 5), oldest stock date first.
*Check: 10 rows. The first one was stocked on 2026-08-21.*

**Q3.** Which in-stock vehicles are listed over $60,000? Show VIN, make, model and list price, most expensive first.
*Check: 71 rows. The top one is $94,770.*

**Q4.** How many customers have no email on file?
*Hint: missing values are `NULL`, and you test for them with `IS NULL`, not `= NULL`.*
*Check: 313.*

---

## Level 2: Summarizing (`COUNT`, `SUM`, `AVG`, `GROUP BY`, `HAVING`)

**Q5.** How many units are in stock at each rooftop, split by new and used?
*Check: 24 rows (12 rooftops × 2). Rooftop 1 has 16 new and 12 used.*

**Q6.** For each deal type (Cash, Finance, Lease), show the number of deals and the average front and back gross, rounded to whole dollars.
*Check: Finance has 1,819 deals with an average front gross of $2,086.*

**Q7.** How many units were sold each month in 2026?
*Hint: `DATE_FORMAT(sold_date, '%Y-%m')` turns a date into "2026-03".*
*Check: 10 rows. January has 56.*

**Q8.** Which salespeople sold 25 or more units in 2025?
*Hint: `WHERE` filters rows before grouping. `HAVING` filters the groups after.*
*Check: 9 rows. The top two have 30 each.*

---

## Level 3: Combining tables (`JOIN`)

**Q9.** Show 2026 units sold and total front gross by rooftop **name** (not ID), highest gross first.
*Hint: the name lives in `rooftops`, and the deals live in `deals`. Join on `rooftop_id`.*
*Check: 12 rows. Lakeshore Lexus is first, with 88 units.*

**Q10.** Aged inventory: list used vehicles in stock more than 60 days, with rooftop name and days in stock.
*Hint: `DATEDIFF('2026-11-01', stock_date)` gives days in stock.*
*Check: 30 rows. The oldest has been there 213 days.*

**Q11.** List every October 2026 deal with the customer's full name, the vehicle (year, make and model in one column) and the rooftop name.
*Hint: this joins four tables. `CONCAT(first_name, ' ', last_name)` combines columns.*
*Check: 175 rows.*

**Q12.** Which customers have never bought a vehicle?
*Hint: a `LEFT JOIN` keeps every customer even with no matching deal. Customers with no deal come back with `NULL` in the deal columns.*
*Check: 597 rows.*

---

## Level 4: Real business questions (subqueries and `WITH`)

**Q13.** Service defection list: customers who bought a vehicle before 2025-11-01 and have had **no** service visit since 2025-11-01.
*Hint: build two lists with `WITH` (buyers, and recent service customers), then find who's in the first list but not the second.*
*Check: 322 rows.*

**Q14.** Customer-pay service revenue (labor + parts) by rooftop for 2026, plus each rooftop's percent of the group total.
*Check: 12 rows. Onondaga Jeep is first at about 9.8%.*

**Q15.** Repeat buyers: customers with 2 or more deals, most vehicles first.
*Check: 326 rows. The top customer bought 5.*

**Q16.** Days supply by rooftop: units in stock ÷ average units sold per day over the last 30 days (2026-10-02 to 2026-10-31).
*Check: 12 rows. Onondaga Toyota is highest at 96 days.*

---

## Level 5: Window functions and data cleanup

**Q17.** Rank rooftops within each market by 2026 total gross (front + back).
*Hint: `RANK() OVER (PARTITION BY market ORDER BY ...)`. "Partition by" means start the ranking over for each market.*
*Check: 12 rows. Lakeshore Lexus is #1 in Buffalo.*

**Q18.** For every repeat purchase, show how many days it came after that customer's previous purchase.
*Hint: `LAG(sold_date) OVER (PARTITION BY customer_id ORDER BY sold_date)` looks one row back.*
*Check: 388 rows.*

**Q19.** Find duplicate customers who share an email address, ignoring upper/lower case. Show the email, how many records share it and their customer IDs.
*Hint: `GROUP_CONCAT(customer_id)` lists the IDs in one cell.*
*Check: 53 rows.*

**Q20.** Find duplicate customers who share a phone number once formatting is removed. "(585) 555-0123", "585-555-0123" and "5855550123" are the same number. Show each pair once.
*Hint: strip characters with nested `REPLACE()`, then join the table to itself.*
*Check: 47 pairs.*

---

### Once you finish

Q19 and Q20 overlap. Some duplicates match on email, some on phone and some on both. A good stretch goal: write one query that finds every duplicate pair either way, then build a `customer_master` table that maps each duplicate ID to one "keeper" ID. That's the core problem behind any customer-360 project.
