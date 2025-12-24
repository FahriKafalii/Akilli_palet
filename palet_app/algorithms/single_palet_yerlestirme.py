from .ga_utils import (
    parse_json_input,
    group_products_smart,
    simulate_single_pallet,
    generate_grid_placement,
    PaletConfig,
    UrunData
)
from ..models import Palet

def single_palet_yerlestirme_main(urunler, container_info, optimization=None):
    """
    Single Palet Sürecini Yöneten Ana Fonksiyon.
    Django modelleriyle çalışır.
    """
    print("--- Single Palet Operasyonu Başlıyor ---")
    
    # 1. Veriyi Hazırla
    palet_cfg = PaletConfig(
        length=container_info['length'],
        width=container_info['width'],
        height=container_info['height'],
        max_weight=container_info['weight']
    )
    
    # Django modellerini UrunData'ya çevir
    all_products = []
    for urun in urunler:
        urun_data = UrunData(
            urun_id=urun.id,
            code=urun.urun_kodu,
            boy=urun.boy,
            en=urun.en,
            yukseklik=urun.yukseklik,
            agirlik=urun.agirlik,
            quantity=1,
            is_package=False
        )
        urun_data.donus_serbest = urun.donus_serbest
        urun_data.mukavemet = urun.mukavemet
        all_products.append(urun_data)
    
    # 2. Grupla (Smart Grouping)
    groups = group_products_smart(all_products)
    
    single_pallets = [] # Oluşan paletler (Objeler veya Dict)
    mix_pool = []       # Mix'e kalacak ürünler
    
    total_palet_id = 1
    
    for key, group_items in groups.items():
        urun_kodu = key[0] # Key: (Code, L, W, H, Wgt)
        total_qty = len(group_items)
        
        print(f"Grup İnceleniyor: {urun_kodu}, Adet: {total_qty}")
        
        # 3. Simülasyon - REFACTORED: Efficiency-based evaluation
        sim_result = simulate_single_pallet(group_items, palet_cfg)
        
        if sim_result["can_be_single"]:
            # --- ✅ EFFICIENCY APPROVED: CREATE SINGLE PALLETS ---
            
            # REFACTORED: Use CAPACITY (not pack_count) for pallet count calculation
            capacity = sim_result["capacity"]  # Max items per pallet
            efficiency = sim_result["efficiency"]
            pack_count = sim_result["pack_count"]  # Actual items to place
            
            # Calculate how many pallets we can create
            # REFACTORED: Allow PARTIAL pallets if efficiency is good
            if total_qty >= capacity:
                # Enough stock for full pallets
                num_full_pallets = total_qty // capacity
                remainder = total_qty % capacity
                
                # Create partial pallet if remainder exists and efficiency allows
                create_partial = (remainder > 0 and remainder >= capacity * 0.3)  # At least 30% of capacity
                
                print(f"  -> ✅ ONAYLANDI. {sim_result['reason']}")
                print(f"  -> Efficiency: {efficiency*100:.1f}% | Capacity: {capacity} items/pallet")
                print(f"  -> Stock: {total_qty} → {num_full_pallets} full pallet(s)")
                
                if create_partial:
                    print(f"  -> + 1 partial pallet ({remainder} items, {remainder/capacity*100:.0f}% of capacity)")
                
            else:
                # Stock < capacity, but efficiency is good → CREATE PARTIAL PALLET
                num_full_pallets = 0
                remainder = total_qty
                create_partial = True
                
                print(f"  -> ✅ ONAYLANDI (Partial Pallet). {sim_result['reason']}")
                print(f"  -> Efficiency: {efficiency*100:.1f}% | Stock: {total_qty}/{capacity} items")
                print(f"  -> Creating 1 partial pallet ({total_qty/capacity*100:.0f}% of capacity)")
            
            # Create full pallets
            for palet_no in range(num_full_pallets):
                palet_items = group_items[palet_no * capacity:(palet_no + 1) * capacity]
                
                # ✅ MIXED-ORIENTATION GRID PLACEMENT
                placements = generate_grid_placement(palet_items, palet_cfg)
                
                # Prepare placement data
                urun_konumlari = {}
                urun_boyutlari = {}
                toplam_agirlik = 0.0
                kullanilan_hacim = 0.0
                
                for placement in placements:
                    item = placement['urun']
                    urun_id = str(item.id)
                    
                    urun_konumlari[urun_id] = [
                        placement['x'],
                        placement['y'],
                        placement['z']
                    ]
                    urun_boyutlari[urun_id] = [
                        placement['L'],
                        placement['W'],
                        placement['H']
                    ]
                    
                    toplam_agirlik += item.agirlik
                    kullanilan_hacim += (placement['L'] * placement['W'] * placement['H'])
                
                # Create Django Pallet object
                palet = Palet(
                    optimization=optimization,
                    palet_id=total_palet_id,
                    palet_turu='single',
                    custom_en=palet_cfg.width,
                    custom_boy=palet_cfg.length,
                    custom_max_yukseklik=palet_cfg.height,
                    custom_max_agirlik=palet_cfg.max_weight,
                    toplam_agirlik=toplam_agirlik,
                    kullanilan_hacim=kullanilan_hacim,
                    urun_konumlari=urun_konumlari,
                    urun_boyutlari=urun_boyutlari
                )
                palet.save()
                
                single_pallets.append(palet)
                total_palet_id += 1
            
            # Create partial pallet if allowed
            if create_partial and remainder > 0:
                palet_items = group_items[-remainder:]
                
                # ✅ MIXED-ORIENTATION GRID PLACEMENT
                placements = generate_grid_placement(palet_items, palet_cfg)
                
                urun_konumlari = {}
                urun_boyutlari = {}
                toplam_agirlik = 0.0
                kullanilan_hacim = 0.0
                
                for placement in placements:
                    item = placement['urun']
                    urun_id = str(item.id)
                    
                    urun_konumlari[urun_id] = [
                        placement['x'],
                        placement['y'],
                        placement['z']
                    ]
                    urun_boyutlari[urun_id] = [
                        placement['L'],
                        placement['W'],
                        placement['H']
                    ]
                    
                    toplam_agirlik += item.agirlik
                    kullanilan_hacim += (placement['L'] * placement['W'] * placement['H'])
                
                palet = Palet(
                    optimization=optimization,
                    palet_id=total_palet_id,
                    palet_turu='single',  # Still tagged as 'single' (same product type)
                    custom_en=palet_cfg.width,
                    custom_boy=palet_cfg.length,
                    custom_max_yukseklik=palet_cfg.height,
                    custom_max_agirlik=palet_cfg.max_weight,
                    toplam_agirlik=toplam_agirlik,
                    kullanilan_hacim=kullanilan_hacim,
                    urun_konumlari=urun_konumlari,
                    urun_boyutlari=urun_boyutlari
                )
                palet.save()
                
                single_pallets.append(palet)
                total_palet_id += 1
                
                # No items to mix pool (all used in partial pallet)
            elif remainder > 0:
                # Remainder too small for partial pallet → send to mix
                leftovers = group_items[-remainder:]
                mix_pool.extend(leftovers)
                print(f"  -> {remainder} items (<30% capacity) → Mix Pool")
                
        else:
            # --- ❌ EFFICIENCY TOO LOW: SEND TO MIX ---
            print(f"  -> ❌ REDDEDİLDİ. {sim_result['reason']}")
            print(f"  -> Tamamı ({total_qty} items) Mix havuzuna gidiyor.")
            mix_pool.extend(group_items)
            
    print(f"--- Single Bitti. Toplam {len(single_pallets)} palet üretildi. Mix Havuzu: {len(mix_pool)} ürün. ---")
    
    # Mix pool'daki UrunData'ları Django Urun modellerine geri çevir
    yerlesmemis_urunler = []
    for item in mix_pool:
        urun_obj = next((u for u in urunler if u.id == item.id), None)
        if urun_obj:
            yerlesmemis_urunler.append(urun_obj)
    
    return single_pallets, yerlesmemis_urunler