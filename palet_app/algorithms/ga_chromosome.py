import random


class Chromosome:
    """
    GA bireyini temsil eder - SEQUENCE-ONLY MODE (Auto-Orientation).

    CRITICAL: Motor now handles rotations automatically.
    GA only optimizes the ORDER (sequence) of items.
    
    - sira_gen : ürünlerin yerleştirilme sırası (permütasyon)
    """

    def __init__(self, urunler, sira_gen=None):
        self.urunler = urunler
        self.n = len(urunler)

        # SIRA GENİ (PERMÜTASYON) - GA's only focus
        if sira_gen is None:
            self.sira_gen = list(range(self.n))
            random.shuffle(self.sira_gen)
        else:
            self.sira_gen = list(sira_gen)

        # FİTNESS BİLGİLERİ
        self.fitness = 0.0
        self.palet_sayisi = 0
        self.ortalama_doluluk = 0.0
        self.yerlesmemis_urun_sayisi = 0

    def copy(self):
        """Kromozomun tam bir kopyasını üretir."""
        yeni = Chromosome(
            urunler=self.urunler,
            sira_gen=self.sira_gen.copy()
        )
        yeni.fitness = self.fitness
        yeni.palet_sayisi = self.palet_sayisi
        yeni.ortalama_doluluk = self.ortalama_doluluk
        yeni.yerlesmemis_urun_sayisi = self.yerlesmemis_urun_sayisi
        return yeni

    def __repr__(self):
        return (
            f"<Chromosome fitness={self.fitness:.2f} "
            f"palet={self.palet_sayisi} doluluk={self.ortalama_doluluk:.2f}>"
        )
