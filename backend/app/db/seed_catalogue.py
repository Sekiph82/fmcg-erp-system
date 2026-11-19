"""POVU product range (owner's list and the POVU Catalogue, 2026-11-19) as product master data.

Idempotent: creates missing SKUs, refreshes name/category/description of existing ones, never touches prices or costs.
The catalogue has no prices, so selling_price/standard_cost stay empty until the owner's price list is loaded.
Run:  python -m app.db.seed_catalogue
"""
import asyncio

from sqlalchemy import select

from app.models.master import Product, ProductCategory, UnitOfMeasure

H, P = ProductCategory.HOUSEHOLD, ProductCategory.PERSONAL_CARE

# (SKU, product name, category, catalogue line, size); one row per pack size, sold per piece
RANGE = [
    # Laundry care
    ("POVU-HWP-20G", "POVU Hand Wash Powder 20 g Sachet", H, "Hand Wash Powder", "20 g sachet"),
    ("POVU-HWP-1KG", "POVU Hand Wash Powder 1 kg Pouch", H, "Hand Wash Powder", "1 kg pouch"),
    ("POVU-HWP-10KG", "POVU Hand Wash Powder 10 kg Bag", H, "Hand Wash Powder", "10 kg bag"),
    ("POVU-WCP-40G", "POVU WhiteCare Machine Powder Whites 40 g Sachet", H, "WhiteCare", "40 g sachet"),
    ("POVU-WCP-1KG", "POVU WhiteCare Machine Powder Whites 1 kg Pouch", H, "WhiteCare", "1 kg pouch"),
    ("POVU-WCP-10KG", "POVU WhiteCare Machine Powder Whites 10 kg Bag", H, "WhiteCare", "10 kg bag"),
    ("POVU-CGP-40G", "POVU ColorGuard Machine Powder Colors 40 g Sachet", H, "ColorGuard", "40 g sachet"),
    ("POVU-CGP-1KG", "POVU ColorGuard Machine Powder Colors 1 kg Pouch", H, "ColorGuard", "1 kg pouch"),
    ("POVU-CGP-10KG", "POVU ColorGuard Machine Powder Colors 10 kg Bag", H, "ColorGuard", "10 kg bag"),
    ("POVU-OXB-20G", "POVU OxyBright Oxygen Whitening Powder 20 g Sachet", H, "OxyBright", "20 g sachet"),
    ("POVU-OXB-1KG", "POVU OxyBright Oxygen Whitening Powder 1 kg Pouch", H, "OxyBright", "1 kg pouch"),
    ("POVU-OXB-10KG", "POVU OxyBright Oxygen Whitening Powder 10 kg Bag", H, "OxyBright", "10 kg bag"),
    ("POVU-SCS-25G", "POVU ScaleShield Anti-Limescale Powder 25 g Sachet", H, "ScaleShield", "25 g sachet"),
    ("POVU-SCS-1KG", "POVU ScaleShield Anti-Limescale Powder 1 kg Pouch", H, "ScaleShield", "1 kg pouch"),
    ("POVU-SCS-10KG", "POVU ScaleShield Anti-Limescale Powder 10 kg Bag", H, "ScaleShield", "10 kg bag"),
    ("POVU-CFL-1L", "POVU ColorFresh Liquid Detergent Colors 1 L Bottle", H, "ColorFresh", "1 L bottle"),
    ("POVU-CFL-40ML", "POVU ColorFresh Liquid Detergent Colors 40 ml Sachet", H, "ColorFresh", "40 ml sachet"),
    ("POVU-WFL-1L", "POVU WhiteFresh Liquid Detergent Whites 1 L Bottle", H, "WhiteFresh", "1 L bottle"),
    ("POVU-WFL-50ML", "POVU WhiteFresh Liquid Detergent Whites 50 ml Sachet", H, "WhiteFresh", "50 ml sachet"),
    ("POVU-SBL-1L", "POVU SoftBaby Liquid Detergent Baby 1 L Bottle", H, "SoftBaby", "1 L bottle"),
    ("POVU-SBL-40ML", "POVU SoftBaby Liquid Detergent Baby 40 ml Sachet", H, "SoftBaby", "40 ml sachet"),
    ("POVU-FLS-1L", "POVU FloraSoft Fabric Softener Floral 1 L Bottle", H, "FloraSoft", "1 L bottle"),
    ("POVU-PRS-1L", "POVU PureSoft Fabric Softener Sensitive 1 L Bottle", H, "PureSoft", "1 L bottle"),
    ("POVU-FSF-30ML", "POVU Fabric Softener 30 ml Sachet", H, "Fabric Softener", "30 ml sachet"),
    ("POVU-SFB-20L", "POVU SafeBleach Regular 20 L Drum", H, "SafeBleach", "20 L drum"),
    ("POVU-PWB-1L", "POVU PowerBleach Concentrated 1 L Bottle", H, "PowerBleach", "1 L bottle"),
    ("POVU-STL-50ML", "POVU StainLift Liquid Stain Remover 50 ml Sachet", H, "StainLift", "50 ml sachet"),
    ("POVU-STL-500ML", "POVU StainLift Liquid Stain Remover 500 ml Bottle", H, "StainLift", "500 ml bottle"),
    # Dish care
    ("POVU-LMB-1L", "POVU LemonBright Dishwashing Lemon 1 L Bottle", H, "LemonBright", "1 L bottle"),
    ("POVU-LMB-15ML", "POVU LemonBright Dishwashing Lemon 15 ml Sachet", H, "LemonBright", "15 ml sachet"),
    ("POVU-ORS-1L", "POVU OrangeSpark Dishwashing Orange 1 L Bottle", H, "OrangeSpark", "1 L bottle"),
    ("POVU-GFD-1L", "POVU GermFree Dish Antibacterial 1 L Bottle", H, "GermFree Dish", "1 L bottle"),
    # Surface care
    ("POVU-ALC-30ML", "POVU AllClean Multi-Purpose Cleaner 30 ml Sachet", H, "AllClean", "30 ml sachet"),
    ("POVU-ALC-1L", "POVU AllClean Multi-Purpose Cleaner 1 L Bottle", H, "AllClean", "1 L bottle"),
    ("POVU-BGS-1L", "POVU BlackGold Liquid Black Soap 1 L Bottle", H, "BlackGold Soap", "1 L bottle"),
    ("POVU-GRA-1L", "POVU GreaseAway Degreaser 1 L Bottle", H, "GreaseAway", "1 L bottle"),
    ("POVU-SCG-1L", "POVU ScaleGone Limescale Remover 1 L Bottle", H, "ScaleGone", "1 L bottle"),
    ("POVU-CRV-20ML", "POVU CrystalView Glass Cleaner 20 ml Sachet", H, "CrystalView", "20 ml sachet"),
    ("POVU-CRV-500ML", "POVU CrystalView Glass Cleaner 500 ml Bottle", H, "CrystalView", "500 ml bottle"),
    ("POVU-FLF-1L", "POVU FloorFresh Floor Cleaner 1 L Bottle", H, "FloorFresh", "1 L bottle"),
    ("POVU-FLF-30ML", "POVU FloorFresh Floor Cleaner 30 ml Sachet", H, "FloorFresh", "30 ml sachet"),
    ("POVU-BWG-750ML", "POVU BowlGuard Toilet Bowl Cleaner Gel 750 ml Bottle", H, "BowlGuard", "750 ml bottle"),
    ("POVU-BWG-50ML", "POVU BowlGuard Toilet Bowl Cleaner Gel 50 ml Sachet", H, "BowlGuard", "50 ml sachet"),
    ("POVU-CRS-500G", "POVU CreamShine Cream Cleaner 500 g Bottle", H, "CreamShine", "500 g bottle"),
    ("POVU-SHS-500ML", "POVU ShieldSpray Disinfectant Trigger Spray 500 ml Bottle", H, "ShieldSpray", "500 ml bottle"),
    ("POVU-BSP-50ML", "POVU BathSpark Tile & Bathroom Cleaner 50 ml Sachet", H, "BathSpark", "50 ml sachet"),
    ("POVU-BSP-500ML", "POVU BathSpark Tile & Bathroom Cleaner 500 ml Bottle", H, "BathSpark", "500 ml bottle"),
    # Specialty / auto care
    ("POVU-AQF-300ML", "POVU AquaFresh Mist Air Freshener 300 ml Trigger Spray", H, "AquaFresh Mist", "300 ml trigger spray"),
    ("POVU-AFM-30ML", "POVU AutoFoam Car Shampoo 30 ml Sachet", H, "AutoFoam", "30 ml sachet"),
    ("POVU-AFM-500ML", "POVU AutoFoam Car Shampoo 500 ml Bottle", H, "AutoFoam", "500 ml bottle"),
    ("POVU-CBC-500ML", "POVU CabinClean Interior Cleaner 500 ml Bottle", H, "CabinClean", "500 ml bottle"),
    # Personal care
    ("POVU-PLC-500ML", "POVU PalmCare Liquid Hand Soap 500 ml Bottle", P, "PalmCare", "500 ml bottle"),
    ("POVU-PLC-5ML", "POVU PalmCare Liquid Hand Soap 5 ml Sachet", P, "PalmCare", "5 ml sachet"),
    ("POVU-WTT-75G", "POVU WhiteTooth Whitening Toothpaste 75 g Tube", P, "WhiteTooth", "75 g tube"),
    ("POVU-WTT-6G", "POVU WhiteTooth Toothpaste 6 g Sachet", P, "WhiteTooth", "6 g sachet"),
    ("POVU-SHH-250ML", "POVU ShinyHair Shampoo 250 ml Bottle", P, "ShinyHair", "250 ml bottle"),
    ("POVU-SHH-8ML", "POVU ShinyHair Shampoo 8 ml Sachet", P, "ShinyHair", "8 ml sachet"),
    ("POVU-SBS-250ML", "POVU SoftBaby Shampoo 250 ml Bottle", P, "SoftBaby Shampoo", "250 ml bottle"),
    ("POVU-SBS-8ML", "POVU SoftBaby Shampoo 8 ml Sachet", P, "SoftBaby Shampoo", "8 ml sachet"),
    ("POVU-FSP-250ML", "POVU FreshSplash Shower Gel 250 ml Bottle", P, "FreshSplash", "250 ml bottle"),
    ("POVU-FSP-8ML", "POVU FreshSplash Shower Gel 8 ml Sachet", P, "FreshSplash", "8 ml sachet"),
    ("POVU-FSP-20L", "POVU FreshSplash Shower Gel Institutional 20 L Drum", P, "FreshSplash", "20 L drum"),
    ("POVU-SFH-500ML", "POVU SafeHands Hand Sanitizer 500 ml Bottle", P, "SafeHands", "500 ml bottle"),
    ("POVU-SLC-250ML", "POVU SilkyCare Hair Conditioner 250 ml Bottle", P, "SilkyCare", "250 ml bottle"),
    ("POVU-SLC-10ML", "POVU SilkyCare Hair Conditioner 10 ml Sachet", P, "SilkyCare", "10 ml sachet"),
    ("POVU-SLC-20L", "POVU SilkyCare Hair Conditioner Institutional 20 L Drum", P, "SilkyCare", "20 L drum"),
    ("POVU-GLC-10ML", "POVU GlowClean Facial Cleansing Gel 10 ml Sachet", P, "GlowClean", "10 ml sachet"),
    ("POVU-GLC-150ML", "POVU GlowClean Facial Cleansing Gel 150 ml Bottle", P, "GlowClean", "150 ml bottle"),
    ("POVU-SGL-10ML", "POVU SoftGlow Moisturizing Cream 10 ml Sachet", P, "SoftGlow", "10 ml sachet"),
    ("POVU-SGL-150ML", "POVU SoftGlow Moisturizing Cream 150 ml Bottle", P, "SoftGlow", "150 ml bottle"),
    ("POVU-SMS-100ML", "POVU SmoothShave Shaving Cream 100 ml Bottle", P, "SmoothShave", "100 ml bottle"),
    ("POVU-BDS-20ML", "POVU BodySoft Body Lotion 20 ml Sachet", P, "BodySoft", "20 ml sachet"),
    ("POVU-BDS-250ML", "POVU BodySoft Body Lotion 250 ml Bottle", P, "BodySoft", "250 ml bottle"),
    # Professional care
    ("POVU-PBP-20L", "POVU PowerBleach Pro Industrial Bleach 20 L Drum", H, "PowerBleach Pro", "20 L drum"),
    ("POVU-SCP-20L", "POVU SoftCare Pro Industrial Fabric Softener 20 L Drum", H, "SoftCare Pro", "20 L drum"),
    ("POVU-DSP-20L", "POVU DishPro Industrial Dishwashing 20 L Drum", H, "DishPro", "20 L drum"),
    ("POVU-SSP-20L", "POVU SafeShield Pro Industrial Disinfectant 20 L Drum", H, "SafeShield Pro", "20 L drum"),
    ("POVU-QAC-500ML", "POVU QacShield QAC-Based Surface Sanitizer 500 ml Bottle", H, "QacShield", "500 ml bottle"),
    ("POVU-QAC-20L", "POVU QacShield QAC-Based Surface Sanitizer 20 L Drum", H, "QacShield", "20 L drum"),
    ("POVU-GTR-250ML", "POVU GentleRub Alcohol-Free Hand Rub 250 ml Bottle", P, "GentleRub", "250 ml bottle"),
    ("POVU-GTR-10L", "POVU GentleRub Bulk Alcohol-Free Hand Rub 10 L Drum", P, "GentleRub", "10 L drum"),
    ("POVU-LDS-500ML", "POVU LaundryShield Sanitizer Additive 500 ml Bottle", H, "LaundryShield", "500 ml bottle"),
    ("POVU-LDS-10L", "POVU LaundryShield Sanitizer Additive 10 L Drum", H, "LaundryShield", "10 L drum"),
    # Wet wipes & baby care
    ("POVU-SFW-64", "POVU SafeWipe Antibacterial Surface Wipes 64 pcs", H, "SafeWipe", "64 wipes"),
    ("POVU-SFW-100", "POVU SafeWipe Antibacterial Surface Wipes 100 pcs", H, "SafeWipe", "100 wipes"),
    ("POVU-MDW-50", "POVU MediWipe CHX Medical Wipes 50 pcs", H, "MediWipe CHX", "50 wipes"),
    ("POVU-MDW-100", "POVU MediWipe CHX Medical Wipes 100 pcs", H, "MediWipe CHX", "100 wipes"),
    ("POVU-FFT-50", "POVU FreshFlush Flushable Toilet Wipes 50 pcs", P, "FreshFlush", "50 wipes"),
    ("POVU-FFT-80", "POVU FreshFlush Flushable Toilet Wipes 80 pcs", P, "FreshFlush", "80 wipes"),
    ("POVU-BBW-48", "POVU BabySoft Baby Wipes 48 pcs", P, "BabySoft", "48 wipes"),
    ("POVU-BBW-72", "POVU BabySoft Baby Wipes 72 pcs", P, "BabySoft", "72 wipes"),
]


async def seed_catalogue(db) -> int:
    """Upsert the POVU range; returns how many SKUs were created."""
    existing = {p.sku: p for p in (await db.execute(select(Product).where(Product.sku.in_([r[0] for r in RANGE])))).scalars()}
    created = 0
    for sku, name, category, line, size in RANGE:
        p = existing.get(sku)
        if p is None:
            p = Product(sku=sku, uom=UnitOfMeasure.PCS, units_per_carton=1, is_active=True)
            db.add(p)
            created += 1
        p.name, p.category, p.description = name, category, f"{line} · {size}"
    await db.flush()
    return created


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal

    async def _main():
        async with AsyncSessionLocal() as db:
            n = await seed_catalogue(db)
            await db.commit()
            print(f"POVU range: {len(RANGE)} SKUs ({n} new)")

    asyncio.run(_main())
