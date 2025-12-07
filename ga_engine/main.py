"""
ga_engine.main

Bu dosya, ga_engine modülünü hızlıca test etmek için basit bir örnek içerir.
Projeye entegre etmeden önce, terminalden:

    python -m ga_engine.main

diye çalıştırıp GA'nın davranışını gözlemleyebilirsin.
"""

from dataclasses import dataclass

from .ga_core import run_ga
from .utils import PaletConfig, urun_hacmi


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


def build_dummy_data():
    """
    Sadece test için sahte ürün datası üretir.
    Gerçek projede Django modellerinden gelen Urun listesi kullanılacak.
    """
    urunler = []

    # Örnek: aynı tipten 40 kutu (single adayına benzer)
    for i in range(40):
        urunler.append(
            DummyUrun(
                urun_kodu="A",
                boy=40,
                en=30,
                yukseklik=20,
                agirlik=10,
            )
        )

    # Örnek: başka tipten 20 kutu
    for i in range(20):
        urunler.append(
            DummyUrun(
                urun_kodu="B",
                boy=30,
                en=20,
                yukseklik=15,
                agirlik=8,
            )
        )

    return urunler


def main():
    urunler = build_dummy_data()
    palet_cfg = PaletConfig(length=120, width=100, height=180, max_weight=1250)

    print(f"Toplam ürün: {len(urunler)}")
    toplam_hacim = sum(urun_hacmi(u) for u in urunler)
    print(f"Toplam hacim: {toplam_hacim:.2f}")
    print(f"Palet hacmi: {palet_cfg.volume:.2f}")

    best, history = run_ga(
        urunler=urunler,
        palet_cfg=palet_cfg,
        population_size=40,
        generations=80,
    )

    print("\n=== GA SONUÇ ===")
    print(f"En iyi fitness: {best.fitness:.2f}")
    print(f"Kullanılan palet sayısı: {best.palet_sayisi}")
    print(f"Ortalama doluluk: {best.ortalama_doluluk:.3f}")

    # Son birkaç neslin özeti
    print("\nSon 5 nesil özeti:")
    for h in history[-5:]:
        print(
            f"Gen {h['generation']:3d} | "
            f"fit={h['best_fitness']:.1f} | "
            f"palet={h['palet_sayisi']} | "
            f"doluluk={h['ortalama_doluluk']:.3f}"
        )


if __name__ == "__main__":
    main()
