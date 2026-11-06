import unittest
from bundler_engine import analyze_baskets


class TestMarketBasketBundler(unittest.TestCase):
    def test_lift_separates_true_bundles_from_carry_bags(self):
        total, rules, traps = analyze_baskets()
        self.assertEqual(total, 1500)
        self.assertGreater(len(rules), 5)

        # Ensure high-lift pairs like Espresso Beans <-> Barista Oat Milk are discovered
        rule_pairs = {(r["antecedent_sku"], r["consequent_sku"]) for r in rules}
        self.assertIn(("ESP-BEAN", "OAT-MILK"), rule_pairs)
        self.assertIn(("PASTA-PEN", "SAUCE-ARR"), rule_pairs)

        # Ensure Reusable Carry Bag (TOTE-BAG) is filtered into traps due to low lift (~1.0)
        trap_consequents = {t["consequent_sku"] for t in traps}
        self.assertIn("TOTE-BAG", trap_consequents)


if __name__ == "__main__":
    unittest.main()

