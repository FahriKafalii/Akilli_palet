import random


class Chromosome:
    """
    GA bireyini temsil eder.

    - sira_gen : ürünlerin yerleştirilme sırası (permutasyon)
    - rot_gen  : her ürün için seçilen rotasyon index'i
                 (0 veya 1 → X-Y düzleminde iki olası yön)
    """

    def __init__(self, urunler, sira_gen=None, rot_gen=None):
        self.urunler = urunler
        self.n = len(urunler)

        # 1) SIRA GENİ (PERMÜTASYON)
        if sira_gen is None:
            self.sira_gen = list(range(self.n))
            random.shuffle(self.sira_gen)
        else:
            self.sira_gen = list(sira_gen)

        # 2) ROTASYON GENİ (HER ÜRÜN İÇİN 0–1)
        if rot_gen is None:
            # 0: (boy, en, yuk)
            # 1: (en, boy, yuk)
            self.rot_gen = [random.randint(0, 1) for _ in range(self.n)]
        else:
            # Dışarıdan gelen listeyi de 0/1'e clamp etmek istersen burayı sıkılaştırabiliriz,
            # şimdilik olduğu gibi alıyoruz.
            self.rot_gen = list(rot_gen)

        # 3) FİTNESS BİLGİLERİ
        self.fitness = 0.0
        self.palet_sayisi = 0
        self.ortalama_doluluk = 0.0
        self.yerlesmemis_urun_sayisi = 0

    def copy(self):
        """Kromozomun tam bir kopyasını üretir."""
        yeni = Chromosome(
            urunler=self.urunler,
            sira_gen=self.sira_gen.copy(),
            rot_gen=self.rot_gen.copy(),
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
