"""
Generates sql/02_seed_data.sql: invented dealership data for SQL practice.

Nothing here comes from a real dealership. Names, VINs, emails and phone
numbers are random. Emails use reserved example.* domains and phone numbers
use the 555 prefix so none of them belong to a real person.

Run:  python scripts/generate_seed_data.py
The random seed is fixed, so every run produces the same data and the
answers in exercises/solutions.sql stay the same.
"""

import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

AS_OF = date(2026, 11, 1)          # "today" for the dataset
START = date(2024, 1, 1)
OUT = Path(__file__).resolve().parent.parent / "sql" / "02_seed_data.sql"

# ---------------------------------------------------------------- rooftops
ROOFTOPS = [
    # id, name, brand, market, luxury, opened
    (1,  "Lakeshore Ford",        "Ford",      "Buffalo",   0, date(1998, 5, 1)),
    (2,  "Lakeshore Toyota",      "Toyota",    "Buffalo",   0, date(2004, 3, 1)),
    (3,  "Lakeshore Chevrolet",   "Chevrolet", "Buffalo",   0, date(2009, 8, 1)),
    (4,  "Lakeshore Lexus",       "Lexus",     "Buffalo",   1, date(2012, 6, 1)),
    (5,  "Genesee Ford",          "Ford",      "Rochester", 0, date(2011, 4, 1)),
    (6,  "Genesee Honda",         "Honda",     "Rochester", 0, date(2015, 9, 1)),
    (7,  "Genesee Subaru",        "Subaru",    "Rochester", 0, date(2018, 2, 1)),
    (8,  "Genesee BMW",           "BMW",       "Rochester", 1, date(2019, 7, 1)),
    (9,  "Onondaga Toyota",       "Toyota",    "Syracuse",  0, date(2016, 1, 1)),
    (10, "Onondaga Hyundai",      "Hyundai",   "Syracuse",  0, date(2020, 10, 1)),
    (11, "Onondaga Jeep",         "Jeep",      "Syracuse",  0, date(2021, 5, 1)),
    (12, "Onondaga Audi",         "Audi",      "Syracuse",  1, date(2024, 4, 1)),
]

MODELS = {
    "Ford":      ["F-150", "Escape", "Explorer", "Bronco Sport", "Mustang", "Maverick"],
    "Toyota":    ["Camry", "RAV4", "Highlander", "Tacoma", "Corolla", "Tundra"],
    "Chevrolet": ["Silverado", "Equinox", "Traverse", "Tahoe", "Malibu"],
    "Lexus":     ["RX 350", "NX 350", "ES 350", "GX 550"],
    "Honda":     ["CR-V", "Civic", "Accord", "Pilot", "HR-V"],
    "Subaru":    ["Outback", "Forester", "Crosstrek", "Ascent"],
    "BMW":       ["X3", "X5", "3 Series", "5 Series"],
    "Hyundai":   ["Tucson", "Santa Fe", "Elantra", "Palisade"],
    "Jeep":      ["Grand Cherokee", "Wrangler", "Compass", "Gladiator"],
    "Audi":      ["Q5", "Q7", "A4", "A6"],
    "Nissan":    ["Rogue", "Altima", "Pathfinder"],
    "Kia":       ["Sportage", "Telluride", "Sorento"],
}
LUXURY_MAKES = {"Lexus", "BMW", "Audi"}
ZIPS = {
    "Buffalo":   ["14201", "14215", "14221", "14075", "14094", "14217"],
    "Rochester": ["14604", "14610", "14618", "14580", "14526", "14450"],
    "Syracuse":  ["13202", "13205", "13210", "13027", "13088", "13104"],
}
AREA = {"Buffalo": "716", "Rochester": "585", "Syracuse": "315"}

FIRST = ["James", "Mary", "Robert", "Patricia", "Michael", "Jennifer", "William",
         "Linda", "David", "Elizabeth", "Richard", "Barbara", "Joseph", "Susan",
         "Thomas", "Jessica", "Christopher", "Sarah", "Daniel", "Karen", "Matthew",
         "Lisa", "Anthony", "Nancy", "Mark", "Sandra", "Steven", "Ashley", "Paul",
         "Emily", "Andrew", "Michelle", "Joshua", "Amanda", "Kevin", "Melissa",
         "Brian", "Stephanie", "Nicholas", "Rebecca", "Eric", "Laura", "Ryan",
         "Katherine", "Jacob", "Rachel", "Gary", "Megan", "Tyler", "Olivia",
         "Brandon", "Hannah", "Justin", "Grace", "Aaron", "Sophia", "Kyle", "Chloe"]
LAST = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis",
        "Wilson", "Anderson", "Taylor", "Thomas", "Moore", "Martin", "Jackson",
        "Thompson", "White", "Harris", "Clark", "Lewis", "Robinson", "Walker",
        "Young", "Allen", "King", "Wright", "Scott", "Hill", "Green", "Adams",
        "Baker", "Nelson", "Carter", "Mitchell", "Roberts", "Turner", "Phillips",
        "Campbell", "Parker", "Evans", "Edwards", "Collins", "Stewart", "Morris",
        "Murphy", "Cook", "Rogers", "Morgan", "Cooper", "Peterson", "Reed",
        "Bailey", "Kelly", "Howard", "Russo", "Romano", "Kowalski", "Nowak",
        "Schmidt", "Fischer", "O'Brien", "Sullivan", "Ryan", "Murray", "Quinn"]
NICK = {"Robert": "Bob", "William": "Bill", "Michael": "Mike", "Jennifer": "Jen",
        "Elizabeth": "Liz", "James": "Jim", "Katherine": "Kate", "Christopher": "Chris",
        "Joseph": "Joe", "Daniel": "Dan", "Anthony": "Tony", "Patricia": "Pat",
        "Thomas": "Tom", "Nicholas": "Nick", "Matthew": "Matt", "Steven": "Steve",
        "Andrew": "Andy", "Rebecca": "Becky", "Joshua": "Josh"}
DOMAINS = ["example.com", "example.net", "example.org"]

VIN_CHARS = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"


def rand_date(a, b):
    return a + timedelta(days=random.randint(0, (b - a).days))


def sql_val(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, date):
        return f"'{v.isoformat()}'"
    return "'" + str(v).replace("'", "''") + "'"


def inserts(table, cols, rows, batch=500):
    out = []
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        vals = ",\n".join("(" + ", ".join(sql_val(v) for v in r) + ")" for r in chunk)
        out.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES\n{vals};\n")
    return out


# ---------------------------------------------------------------- salespeople
salespeople = {}
for r in ROOFTOPS:
    salespeople[r[0]] = [f"{random.choice(FIRST)} {random.choice(LAST)}"
                         for _ in range(random.randint(3, 5))]

# ---------------------------------------------------------------- customers
customers = []
used_emails, used_phones = set(), set()
for cid in range(1, 2801):
    market = random.choice(list(ZIPS))
    fn, ln = random.choice(FIRST), random.choice(LAST)
    email = None
    if random.random() > 0.10:
        while True:
            email = f"{fn.lower()}.{ln.lower().replace(chr(39), '')}{random.randint(1, 999)}@{random.choice(DOMAINS)}"
            if email not in used_emails:
                used_emails.add(email)
                break
    phone = None
    if random.random() > 0.08:
        while True:
            phone = f"{AREA[market]}-555-{random.randint(0, 9999):04d}"
            if phone not in used_phones:
                used_phones.add(phone)
                break
    customers.append({
        "customer_id": cid, "first_name": fn, "last_name": ln, "email": email,
        "phone": phone, "zip": random.choice(ZIPS[market]), "market": market,
        "created_date": rand_date(START, date(2026, 9, 30)),
    })

# ---------------------------------------------------------------- vehicles
vehicles, used_vins = [], set()


def new_vin():
    while True:
        v = "".join(random.choice(VIN_CHARS) for _ in range(17))
        if v not in used_vins:
            used_vins.add(v)
            return v


for i in range(3000):
    rt = random.choice(ROOFTOPS)
    rid, brand, luxury = rt[0], rt[2], rt[4]
    is_new = random.random() < 0.55
    # most units spread over the whole period, plus a recent batch
    # so there is a realistic amount of current inventory
    first_day = max(START, rt[5]) if i < 2500 else date(2026, 7, 1)
    stock_date = rand_date(first_day, date(2026, 10, 31))
    if is_new:
        make = brand
        year = stock_date.year + (1 if stock_date.month >= 8 else 0)
        mileage = random.randint(3, 40)
        cost = random.uniform(45000, 88000) if luxury else random.uniform(26000, 62000)
    else:
        make = brand if random.random() < 0.45 else random.choice(list(MODELS))
        year = stock_date.year - random.randint(1, 8)
        age = stock_date.year - year
        mileage = max(800, int(random.gauss(12500 * age, 4000)))
        base = 40000 if make in LUXURY_MAKES else 30000
        cost = max(6500, base * (0.86 ** age) * random.uniform(0.85, 1.15))
    cost = round(cost, -1)
    list_price = round(cost * random.uniform(1.06, 1.13), -1)
    mean_days = 62 if is_new else 41
    days_to_sell = int(random.expovariate(1 / mean_days)) + 1
    sold_date = stock_date + timedelta(days=days_to_sell)
    vehicles.append({
        "vin": new_vin(), "rooftop_id": rid, "new_used": "New" if is_new else "Used",
        "model_year": year, "make": make, "model": random.choice(MODELS[make]),
        "mileage": mileage, "stock_date": stock_date, "cost": cost,
        "list_price": list_price,
        "sold_date": sold_date if sold_date < AS_OF else None,
    })
for v in vehicles:
    v["status"] = "sold" if v["sold_date"] else "in_stock"

# ---------------------------------------------------------------- deals
sold = sorted([v for v in vehicles if v["sold_date"]], key=lambda v: v["sold_date"])
deals = []
buyers = []                         # customer ids who have bought before
pool = customers[:]
random.shuffle(pool)
pool_i = 0
for did, v in enumerate(sold, start=1):
    if buyers and random.random() < 0.15:
        cid = random.choice(buyers)                  # repeat buyer
    else:
        cid = pool[pool_i]["customer_id"]
        pool_i += 1
        buyers.append(cid)
    c = customers[cid - 1]
    if c["created_date"] > v["sold_date"]:
        c["created_date"] = v["sold_date"] - timedelta(days=random.randint(0, 30))
    deal_type = random.choices(["Cash", "Finance", "Lease"],
                               [0.18, 0.62, 0.20] if v["new_used"] == "New" else [0.25, 0.75, 0.0])[0]
    sale_price = round(v["list_price"] * random.uniform(0.93, 1.01), 2)
    back = {"Cash": random.uniform(0, 400), "Finance": random.uniform(700, 2800),
            "Lease": random.uniform(400, 1600)}[deal_type]
    deals.append({
        "deal_id": did, "vin": v["vin"], "customer_id": cid,
        "rooftop_id": v["rooftop_id"],
        "salesperson": random.choice(salespeople[v["rooftop_id"]]),
        "sold_date": v["sold_date"], "deal_type": deal_type,
        "sale_price": sale_price, "front_gross": round(sale_price - v["cost"], 2),
        "back_gross": round(back, 2),
    })

# ---------------------------------------------------------------- service ROs
rooftop_market = {r[0]: r[3] for r in ROOFTOPS}
vehicle_by_vin = {v["vin"]: v for v in vehicles}
ros = []
ro_id = 100000
for d in deals:
    v = vehicle_by_vin[d["vin"]]
    loyal = random.random() < 0.62
    max_visits = 99 if loyal else random.randint(0, 2)
    visit = d["sold_date"] + timedelta(days=random.randint(60, 200))
    n = 0
    while visit < AS_OF and n < max_visits:
        rid = d["rooftop_id"]
        if random.random() < 0.12:
            same_mkt = [r[0] for r in ROOFTOPS if r[3] == rooftop_market[rid]]
            rid = random.choice(same_mkt)
        years_owned = (visit - d["sold_date"]).days / 365
        warranty = v["new_used"] == "New" and years_owned < 3 and random.random() < 0.35
        labor = round(random.uniform(60, 220) if random.random() < 0.7 else random.uniform(250, 1400), 2)
        parts = round(labor * random.uniform(0.3, 1.6), 2)
        ro_id += 1
        ros.append({
            "ro_id": ro_id, "vin": d["vin"], "customer_id": d["customer_id"],
            "rooftop_id": rid, "ro_date": visit,
            "pay_type": "Warranty" if warranty else "Customer",
            "labor_total": labor, "parts_total": parts,
        })
        n += 1
        visit += timedelta(days=random.randint(110, 230))
ros.sort(key=lambda r: r["ro_date"])
for i, r in enumerate(ros, start=100001):
    r["ro_id"] = i

# ---------------------------------------------------------------- planted duplicates
# Copy some existing customers as new records with small differences,
# then move some of their later deals/ROs to the duplicate record,
# the same way a duplicate gets created at a real store.
dupes = []
next_id = len(customers) + 1
candidates = [c for c in customers if c["customer_id"] in set(buyers)]
random.shuffle(candidates)
for c in candidates[:75]:
    kind = random.choice(["email_case", "phone_format", "nickname"])
    d = dict(c)
    d["customer_id"] = next_id
    d["created_date"] = rand_date(c["created_date"], date(2026, 10, 15))
    if kind == "email_case" and c["email"]:
        d["email"] = c["email"].upper()
        d["phone"] = None
    elif kind == "phone_format" and c["phone"]:
        p = c["phone"].replace("-", "")
        d["phone"] = f"({p[:3]}) {p[3:6]}-{p[6:]}" if random.random() < 0.5 else p
        d["email"] = None
    else:
        d["first_name"] = NICK.get(c["first_name"], c["first_name"][0] + ".")
        if not c["phone"]:
            d["email"] = c["email"]
    if d["email"] is None and d["phone"] is None:
        d["phone"] = c["phone"] or None
        d["email"] = c["email"] if d["phone"] is None else None
    dupes.append(d)
    # move this person's later activity onto the duplicate id
    for r in ros:
        if r["customer_id"] == c["customer_id"] and r["ro_date"] >= d["created_date"]:
            r["customer_id"] = next_id
    for dl in deals:
        if dl["customer_id"] == c["customer_id"] and dl["sold_date"] >= d["created_date"]:
            dl["customer_id"] = next_id
    next_id += 1
customers.extend(dupes)

# ---------------------------------------------------------------- write SQL
parts = [
    "-- =============================================================\n",
    "-- 02_seed_data.sql  (generated by scripts/generate_seed_data.py)\n",
    "-- Invented practice data. Run 01_create_schema.sql first.\n",
    f"-- Dataset 'today' is {AS_OF.isoformat()}. Use that date, not CURDATE().\n",
    "-- =============================================================\n\n",
    "USE dealer_practice;\n\n",
]
parts += inserts("rooftops",
                 ["rooftop_id", "name", "brand", "market", "is_luxury", "opened_date"],
                 [list(r) for r in ROOFTOPS])
parts += inserts("customers",
                 ["customer_id", "first_name", "last_name", "email", "phone", "zip", "created_date"],
                 [[c[k] for k in ["customer_id", "first_name", "last_name", "email",
                                  "phone", "zip", "created_date"]] for c in customers])
vcols = ["vin", "rooftop_id", "new_used", "model_year", "make", "model", "mileage",
         "stock_date", "cost", "list_price", "status"]
parts += inserts("vehicles", vcols, [[v[k] for k in vcols] for v in vehicles])
dcols = ["deal_id", "vin", "customer_id", "rooftop_id", "salesperson", "sold_date",
         "deal_type", "sale_price", "front_gross", "back_gross"]
parts += inserts("deals", dcols, [[d[k] for k in dcols] for d in deals])
rcols = ["ro_id", "vin", "customer_id", "rooftop_id", "ro_date", "pay_type",
         "labor_total", "parts_total"]
parts += inserts("service_ros", rcols, [[r[k] for k in rcols] for r in ros])

OUT.write_text("".join(parts), encoding="utf-8")
print(f"rooftops={len(ROOFTOPS)} customers={len(customers)} (dupes={len(dupes)}) "
      f"vehicles={len(vehicles)} deals={len(deals)} service_ros={len(ros)}")
print(f"wrote {OUT}")
