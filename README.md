# Retail Market Basket & Product Bundler Engine

An association-rule mining and retail pricing analytics tool that transforms raw Point-of-Sale (POS) transaction invoices into **margin-positive product bundle recommendations**.

## Key Analytical Highlight: Filtering Out "High-Confidence Traps"
A naive cross-sell query looks only at **Confidence** ($P(B \mid A)$). In retail, that mistakenly recommends bundling every product with *Reusable Carry Bags* or *Mineral Water* simply because 55% of all shoppers buy a carry bag at checkout.

This engine enforces a strict **Lift threshold ($\text{Lift} \ge 1.5$)** alongside Support and Confidence:
$$\text{Lift}(A \Rightarrow B) = \frac{P(A \cap B)}{P(A) \cdot P(B)}$$
* **Accepted Bundles ($\text{Lift} > 2.2\times$):** *Specialty Espresso Beans + Barista Oat Milk*, *Durum Wheat Penne + Arrabbiata Sauce*, *Whey Protein Isolate + Shaker Bottle*.
* **Rejected Margin Traps ($\text{Lift} \approx 1.0\times$):** High-confidence checkout staples where offering a 10% bundle discount erodes margin without driving incremental attachment.

## Quick Start
```bash
# Generate 1,500 POS invoices and print the bundle recommendation & trap filter report
python bundler_engine.py

# Run unit tests
python -m unittest test_bundler.py
```

