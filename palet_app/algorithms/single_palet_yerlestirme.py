"""
Single Palet Yerleştirme Algoritması (Maximal Empty Spaces yaklaşımı)
"""

class Bosluk:
    """Paletin içindeki boş bir dikdörtgen alanı temsil eder"""
    def __init__(self, x, y, z, en, boy, yukseklik):
        self.x = x
        self.y = y
        self.z = z
        self.en = en
        self.boy = boy
        self.yukseklik = yukseklik
    
    def hacim(self):
        """Boşluğun hacmini döner"""
        return self.en * self.boy * self.yukseklik
    
    def sigiyor_mu(self, urun_en, urun_boy, urun_yukseklik):
        """Verilen boyuttaki ürün bu boşluğa sığıyor mu?"""
        return (urun_en <= self.en and 
                urun_boy <= self.boy and 
                urun_yukseklik <= self.yukseklik)
    
    def __repr__(self):
        return f"Bosluk(pos=({self.x},{self.y},{self.z}), size=({self.en},{self.boy},{self.yukseklik}))"


def urunleri_grupla(urunler):
    """Ürünleri kodlarına göre gruplar."""
    gruplar = {} 
    for urun in urunler:
        if urun.urun_kodu not in gruplar:
            gruplar[urun.urun_kodu] = []
        gruplar[urun.urun_kodu].append(urun)
    return gruplar



def single_palet_yerlestirme(urunler, container_info, optimization):
    """Aynı tür ürünleri single paletlere yerleştirir."""
    from ..models import Palet
    
    gruplar = urunleri_grupla(urunler)
    
    yerlestirilmis_paletler = []
    yerlesmemis_urunler = []
    palet_id = 1
    max_palet_sayisi = 50
    
    for urun_kodu, grup_urunleri in gruplar.items():
        print(f"Single palet oluşturuluyor: {urun_kodu}, Toplam ürün: {len(grup_urunleri)}")

        if len(grup_urunleri) > 0 and len(yerlestirilmis_paletler) < max_palet_sayisi:

            palet = Palet(
                optimization=optimization,
                palet_id=palet_id,
                palet_tipi=None,
                palet_turu='single',
                custom_en=container_info.get('width', 100),
                custom_boy=container_info.get('length', 120),
                custom_max_yukseklik=container_info.get('height', 180),
                custom_max_agirlik=container_info.get('weight', 1250)
            )
            palet.save()

            yerlesen, konumlar, boyutlar = en_iyi_single_palet_yerlesim(grup_urunleri, palet)

            doluluk = palet.doluluk_orani()
            if doluluk >= 85.0:
                print(f"Single palet {palet_id}: {len(yerlesen)} ürün yerleştirildi, % {doluluk:.2f} doluluk - KABUL")
                palet.urun_konumlari = konumlar
                palet.urun_boyutlari = boyutlar
                palet.save()

                yerlestirilmis_paletler.append(palet)
                palet_id += 1

                for urun in yerlesen:
                    grup_urunleri.remove(urun)
                if grup_urunleri:
                    yerlesmemis_urunler.extend(grup_urunleri)

            else:
                print(f"Single palet {palet_id}: {len(yerlesen)} ürün yerleştirildi ama % {doluluk:.2f} - RED")
                palet.delete()
                yerlesmemis_urunler.extend(grup_urunleri)

    return yerlestirilmis_paletler, yerlesmemis_urunler



def boslugu_bol(bosluk, urun_konum, urun_boyut):
    """
    Yerleştirilen üründen sonra boşluğu 3 alt boşluğa böl.
    """
    ux, uy, uz = urun_konum
    u_en, u_boy, u_yuk = urun_boyut
    
    yeni = []

    # Sağ boşluk (X ekseni)
    if bosluk.en > u_en:
        yeni.append(Bosluk(
            x=bosluk.x + u_en,
            y=bosluk.y,
            z=bosluk.z,
            en=bosluk.en - u_en,
            boy=bosluk.boy,
            yukseklik=bosluk.yukseklik
        ))

    # Arka boşluk (Y ekseni)
    if bosluk.boy > u_boy:
        yeni.append(Bosluk(
            x=bosluk.x,
            y=bosluk.y + u_boy,
            z=bosluk.z,
            en=bosluk.en,   # Ürünün eni kadar
            boy=bosluk.boy - u_boy,
            yukseklik=bosluk.yukseklik
        ))

    # Üst boşluk (Z ekseni)
    if bosluk.yukseklik > u_yuk:
        yeni.append(Bosluk(
            x=bosluk.x,
            y=bosluk.y,
            z=bosluk.z + u_yuk,
            en=bosluk.en,
            boy=bosluk.boy,
            yukseklik=bosluk.yukseklik - u_yuk
        ))

    return [b for b in yeni if b.hacim() > 0]



def en_iyi_single_palet_yerlesim(urunler, palet, strateji='best_fit'):
    """
    Single palet için MES yerleştirme + global optimum rotasyon seçimi.
    """
    import time
    baslangic = time.time()
    timeout = 60

    yerlesen_urunler = []
    urun_konumlari = {}
    urun_boyutlari = {}

    bosluklar = [Bosluk(0, 0, 0, palet.en, palet.boy, palet.max_yukseklik)]

    # --- GLOBAL EN İYİ ROTASYON SEÇİMİ ---
    ilk = urunler[0]
    rotlar = ilk.possible_orientations()

    def kapasite(rot):
        u_en, u_boy, u_yuk = rot

        # iki eksen hizalamasını da dene
        taban1 = (palet.en // u_en) * (palet.boy // u_boy)
        taban2 = (palet.en // u_boy) * (palet.boy // u_en)

        taban = max(taban1, taban2)
        katman = palet.max_yukseklik // u_yuk

        return taban * katman

    best_rot = max(rotlar, key=kapasite)
    # -------------------------------------

    sirali = sorted(urunler, key=lambda u: u.en * u.boy * u.yukseklik, reverse=True)

    for idx, urun in enumerate(sirali):

        if time.time() - baslangic > timeout:
            print("Timeout!")
            break

        if palet.toplam_agirlik + urun.agirlik > palet.max_agirlik:
            continue

        rotasyonlar = [best_rot]  # SADECE EN İYİ ROTASYON KULLANILIR

        en_iyi_bosluk = None
        en_iyi_skor = float('inf')
        en_iyi_rotasyon = None

        for b in bosluklar:
            for r in rotasyonlar:
                u_en, u_boy, u_yuk = r

                if not b.sigiyor_mu(u_en, u_boy, u_yuk):
                    continue

                israf = b.hacim() - (u_en * u_boy * u_yuk)
                skor = b.z * 1000 + israf

                if skor < en_iyi_skor:
                    en_iyi_skor = skor
                    en_iyi_bosluk = b
                    en_iyi_rotasyon = r

        if not en_iyi_bosluk:
            continue

        konum = (en_iyi_bosluk.x, en_iyi_bosluk.y, en_iyi_bosluk.z)
        boyut = en_iyi_rotasyon

        yerlesen_urunler.append(urun)
        urun_konumlari[str(urun.id)] = konum
        urun_boyutlari[str(urun.id)] = boyut

        u_en, u_boy, u_yuk = boyut
        palet.kullanilan_hacim += u_en * u_boy * u_yuk
        palet.toplam_agirlik += urun.agirlik

        bosluklar.remove(en_iyi_bosluk)
        yeni = boslugu_bol(en_iyi_bosluk, konum, boyut)
        bosluklar.extend(yeni)

        bosluklar.sort(key=lambda b: b.hacim(), reverse=True)

    return yerlesen_urunler, urun_konumlari, urun_boyutlari