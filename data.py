"""Static content for the Verda Farm storefront.

The catalogue itself now lives in Mongo (`product_service.py`) so the admin can
edit it without a deploy. `SEED_PRODUCTS` below is only the starting stock that
`flask seed-products` loads into an empty database — nothing reads it at request
time, and editing it will not change a catalogue that has already been seeded.

Pricing knobs (delivery fee, quantity caps) live in config.py, not here.
"""

SEED_PRODUCTS = [
    {
        "id": "plantain",
        "name": "Plantain",
        "cat": "Fresh Produce",
        "aud": ["retail", "wholesale"],
        "price": 4500,
        "unit": "per bunch",
        "tone": "#E9DFA0",
        "ink": "#524711",
        "tag": "Staple",
        "blurb": "Firm, sun-ripened plantain harvested at peak starch.",
    },
    {
        "id": "bell",
        "name": "Bell Pepper",
        "cat": "Fresh Produce",
        "aud": ["retail", "wholesale"],
        "price": 3200,
        "unit": "per kg",
        "tone": "#7BB661",
        "ink": "#1f3a12",
        "tag": "Fresh",
        "blurb": "Crisp tricolour bells, graded and cold-chained.",
    },
    {
        "id": "herbanero",
        "name": "Herbanero Pepper",
        "cat": "Fresh Produce",
        "aud": ["retail", "wholesale", "export"],
        "price": 5800,
        "unit": "per kg",
        "tone": "#E4713F",
        "ink": "#4a1c0c",
        "tag": "Signature",
        "blurb": "Our signature aromatic heat — small batch, high demand.",
    },
    {
        "id": "tomato",
        "name": "Roma Tomatoes",
        "cat": "Fresh Produce",
        "aud": ["retail", "wholesale"],
        "price": 2800,
        "unit": "per basket",
        "tone": "#D8583F",
        "ink": "#3f120a",
        "tag": "Fresh",
        "blurb": "Thick-walled Roma, ideal for stews and paste.",
    },
    {
        "id": "corn",
        "name": "Sweet Corn",
        "cat": "Grains & Staples",
        "aud": ["retail", "wholesale"],
        "price": 1900,
        "unit": "per kg",
        "tone": "#E7CE76",
        "ink": "#5f4d10",
        "tag": "Staple",
        "blurb": "Golden kernels, milled or sold on the cob.",
    },
    {
        "id": "cassava",
        "name": "Cassava",
        "cat": "Grains & Staples",
        "aud": ["retail", "wholesale", "export"],
        "price": 1200,
        "unit": "per kg",
        "tone": "#CBB98F",
        "ink": "#463819",
        "tag": "Staple",
        "blurb": "Fresh tubers and processed flour available.",
    },
    {
        "id": "cocoa",
        "name": "Cocoa Beans",
        "cat": "Cash Crops",
        "aud": ["wholesale", "export"],
        "price": 9800,
        "unit": "per kg",
        "tone": "#8a5a3b",
        "ink": "#f2e6dc",
        "tag": "Export",
        "blurb": "Fermented, sun-dried, export-grade beans.",
    },
    {
        "id": "sesame",
        "name": "Sesame Seeds",
        "cat": "Cash Crops",
        "aud": ["wholesale", "export"],
        "price": 6400,
        "unit": "per kg",
        "tone": "#E4D8BE",
        "ink": "#54481f",
        "tag": "Export",
        "blurb": "Cleaned white sesame, 99% purity.",
    },
    {
        "id": "cashew",
        "name": "Raw Cashew Nuts",
        "cat": "Cash Crops",
        "aud": ["wholesale", "export"],
        "price": 7200,
        "unit": "per kg",
        "tone": "#D8BE8E",
        "ink": "#4d3a14",
        "tag": "Export",
        "blurb": "Bold-count RCN, moisture-controlled.",
    },
    {
        "id": "plantain-flour",
        "name": "Plantain Flour",
        "cat": "Processed",
        "aud": ["retail", "wholesale"],
        "price": 5200,
        "unit": "per 1kg pack",
        "tone": "#D9C08A",
        "ink": "#4a3a10",
        "tag": "Processed",
        "blurb": "Stone-milled unripe plantain, packed to order.",
    },
    {
        "id": "dried-herbanero",
        "name": "Dried Herbanero",
        "cat": "Processed",
        "aud": ["retail", "wholesale", "export"],
        "price": 8900,
        "unit": "per 500g",
        "tone": "#C9552B",
        "ink": "#3f150a",
        "tag": "Processed",
        "blurb": "Slow-dried and flaked — shelf-stable heat.",
    },
    {
        "id": "garri",
        "name": "Cassava Garri",
        "cat": "Processed",
        "aud": ["retail", "wholesale"],
        "price": 3600,
        "unit": "per 2kg pack",
        "tone": "#EAD9B0",
        "ink": "#544216",
        "tag": "Processed",
        "blurb": "Fine, well-fermented white garri.",
    },
]

CATEGORIES = ["All", "Fresh Produce", "Grains & Staples", "Cash Crops", "Processed"]

AUDIENCES = [
    ("All", "All buyers"),
    ("retail", "Retail"),
    ("wholesale", "Wholesale"),
    ("export", "Export"),
]

CATEGORY_CARDS = [
    {
        "label": "Fresh Produce",
        "desc": "Plantain, peppers, tomatoes",
        "tone": "#2E7D4E",
    },
    {
        "label": "Grains & Staples",
        "desc": "Corn, cassava & more",
        "tone": "#B8862F",
    },
    {
        "label": "Cash Crops",
        "desc": "Cocoa, sesame, cashew",
        "tone": "#7A4A2B",
    },
    {
        "label": "Processed",
        "desc": "Flour, garri, dried goods",
        "tone": "#4C7A52",
    },
]

VOLUME_TIERS = [
    ("50–200 kg", "5%", "2 days"),
    ("200–500 kg", "12%", "3 days"),
    ("500 kg – 2 tonnes", "20%", "4–5 days"),
    ("2 tonnes +", "Custom", "Scheduled"),
]

EXPORT_STEPS = [
    ("1", "Inquire", "Send product, grade and volume needs."),
    ("2", "Sample & quote", "We ship samples and confirm FOB/CIF pricing."),
    ("3", "Documentation", "Phytosanitary, quality & export papers handled."),
    ("4", "Ship", "Container loading and tracked delivery."),
]

# Catalogue lookups (find / filter / related) moved to product_service.py when
# the catalogue moved into Mongo.
