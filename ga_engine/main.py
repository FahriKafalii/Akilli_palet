"""
ga_engine.main

Bu dosya, GA motorunu şirketten gelen JSON dosyasıyla test etmek için kullanılır.

ŞU ANKİ DURUM (AŞAMA 5–6 arası):
    - JSON → ürün listesi (package_quantity kadar kutu oluşturuyoruz)
    - Single-first pipeline:
        * Her ürün tipi için single palet simülasyonu (>= %80 doluluk)
        * Single paletlere gidenler ayrılıyor
        * Geri kalan tüm ürünler MIX havuzuna gidiyor
    - MIX havuzu için GA çalışıyor (sadece hacim + ağırlık kısıtları)
    - Sonuçlar:
        * Single palet özeti
        * MIX GA sonucu ve palet detayları
        * Toplam palet sayısı & genel doluluk

Kullanım:
    python -m ga_engine.main
"""

import json
from dataclasses import dataclass
from pathlib import Path

from .ga_core import run_ga
from .utils import (
    PaletConfig,
    urun_hacmi,
    urun_agirlik,
    convert_json_packages_to_products,
    basit_palet_paketleme,
    group_by_product_code,
    simulate_single_pallet,
)


# GA içinde kullanılacak geçici ürün class'ı
@dataclass
class DummyUrun:
    urun_kodu: str
    boy: float
    en: float
    yukseklik: float
    agirlik: float
    mukavemet: float = 1000.0
    donus_serbest: bool = True
    istiflenebilir: bool = True
def calculate_dynamic_params(product_count: int):
    """
    Ürün sayısına göre GA parametrelerini otomatik hesaplar.
    Taban: 30 popülasyon, 50 nesil.
    Artış: Her 150 üründe +1 popülasyon, her 40 üründe +1 nesil.
    """
    pop_size = 30 + (product_count // 150)
    if pop_size > 100: pop_size = 100  # Tavan limit

    generations = 50 + (product_count // 40)
    if generations > 300: generations = 300  # Tavan limit

    print(f"🧮 Dinamik Parametreler: {product_count} ürün -> Pop: {pop_size}, Gen: {generations}")
    return pop_size, generations

def main():
    # -----------------------------
    # 1) JSON DOSYASINI YÜKLE
    # -----------------------------
    json_path = Path(__file__).resolve().parent.parent / "test_data" / "0552.json"

    print(f"JSON yükleniyor: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # -------------------------------------------
    # 2) JSON → ÜRÜN LİSTESİNE DÖNÜŞTÜR
    # -------------------------------------------
    tum_urunler = convert_json_packages_to_products(data, DummyUrun)

    print(f"Toplam ürün adedi (hesaplanan): {len(tum_urunler)}")

    toplam_hacim = sum(urun_hacmi(u) for u in tum_urunler)
    print(f"Toplam ürün hacmi: {toplam_hacim:.2f} cm³")

    # -------------------------------------------
    # 3) PALET PARAMETRELERİNİ JSON'DAN AL (DİNAMİK)
    # -------------------------------------------
    container_info = data.get("container", {})
    
    # Eğer JSON'da container bilgisi yoksa varsayılan (120x100x180) kullanılır
    p_len = float(container_info.get("length", 120))
    p_wid = float(container_info.get("width", 100))
    p_hgt = float(container_info.get("height", 180))
    p_wgt = float(container_info.get("weight", 1250))

    palet_cfg = PaletConfig(length=p_len, width=p_wid, height=p_hgt, max_weight=p_wgt)

    print(f"Palet Bilgisi: {p_len}x{p_wid}x{p_hgt} cm, Max Ağırlık: {p_wgt} kg")
    print(f"Palet hacmi: {palet_cfg.volume:.2f} cm³")

    # -------------------------------------------
    # 4) SINGLE-FIRST PIPELINE
    # -------------------------------------------
    print("\nSingle-first pipeline çalışıyor...")

    gruplar = group_by_product_code(tum_urunler)

    single_pallets = []  # Single palet listesi
    mix_pool = []  # GA'ya gidecek ürünler

    for kod, urun_listesi in gruplar.items():
        kalan = list(urun_listesi)

        while kalan:
            sim = simulate_single_pallet(kalan, palet_cfg)
            used = sim["used"]
            remaining = sim["remaining"]
            fill = sim["fill_ratio"]

            if not used:
                # Hiç sığmıyorsa -> hepsi mix'e
                mix_pool.extend(kalan)
                break

            if sim["can_be_single"]:
                # Bu ürün tipinden bir single palet oluştur
                v = len(used) * urun_hacmi(used[0])
                w = sum(urun_agirlik(u) for u in used)

                single_pallets.append(
                    {
                        "urunler": used,
                        "volume": v,
                        "weight": w,
                        "fill_ratio": fill,
                        "urun_kodu": kod,
                        "single": True,
                        "placements": sim["placements"],
                    }
                )
                kalan = remaining
            else:
                # Single için doluluk yeterli değil → kalanların hepsi mix'e
                mix_pool.extend(kalan)
                break

    single_palet_sayisi = len(single_pallets)
    single_urun_sayisi = sum(len(p["urunler"]) for p in single_pallets)
    mix_urun_sayisi = len(mix_pool)

    print(f"\nSingle palet sayısı: {single_palet_sayisi}")
    print(f"Single paletlerdeki ürün adedi: {single_urun_sayisi}")
    print(f"MIX havuzuna giden ürün adedi: {mix_urun_sayisi}")

    # -------------------------------------------
    # 5) MIX HAVUZU İÇİN GA MOTORUNU ÇALIŞTIR
    # -------------------------------------------
    best = None
    history = []

    if mix_pool:  
        print("\nGA (MIX havuzu için) çalışıyor...\n")

        # Dinamik Hesaplama
        d_pop, d_gen = calculate_dynamic_params(len(mix_pool))

        best, history = run_ga(
            urunler=mix_pool,
            palet_cfg=palet_cfg,
            population_size=d_pop,
            generations=d_gen,
        )
    else:        
        print("\nMIX havuzunda ürün yok, GA çalıştırılmayacak.\n")

    # -------------------------------------------
    # 6) SONUÇLARI YAZDIR
    # -------------------------------------------

    print("\n=== ÖZET ===")
    print(f"Toplam ürün sayısı      : {len(tum_urunler)}")
    print(f"Single palet sayısı     : {single_palet_sayisi}")
    print(f"Single palet ürün sayısı: {single_urun_sayisi}")
    print(f"MIX havuzu ürün sayısı  : {mix_urun_sayisi}")

    # MIX GA sonucu
    print("\n=== GA SONUÇ (MIX) ===")
    if best is None:
        print("Mix havuzunda ürün yok, GA sonucu yok.")
        mix_pallets = []
    else:
        print(f"En iyi fitness (MIX): {best.fitness:.2f}")
        print(f"Mix palet sayısı    : {best.palet_sayisi}")
        print(f"Mix ort. doluluk    : {best.ortalama_doluluk:.3f}")
        mix_pallets = basit_palet_paketleme(best, palet_cfg)

    # -------------------------------------------
    # 7) TOPLAM PALET VE GENEL DOLULUK
    # -------------------------------------------
    toplam_palet_sayisi = single_palet_sayisi + len(mix_pallets)
    if toplam_palet_sayisi > 0:
        toplam_doluluk = sum(p["fill_ratio"] for p in single_pallets) + sum(
            p["fill_ratio"] for p in mix_pallets
        )
        genel_ortalama_doluluk = toplam_doluluk / toplam_palet_sayisi
    else:
        genel_ortalama_doluluk = 0.0

    print("\n=== GENEL SONUÇ ===")
    print(f"Toplam palet sayısı (single + mix): {toplam_palet_sayisi}")
    print(f"Genel ortalama doluluk            : {genel_ortalama_doluluk:.3f}")

    # -------------------------------------------
    # 8) SINGLE PALET DETAYLARI
    # -------------------------------------------
    print("\n--- SINGLE PALET DETAYLARI ---")
    if not single_pallets:
        print("Single palet yok.")
    else:
        for idx, p in enumerate(single_pallets, start=1):
            print(f"\nSingle Palet {idx}:")
            print(f"  Ürün kodu: {p['urun_kodu']}")
            print(f"  Doluluk : {p['fill_ratio']:.3f}")
            print(f"  Ağırlık : {p['weight']:.1f} kg")
            print(f"  Ürün sayısı: {len(p['urunler'])}")

    # -------------------------------------------
    # 9) MIX PALET DETAYLARI
    # -------------------------------------------
    print("\n--- MIX PALET DETAYLARI (GA Çıktısı) ---")
    if not mix_pallets:
        print("Mix palet yok veya GA çalışmadı.")
    else:
        for idx, palet in enumerate(mix_pallets, start=1):
            print(f"\nMix Palet {idx}:")
            print(f"  Doluluk: {palet['fill_ratio']:.3f}")
            print(f"  Ağırlık: {palet['weight']:.1f} kg")
            print(f"  Ürün sayısı: {len(palet['urunler'])}")

            sayac = {}
            for u in palet["urunler"]:
                sayac[u.urun_kodu] = sayac.get(u.urun_kodu, 0) + 1

            print("  Ürün dağılımı:")
            for kod, adet in sayac.items():
                print(f"    {kod} : {adet} adet")

    # -------------------------------------------
    # 10) SON 5 NESLİN ÖZETİ (SADECE MIX GA VARSA)
    # -------------------------------------------
    if history:
        print("\n--- SON 5 NESİL (MIX GA) ---")
        for h in history[-5:]:
            print(
                f"Gen {h['generation']:3d} | "
                f"fit={h['best_fitness']:.1f} | "
                f"palet={h['palet_sayisi']} | "
                f"doluluk={h['ortalama_doluluk']:.3f}"
            )
    # -------------------------------------------
    # 11) SONUÇLARI JSON OLARAK KAYDET (GÖRSELLEŞTİRME İÇİN)
    # -------------------------------------------
    print("\nSonuçlar 'sonuc.json' dosyasına kaydediliyor...")
    
    output_data = {
        "summary": {
            "total_products": len(tum_urunler),
            "total_pallets": toplam_palet_sayisi,
            "avg_occupancy": genel_ortalama_doluluk,
            "pallet_dimensions": {
                "length": palet_cfg.length,
                "width": palet_cfg.width,
                "height": palet_cfg.height
            }
        },
        "pallets": []
    }

    # Helper: Palet verisini JSON formatına çevir
    def serialize_pallet(p_data, p_type, p_id):
        items = []
        for plc in p_data.get("placements", []): 
            items.append({
                "code": plc["urun"].urun_kodu,
                "x": plc["x"],
                "y": plc["y"],
                "z": plc["z"],
                "L": plc["L"],
                "W": plc["W"],
                "H": plc["H"],
                "weight": plc["weight"]
            })
        
        return {
            "pallet_id": p_id,
            "type": p_type,
            "fill_ratio": p_data["fill_ratio"],
            "weight": p_data["weight"],
            "items": items
        }

    # Single Paletleri Ekle
    for i, p in enumerate(single_pallets, 1):
        output_data["pallets"].append(serialize_pallet(p, "SINGLE", f"S-{i}"))

    # Mix Paletleri Ekle
    for i, p in enumerate(mix_pallets, 1):
        output_data["pallets"].append(serialize_pallet(p, "MIX", f"M-{i}"))

    # Dosyaya Yaz (ANA KLASÖRE KAYDET)
    # resolve().parent.parent -> ga_engine klasörünün bir üstüne (Akilli_palet) çıkar
    output_path = Path(__file__).resolve().parent.parent / "sonuc.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✅ Kayıt başarılı: {output_path}")

if __name__ == "__main__":
    main()
