"""
Single Palet Yerleştirme Algoritması
Gelişmiş GA utils entegrasyonu ile optimize edilmiştir.
"""
from .ga_utils import (
    PaletConfig,
    simulate_single_pallet,
    group_by_product_code
)


def single_palet_yerlestirme(urunler, container_info, optimization):
    """
    Aynı tür ürünleri single paletlere yerleştirir (Gelişmiş Versiyon).
    
    Args:
        urunler: Yerleştirilecek ürün listesi
        container_info: Container bilgileri (dict)
        optimization: Optimizasyon objesi
        
    Returns:
        tuple: (yerlestirilmis_paletler, yerlesmemis_urunler)
    """
    from ..models import Palet
    
    # Palet konfigürasyonu oluştur
    palet_cfg = PaletConfig(
        length=container_info.get('length', 120),
        width=container_info.get('width', 100),
        height=container_info.get('height', 180),
        max_weight=container_info.get('weight', 1250)
    )
    
    # Ürünleri kodlarına göre grupla
    gruplar = group_by_product_code(urunler)
    
    yerlestirilmis_paletler = []
    yerlesmemis_urunler = []
    palet_id = 1
    max_palet_sayisi = 50
    
    for urun_kodu, grup_urunleri in gruplar.items():
        print(f"\n{'='*60}")
        print(f"Single palet oluşturuluyor: {urun_kodu}")
        print(f"Toplam ürün: {len(grup_urunleri)}")
        
        # AYNI ÜRÜNDEN BİRDEN FAZLA PALET OLUŞTURABİLİR
        kalan_urunler = grup_urunleri.copy()
        
        while len(kalan_urunler) > 0 and len(yerlestirilmis_paletler) < max_palet_sayisi:
            # Gelişmiş single palet simülasyonu
            sonuc = simulate_single_pallet(kalan_urunler, palet_cfg)
            
            if sonuc["can_be_single"]:
                # Django Palet objesi oluştur
                palet = Palet(
                    optimization=optimization,
                    palet_id=palet_id,
                    palet_tipi=None,
                    palet_turu='single',
                    custom_en=palet_cfg.width,
                    custom_boy=palet_cfg.length,
                    custom_max_yukseklik=palet_cfg.height,
                    custom_max_agirlik=palet_cfg.max_weight
                )
                
                # Placements'tan konum ve boyut bilgilerini al
                urun_konumlari = {}
                urun_boyutlari = {}
                
                for placement in sonuc.get("placements", []):
                    urun = placement["urun"]
                    urun_id = str(urun.id)
                    
                    urun_konumlari[urun_id] = [
                        placement["x"],
                        placement["y"],
                        placement["z"]
                    ]
                    
                    urun_boyutlari[urun_id] = [
                        placement["L"],
                        placement["W"],
                        placement["H"]
                    ]
                
                palet.urun_konumlari = urun_konumlari
                palet.urun_boyutlari = urun_boyutlari
                palet.save()
                
                doluluk = sonuc["fill_ratio"] * 100
                print(f"✓ Single palet {palet_id}: {len(sonuc['used'])} ürün, %{doluluk:.2f} doluluk - KABUL")
                
                yerlestirilmis_paletler.append(palet)
                palet_id += 1
                
                # Kalan ürünleri güncelle
                kalan_urunler = sonuc["remaining"]
                
                if len(kalan_urunler) > 0:
                    print(f"  → Kalan {len(kalan_urunler)} ürün için yeni palet deneniyor...")
            else:
                # Artık single olamaz, MIX'e gönder
                print(f"✗ Single palet oluşturulamadı: {urun_kodu} ({len(kalan_urunler)} ürün) - MIX'e gönderiliyor")
                yerlesmemis_urunler.extend(kalan_urunler)
                break

    return yerlestirilmis_paletler, yerlesmemis_urunler
