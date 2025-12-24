from .ga_utils import (
    parse_json_input,
    group_products_smart,
    simulate_single_pallet,
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
        
        # 3. Simülasyon (Sadece 1 Palet için)
        sim_result = simulate_single_pallet(group_items, palet_cfg)
        
        if sim_result["can_be_single"]:
            # --- BAŞARILI: REPLICATION STRATEJİSİ ---
            
            pack_count = sim_result["pack_count"] # Bir palete sığan adet
            
            # Kaç tane tam dolu palet çıkar?
            num_full_pallets = total_qty // pack_count
            
            # Artan ürün sayısı
            remainder = total_qty % pack_count
            
            print(f"  -> ONAYLANDI. Kriter: {sim_result['reason']}")
            print(f"  -> 1 Palet Kapasitesi: {pack_count} adet")
            print(f"  -> Hızlı Çoğaltma: {num_full_pallets} adet eş palet oluşturuluyor.")
            
            # Paletleri Django modeli olarak oluştur
            for palet_no in range(num_full_pallets):
                # İlk pack_count kadar ürünü al
                palet_items = group_items[palet_no * pack_count:(palet_no + 1) * pack_count]
                
                # Ürün konumları ve boyutlarını hazırla (basit yerleşim - grid)
                urun_konumlari = {}
                urun_boyutlari = {}
                toplam_agirlik = 0.0
                kullanilan_hacim = 0.0
                
                for idx, item in enumerate(palet_items):
                    urun_id = str(item.id)
                    # Basit grid yerleşimi (x, y, z konumları)
                    urun_konumlari[urun_id] = [0, 0, idx * item.yukseklik]
                    urun_boyutlari[urun_id] = [item.boy, item.en, item.yukseklik]
                    
                    # Toplam ağırlık ve hacim hesapla
                    toplam_agirlik += item.agirlik
                    # Yerleştirilen gerçek boyutları kullan (L x W x H)
                    L, W, H = urun_boyutlari[urun_id]
                    kullanilan_hacim += (L * W * H)
                
                # Palet oluştur
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
            
            # Artanları Mix'e at
            if remainder > 0:
                leftovers = group_items[-remainder:]
                mix_pool.extend(leftovers)
                print(f"  -> Kalan {remainder} ürün Mix havuzuna devredildi.")
                
        else:
            # --- BAŞARISIZ: HEPSİNİ MIX'E AT ---
            print(f"  -> REDDEDİLDİ. (Doluluk: %{sim_result['fill_ratio']*100:.1f}). Tamamı Mix'e gidiyor.")
            mix_pool.extend(group_items)
            
    print(f"--- Single Bitti. Toplam {len(single_pallets)} palet üretildi. Mix Havuzu: {len(mix_pool)} ürün. ---")
    
    # Mix pool'daki UrunData'ları Django Urun modellerine geri çevir
    yerlesmemis_urunler = []
    for item in mix_pool:
        urun_obj = next((u for u in urunler if u.id == item.id), None)
        if urun_obj:
            yerlesmemis_urunler.append(urun_obj)
    
    return single_pallets, yerlesmemis_urunler