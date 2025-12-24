from .ga_core import run_ga
from .ga_utils import PaletConfig, pack_maximal_rectangles

def mix_palet_yerlestirme_main(mix_pool, palet_cfg: PaletConfig, start_id=1):
    """
    Mix havuzundaki ürünleri Genetik Algoritma ile yerleştirir.
    """
    if not mix_pool:
        print("Mix havuzu boş, işlem yapılmayacak.")
        return []

    print(f"\n--- Mix Palet (GA) Başlıyor. Ürün Sayısı: {len(mix_pool)} ---")
    
    # 1. Genetik Algoritmayı Çalıştır
    # Parametreleri ihtiyaca göre ayarla: pop_size=50, gen=100
    best_solution, history = run_ga(
        urunler=mix_pool,
        palet_cfg=palet_cfg,
        population_size=40,
        generations=50,
        elitism=4,
        mutation_rate=0.2 # Çeşitlilik için biraz yüksek tuttum
    )
    
    # 2. En İyi Çözümü Decode Et (Paletlere Çevir)
    # ✅ MAXIMAL RECTANGLES kullanarak optimize yerleşim
    from .ga_utils import pack_maximal_rectangles
    final_pallets_data = pack_maximal_rectangles(best_solution.urunler, best_solution.rot_gen, palet_cfg)
    
    # 3. Sonuçları Formatla
    mix_pallets = []
    current_id = start_id
    
    for p_data in final_pallets_data:
        mix_pallets.append({
            "id": current_id,
            "type": "MIX",
            "quantity": len(p_data["items"]),
            "items": p_data["items"], # İçinde koordinat (x,y,z) bilgisi var
            "fill_ratio": p_data.get("fill_ratio", 0),
            "weight": p_data.get("weight", 0)
        })
        current_id += 1
        
    print(f"--- Mix Bitti. GA Tarafından {len(mix_pallets)} adet palet oluşturuldu. ---")
    print(f"En İyi Fitness: {best_solution.fitness:.2f}, Ort. Doluluk: %{best_solution.ortalama_doluluk*100:.1f}")
    
    return mix_pallets