"""
ga_engine.main

Bu dosya, GA motorunu şirketten gelen JSON dosyasıyla test etmek için kullanılır.

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
    convert_json_packages_to_products,
    basit_palet_paketleme,
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


def main():
    # -----------------------------
    # 1) JSON DOSYASINI YÜKLE
    # -----------------------------
    json_path = Path(__file__).resolve().parent.parent / "test_data" / "0114.json"

    print(f"JSON yükleniyor: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # -------------------------------------------
    # 2) JSON → ÜRÜN LİSTESİNE DÖNÜŞTÜR
    # -------------------------------------------
    urunler = convert_json_packages_to_products(data, DummyUrun)

    print(f"Toplam ürün adedi (hesaplanan): {len(urunler)}")

    toplam_hacim = sum(urun_hacmi(u) for u in urunler)
    print(f"Toplam ürün hacmi: {toplam_hacim:.2f} cm³")

    # -------------------------------------------
    # 3) PALET PARAMETRELERİNİ AYARLA
    # -------------------------------------------
    palet_cfg = PaletConfig(length=120, width=100, height=180, max_weight=1250)

    print(f"Palet hacmi: {palet_cfg.volume:.2f} cm³")

    # -------------------------------------------
    # 4) GA MOTORUNU ÇALIŞTIR
    # -------------------------------------------
    print("\nGA Çalışıyor...\n")

    best, history = run_ga(
        urunler=urunler,
        palet_cfg=palet_cfg,
        population_size=50,
        generations=120,
    )

    # -------------------------------------------
    # 5) SONUÇLARI YAZDIR
    # -------------------------------------------
    print("\n=== GA SONUÇ ===")
    print(f"En iyi fitness: {best.fitness:.2f}")
    print(f"Kullanılan palet sayısı: {best.palet_sayisi}")
    print(f"Ortalama doluluk: {best.ortalama_doluluk:.3f}")

    # -------------------------------------------
    # 6) PALET DETAYLARINI YAZDIR
    # -------------------------------------------
    print("\n--- PALET DETAYLARI ---")
    best_pallets = basit_palet_paketleme(best, palet_cfg)

    for idx, palet in enumerate(best_pallets, start=1):
        print(f"\nPalet {idx}:")
        print(f"  Doluluk: {palet['fill_ratio']:.3f}")
        print(f"  Ağırlık: {palet['weight']:.1f} kg")
        print(f"  Ürün sayısı: {len(palet['urunler'])}")

        # Ürünleri tip tip say
        sayac = {}
        for u in palet["urunler"]:
            sayac[u.urun_kodu] = sayac.get(u.urun_kodu, 0) + 1

        print("  Ürün dağılımı:")
        for kod, adet in sayac.items():
            print(f"    {kod} : {adet} adet")

    # -------------------------------------------
    # 7) SON 5 NESLİN ÖZETİ
    # -------------------------------------------
    print("\n--- SON 5 NESİL ---")
    for h in history[-5:]:
        print(
            f"Gen {h['generation']:3d} | "
            f"fit={h['best_fitness']:.1f} | "
            f"palet={h['palet_sayisi']} | "
            f"doluluk={h['ortalama_doluluk']:.3f}"
        )


if __name__ == "__main__":
    main()
