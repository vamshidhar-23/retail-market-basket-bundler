import csv
import random
from itertools import combinations
from pathlib import Path

DATA_FILE = Path(__file__).parent / "retail_transactions.csv"

PRODUCTS = {
    "ESP-BEAN": ("Specialty Espresso Beans 500g", 650.0, "Coffee"),
    "OAT-MILK": ("Barista Oat Milk 1L", 290.0, "Dairy & Alt"),
    "PAPER-FLT": ("V60 Pour-Over Paper Filters", 320.0, "Accessories"),
    "SYRUP-VAN": ("Artisan Vanilla Coffee Syrup", 450.0, "Syrups"),
    "PASTA-PEN": ("Durum Wheat Penne Pasta 500g", 180.0, "Pantry"),
    "SAUCE-ARR": ("Spicy Arrabbiata Pasta Sauce", 260.0, "Pantry"),
    "PARM-CHS": ("Aged Parmesan Cheese Block", 490.0, "Dairy & Alt"),
    "OLIVE-OIL": ("Extra Virgin Olive Oil 500ml", 720.0, "Pantry"),
    "WHEY-PRO": ("Whey Protein Isolate 1kg", 2400.0, "Fitness"),
    "SHAKER-BT": ("Leakproof Gym Shaker Bottle", 350.0, "Fitness"),
    "PEANUT-BT": ("Unsweetened Crunchy Peanut Butter", 380.0, "Fitness"),
    "BANANA-6P": ("Organic Robusta Bananas (6 pcs)", 65.0, "Produce"),
    "TOTE-BAG": ("Reusable Cotton Carry Bag", 25.0, "General"),
    "WATER-1L": ("Mineral Water Bottle 1L", 20.0, "General"),
}


def generate_synthetic_pos_data(filepath=DATA_FILE, num_invoices=1500):
    """
    Generates 1,500 realistic retail store invoices containing natural co-purchase
    clusters (Coffee lovers, Pasta night, Gym stack) plus high-frequency 'noise' items
    (Carry Bag, Water Bottle) to demonstrate why Lift > Confidence is critical.
    """
    random.seed(108)
    rows = []

    for inv_id in range(10001, 10001 + num_invoices):
        invoice_no = f"INV-{inv_id}"
        basket = set()

        r = random.random()
        # Cluster 1: Specialty Coffee Buyers (~28% of baskets)
        if r < 0.28:
            basket.add("ESP-BEAN")
            if random.random() < 0.68:
                basket.add("OAT-MILK")
            if random.random() < 0.45:
                basket.add("PAPER-FLT")
            if random.random() < 0.35:
                basket.add("SYRUP-VAN")

        # Cluster 2: Italian Dinner Night (~26% of baskets)
        elif r < 0.54:
            basket.add("PASTA-PEN")
            if random.random() < 0.74:
                basket.add("SAUCE-ARR")
            if random.random() < 0.52:
                basket.add("PARM-CHS")
            if random.random() < 0.30:
                basket.add("OLIVE-OIL")

        # Cluster 3: Fitness / Gym Stack (~20% of baskets)
        elif r < 0.74:
            basket.add("WHEY-PRO")
            if random.random() < 0.62:
                basket.add("SHAKER-BT")
            if random.random() < 0.48:
                basket.add("PEANUT-BT")
            if random.random() < 0.55:
                basket.add("BANANA-6P")

        # Random impulse items
        all_skus = list(PRODUCTS.keys())
        for _ in range(random.randint(1, 2)):
            basket.add(random.choice(all_skus))

        # High-frequency checkout items (Carry Bag appears in ~55% of all baskets regardless of cluster!)
        if random.random() < 0.55:
            basket.add("TOTE-BAG")

        for sku in sorted(basket):
            name, price, cat = PRODUCTS[sku]
            qty = 1 if sku != "BANANA-6P" else random.choice([1, 2])
            rows.append({
                "invoice_no": invoice_no,
                "sku": sku,
                "product_name": name,
                "category": cat,
                "unit_price": price,
                "quantity": qty,
            })

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["invoice_no", "sku", "product_name", "category", "unit_price", "quantity"]
        )
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def analyze_baskets(filepath=DATA_FILE, min_support=0.04, min_confidence=0.30, min_lift=1.5):
    """
    Computes Association Rules (Support, Confidence, Lift) and Expected Bundle Margin Impact.
    Works out-of-the-box using clean Python structures (no C-compiler dependencies required).
    """
    if not Path(filepath).exists():
        generate_synthetic_pos_data(filepath)

    invoices = {}
    sku_info = {}

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            inv = row["invoice_no"]
            sku = row["sku"]
            invoices.setdefault(inv, set()).add(sku)
            sku_info[sku] = {
                "name": row["product_name"],
                "price": float(row["unit_price"]),
                "category": row["category"],
            }

    total_baskets = len(invoices)
    item_counts = {}
    pair_counts = {}

    for items in invoices.values():
        for item in items:
            item_counts[item] = item_counts.get(item, 0) + 1
        for a, b in combinations(sorted(items), 2):
            pair_counts[(a, b)] = pair_counts.get((a, b), 0) + 1

    rules = []
    traps_filtered = []

    for (sku_a, sku_b), co_count in pair_counts.items():
        support_ab = co_count / total_baskets
        if support_ab < min_support:
            continue

        # Check both directions: A -> B and B -> A
        for ant, con in [(sku_a, sku_b), (sku_b, sku_a)]:
            sup_a = item_counts[ant] / total_baskets
            sup_b = item_counts[con] / total_baskets
            confidence = support_ab / sup_a
            lift = confidence / sup_b

            if confidence < min_confidence:
                continue

            combined_price = sku_info[ant]["price"] + sku_info[con]["price"]
            bundle_price_10pct = round(combined_price * 0.90, 2)

            # Estimate incremental monthly revenue per 1,000 shoppers of Item A
            # assuming 18% of non-attach shoppers convert when offered a 10% bundle discount
            non_attach_rate = 1.0 - confidence
            est_new_conversions_per_1k = round(1000 * sup_a * non_attach_rate * 0.18, 1)
            incremental_rev_per_1k = round(est_new_conversions_per_1k * (sku_info[con]["price"] * 0.80), 2)

            record = {
                "antecedent_sku": ant,
                "antecedent_name": sku_info[ant]["name"],
                "consequent_sku": con,
                "consequent_name": sku_info[con]["name"],
                "support": round(support_ab, 4),
                "confidence": round(confidence, 4),
                "lift": round(lift, 2),
                "combined_mrp": combined_price,
                "recommended_bundle_price": bundle_price_10pct,
                "incremental_rev_per_1k_txns": incremental_rev_per_1k,
            }

            if lift >= min_lift:
                rules.append(record)
            else:
                traps_filtered.append(record)

    rules.sort(key=lambda r: (r["lift"], r["confidence"]), reverse=True)
    traps_filtered.sort(key=lambda r: r["confidence"], reverse=True)
    return total_baskets, rules, traps_filtered


def print_market_basket_report():
    total_baskets, rules, traps = analyze_baskets()
    print("\n" + "=" * 98)
    print(f"  RETAIL MARKET BASKET & PRODUCT BUNDLER ENGINE (Analyzed {total_baskets:,} POS Invoices)")
    print("=" * 98)
    print(
        f"  {'ANCHOR ITEM (IF BOUGHT)':<30} -> {'RECOMMENDED BUNDLE ITEM':<28} | "
        f"{'CONF':>6} | {'LIFT':>5} | {'BUNDLE RS':>9}"
    )
    print("-" * 98)

    seen_pairs = set()
    for r in rules:
        pair_key = tuple(sorted([r["antecedent_sku"], r["consequent_sku"]]))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        ant = r["antecedent_name"][:29]
        con = r["consequent_name"][:27]
        conf_str = f"{r['confidence']*100:.1f}%"
        lift_str = f"{r['lift']:.2f}x"
        bundle_rs = f"Rs.{r['recommended_bundle_price']:,.0f}"
        print(f"  {ant:<30} -> {con:<28} | {conf_str:>6} | {lift_str:>5} | {bundle_rs:>9}")

    print("=" * 98)
    print("\n  [!] HIGH-CONFIDENCE TRAPS FILTERED OUT (High Confidence, but Lift ~ 1.0x):")
    print("      (Items everyone buys anyway -- discounting these wastes store margin!)")
    print("-" * 98)
    for t in traps[:4]:
        print(
            f"  * {t['antecedent_name'][:28]:<28} -> {t['consequent_name'][:28]:<28} | "
            f"Confidence: {t['confidence']*100:.1f}% | Lift: {t['lift']:.2f}x (REJECTED)"
        )
    print("-" * 98 + "\n")


if __name__ == "__main__":
    print_market_basket_report()
