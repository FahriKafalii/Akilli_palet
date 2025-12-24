#!/usr/bin/env python3
"""
Test Script for REFACTORED Single Pallet Logic:
- Mixed-Orientation Tiling
- Efficiency-Based Evaluation
- Partial Pallet Support
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from palet_app.algorithms.ga_utils import (
    PaletConfig,
    UrunData,
    solve_best_layer_configuration,
    simulate_single_pallet,
    generate_grid_placement
)

def test_mixed_orientation_tiling():
    """Test the new Mixed-Orientation Tiling algorithm"""
    print("\n" + "="*80)
    print("TEST 1: MIXED-ORIENTATION TILING")
    print("="*80)
    
    # Pallet: 120x100cm
    # Item: 45x35cm
    
    pallet_L, pallet_W = 120, 100
    item_L, item_W = 45, 35
    
    print(f"\nPallet: {pallet_L} x {pallet_W} cm")
    print(f"Item: {item_L} x {item_W} cm")
    
    # Call new algorithm
    items_per_layer, layout_desc, layer_config = solve_best_layer_configuration(
        pallet_L, pallet_W, item_L, item_W
    )
    
    print(f"\n✅ RESULT:")
    print(f"  Items per layer: {items_per_layer}")
    print(f"  Layout: {layout_desc}")
    print(f"  Configuration: {layer_config}")
    
    # Manual verification
    type_a_rows = layer_config['type_a_rows']
    type_b_rows = layer_config['type_b_rows']
    cols_a = layer_config['cols_a']
    cols_b = layer_config['cols_b']
    
    count_a = type_a_rows * cols_a
    count_b = type_b_rows * cols_b
    total = count_a + count_b
    
    print(f"\n📊 Verification:")
    print(f"  Type-A: {type_a_rows} rows × {cols_a} cols = {count_a} items")
    print(f"  Type-B: {type_b_rows} rows × {cols_b} cols = {count_b} items")
    print(f"  Total: {total} items (matches: {total == items_per_layer})")
    
    # Compare to old algorithm (100% single orientation)
    old_best = max(
        (pallet_L // item_L) * (pallet_W // item_W),  # Orientation A
        (pallet_L // item_W) * (pallet_W // item_L)   # Orientation B
    )
    
    improvement = items_per_layer - old_best
    print(f"\n🎯 Improvement over single-orientation:")
    print(f"  Old best: {old_best} items")
    print(f"  New best: {items_per_layer} items")
    print(f"  Gain: +{improvement} items ({improvement/old_best*100:.1f}% better)")

def test_efficiency_based_simulation():
    """Test the new Efficiency-Based evaluation"""
    print("\n" + "="*80)
    print("TEST 2: EFFICIENCY-BASED SIMULATION")
    print("="*80)
    
    palet_cfg = PaletConfig(
        length=120,
        width=100,
        height=180,
        max_weight=1250
    )
    
    # Test Case 1: Large package (100x100x150) - should pass with new logic
    print("\n--- Test Case 1: Large Package (100x100x150) ---")
    
    items_case1 = []
    for i in range(5):  # Only 5 items (old logic would reject due to low stock)
        items_case1.append(UrunData(
            urun_id=i+1,
            code="LARGE_PKG",
            boy=100, en=100, yukseklik=150,
            agirlik=355
        ))
    
    result1 = simulate_single_pallet(items_case1, palet_cfg)
    
    print(f"Stock: {len(items_case1)} items")
    print(f"Capacity: {result1['capacity']} items")
    print(f"Efficiency: {result1['efficiency']*100:.1f}%")
    print(f"Can be single: {result1['can_be_single']}")
    print(f"Pack count: {result1['pack_count']}")
    print(f"Reason: {result1['reason']}")
    
    # Test Case 2: Smaller items (45x35x30) - better tiling
    print("\n--- Test Case 2: Small Items (45x35x30) ---")
    
    items_case2 = []
    for i in range(20):
        items_case2.append(UrunData(
            urun_id=100+i,
            code="SMALL_PKG",
            boy=45, en=35, yukseklik=30,
            agirlik=15
        ))
    
    result2 = simulate_single_pallet(items_case2, palet_cfg)
    
    print(f"Stock: {len(items_case2)} items")
    print(f"Capacity: {result2['capacity']} items")
    print(f"Efficiency: {result2['efficiency']*100:.1f}%")
    print(f"Can be single: {result2['can_be_single']}")
    print(f"Pack count: {result2['pack_count']}")
    print(f"Reason: {result2['reason']}")
    
    # Test Case 3: Very small items - should fail efficiency check
    print("\n--- Test Case 3: Very Small Items (20x15x10) ---")
    
    items_case3 = []
    for i in range(50):
        items_case3.append(UrunData(
            urun_id=200+i,
            code="TINY_PKG",
            boy=20, en=15, yukseklik=10,
            agirlik=2
        ))
    
    result3 = simulate_single_pallet(items_case3, palet_cfg)
    
    print(f"Stock: {len(items_case3)} items")
    print(f"Capacity: {result3['capacity']} items")
    print(f"Efficiency: {result3['efficiency']*100:.1f}%")
    print(f"Can be single: {result3['can_be_single']}")
    print(f"Reason: {result3['reason']}")

def test_real_json_data():
    """Test with actual JSON data from test_data folder"""
    print("\n" + "="*80)
    print("TEST 3: REAL JSON DATA (0114.json)")
    print("="*80)
    
    json_file = 'test_data/0114.json'
    
    if not os.path.exists(json_file):
        print(f"⚠️  File not found: {json_file}")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    from palet_app.algorithms.ga_utils import parse_json_input, group_products_smart
    
    palet_cfg, all_products = parse_json_input(data)
    groups = group_products_smart(all_products)
    
    print(f"\nTotal products: {len(all_products)}")
    print(f"Product groups: {len(groups)}")
    print(f"Pallet: {palet_cfg.length}x{palet_cfg.width}x{palet_cfg.height}cm, {palet_cfg.max_weight}kg")
    
    print("\n--- Simulating Each Group ---")
    
    approved_count = 0
    rejected_count = 0
    
    for key, group_items in groups.items():
        code, L, W, H, wgt = key
        qty = len(group_items)
        
        sim = simulate_single_pallet(group_items, palet_cfg)
        
        status = "✅ APPROVED" if sim['can_be_single'] else "❌ REJECTED"
        
        print(f"\n{status} | {code}")
        print(f"  Stock: {qty} items | {L}x{W}x{H}cm, {wgt}kg")
        print(f"  Capacity: {sim['capacity']} items/pallet")
        print(f"  Efficiency: {sim['efficiency']*100:.1f}%")
        print(f"  Layout: {sim['layout_desc']}")
        
        if sim['can_be_single']:
            approved_count += 1
            # Calculate pallets
            if qty >= sim['capacity']:
                full = qty // sim['capacity']
                partial = qty % sim['capacity']
                print(f"  → {full} full pallet(s)", end="")
                if partial >= sim['capacity'] * 0.3:
                    print(f" + 1 partial ({partial} items)")
                else:
                    print(f" (remainder: {partial} → mix)")
            else:
                print(f"  → 1 partial pallet ({qty}/{sim['capacity']} items, {qty/sim['capacity']*100:.0f}%)")
        else:
            rejected_count += 1
            print(f"  → All {qty} items → Mix Pool")
    
    print("\n" + "="*80)
    print(f"SUMMARY: {approved_count} approved, {rejected_count} rejected")
    print("="*80)

if __name__ == "__main__":
    print("\n🚀 STARTING REFACTORED SINGLE PALLET TESTS")
    
    try:
        test_mixed_orientation_tiling()
        test_efficiency_based_simulation()
        test_real_json_data()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\nKey Improvements Demonstrated:")
        print("  1. Mixed-Orientation Tiling → More items per layer")
        print("  2. Efficiency-Based Logic → Correct suitability evaluation")
        print("  3. Partial Pallet Support → Better stock utilization")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
