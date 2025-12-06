"""
Mix Palet Yerleştirme Algoritması
"""

def urunleri_sirala(urunler):
    """
    Ürünleri yerleştirme sırasına göre sıralar.
    
    Yerleştirme önceliği:
    1. Mukavemeti yüksek (alta konacak güçlü ürünler)
    2. Ağır ürünler (altta olmalı)
    3. İstiflenebilir ürünler (alta konabilecek)
    
    Args:
        urunler (list): Ürün nesnelerinin listesi
    
    Returns:
        list: Sıralanmış ürün nesnelerinin listesi
    """
    return sorted(
        urunler, 
        key=lambda urun: (
            -urun.mukavemet,    # Mukavemeti yüksek olanlar önce (- işareti ile)
            -urun.agirlik,      # Ağır olanlar önce
            -int(urun.istiflenebilir) # İstiflenebilir olanlar önce (True=1, False=0)
        )
    )

def mix_palet_yerlestirme(yerlesmemis_urunler, container_info, optimization, baslangic_palet_id=1):
    """
    Karışık ürünleri mix paletlere yerleştirir.
    
    Args:
        yerlesmemis_urunler (list): Yerleştirilecek ürünlerin listesi
        container_info (dict): Container bilgileri (length, width, height, weight)
        optimization: Optimizasyon nesnesi
        baslangic_palet_id (int): Başlangıç palet ID'si
    
    Returns:
        list: Yerleştirilen paletlerin listesi
    """
    from ..models import Palet
    
    # Ürünleri kurallara göre sırala
    sirali_urunler = urunleri_sirala(yerlesmemis_urunler)
    
    yerlestirilmis_paletler = []
    palet_id = baslangic_palet_id
    
    # Yerleştirilecek ürün kalmadıysa bitir
    max_palet_sayisi = 50  # Maksimum palet sayısı (sonsuz döngü önleme)
    
    while len(sirali_urunler) > 0 and len(yerlestirilmis_paletler) < max_palet_sayisi:
        print(f"Mix palet {palet_id} oluşturuluyor. Kalan ürün: {len(sirali_urunler)}")
        
        # Yeni mix palet oluştur (dinamik container bilgileriyle)
        palet = Palet(
            optimization=optimization,
            palet_id=palet_id,
            palet_tipi=None,  # Artık sabit tip kullanmıyoruz
            palet_turu='mix',
            custom_en=container_info.get('width', 100),
            custom_boy=container_info.get('length', 120),
            custom_max_yukseklik=container_info.get('height', 180),
            custom_max_agirlik=container_info.get('weight', 1250)
        )
        palet.save()
        
        # Bu palete yerleştirilen ürünler
        yerlesen_urunler, urun_konumlari, urun_boyutlari = en_iyi_mix_palet_yerlesim(sirali_urunler, palet)
        
        # Doluluk oranı kontrolü
        if palet.doluluk_orani() >= 75.0:
            # Bu palet yeterince dolu, kabul et
            palet.urun_konumlari = urun_konumlari
            palet.urun_boyutlari = urun_boyutlari
            
            # Eğer palete tek tip ürün yerleşmişse, palet türünü 'single' olarak değiştir
            if len(set(urun.urun_kodu for urun in yerlesen_urunler)) == 1:
                palet.palet_turu = 'single'
            
            palet.save()
            yerlestirilmis_paletler.append(palet)
            palet_id += 1
            
            # Yerleşen ürünleri listeden çıkar
            for urun in yerlesen_urunler:
                if urun in sirali_urunler:  # Güvenlik kontrolü
                    sirali_urunler.remove(urun)
        elif len(yerlesen_urunler) > 0:
            # Doluluk oranı az olsa bile, yerleşen ürün varsa kabul et
            palet.urun_konumlari = urun_konumlari
            palet.urun_boyutlari = urun_boyutlari
            
            # Eğer palete tek tip ürün yerleşmişse, palet türünü 'single' olarak değiştir
            if len(set(urun.urun_kodu for urun in yerlesen_urunler)) == 1:
                palet.palet_turu = 'single'
            
            palet.save()
            yerlestirilmis_paletler.append(palet)
            palet_id += 1
            
            # Yerleşen ürünleri listeden çıkar
            for urun in yerlesen_urunler:
                if urun in sirali_urunler:  # Güvenlik kontrolü
                    sirali_urunler.remove(urun)
        else:
            # Hiç ürün yerleşmediyse, bu paleti sil ve bitir (sonsuz döngüyü engelle)
            palet.delete()
            break
    
    return yerlestirilmis_paletler

def en_iyi_mix_yerlesim_bul(urun, palet, mevcut_urunler, urun_konumlari, urun_boyutlari):
    """
    Ürünün mix palete yerleştirilebileceği en iyi konumu bulur.
    
    Args:
        urun: Yerleştirilecek ürün
        palet: Palet nesnesi
        mevcut_urunler: Paletin içindeki mevcut ürünler
        urun_konumlari: Mevcut ürünlerin konumları
        urun_boyutlari: Mevcut ürünlerin boyutları
    
    Returns:
        tuple: (konum, boyut) veya yerleşemiyorsa (None, None)
    """
    # Ürün döndürülebilir mi?
    olasi_yonelimler = urun.possible_orientations()
    
    en_az_bosluk = float('inf')
    en_iyi_konum = None
    en_iyi_boyut = None
    
    # Paletin boş olması durumu
    if len(mevcut_urunler) == 0:
        return (0, 0, 0), olasi_yonelimler[0]
    
    # Her olası yönelim için dene
    for boyut in olasi_yonelimler:
        b, e, h = boyut
        
        # Olası tüm konumları dene (optimize edilmiş grid search)
        olasi_z_degerleri = [0]  # Z=0 (taban) her zaman bir seçenek
        
        # Mevcut ürünlerin üst kısımlarını da olası z değeri olarak ekle
        for mevcut_urun in mevcut_urunler:
            m_konum = urun_konumlari.get(str(mevcut_urun.id), (0, 0, 0))
            m_boyut = urun_boyutlari.get(str(mevcut_urun.id), (0, 0, 0))
            mz = m_konum[2] + m_boyut[2]
            if mz not in olasi_z_degerleri:
                olasi_z_degerleri.append(mz)
        
        # Her olası konum için dene (adım boyutlarını artırarak optimizasyon)
        # Daha büyük adımlarla ilerle (container boyutuna göre adaptif)
        adim_boyutu = max(10, int(min(palet.en, palet.boy) / 20))  # Daha büyük adımlar
        for x in range(0, max(1, int(palet.en) - int(b) + 1), adim_boyutu):
            for y in range(0, max(1, int(palet.boy) - int(e) + 1), adim_boyutu):
                for z in olasi_z_degerleri:
                    konum = (x, y, z)
                    
                    # Kurallara uygunluk kontrolü
                    if kurallara_uygun_mu(urun, konum, boyut, palet, mevcut_urunler, urun_konumlari, urun_boyutlari):
                        # Boşluk miktarını hesapla (daha az boşluk = daha iyi yerleşim)
                        bosluk = hesapla_bosluk(konum, boyut, palet, mevcut_urunler, urun_konumlari, urun_boyutlari)
                        
                        # Daha iyi bir yerleşim bulunduysa güncelle
                        if bosluk < en_az_bosluk:
                            en_az_bosluk = bosluk
                            en_iyi_konum = konum
                            en_iyi_boyut = boyut
    
    return en_iyi_konum, en_iyi_boyut

def hesapla_bosluk(konum, boyut, palet, mevcut_urunler, urun_konumlari, urun_boyutlari):
    """
    Yerleşim sonrası oluşacak boşluk miktarını hesaplar.
    
    Args:
        konum: Ürünün konumu (x, y, z)
        boyut: Ürünün boyutu (boy, en, yükseklik)
        palet: Palet nesnesi
        mevcut_urunler: Paletin içindeki mevcut ürünler
        urun_konumlari: Mevcut ürünlerin konumları
        urun_boyutlari: Mevcut ürünlerin boyutları
    
    Returns:
        float: Boşluk skoru (düşük = daha iyi)
    """
    x, y, z = konum
    b, e, h = boyut
    
    # Taban mesafesi: Ürün tabana ne kadar yakın yerleşiyor? (düşük = iyi)
    taban_mesafesi = z
    
    # Kenar mesafesi: Ürün kenarlara ne kadar yakın? (düşük = iyi)
    kenar_mesafesi = min(x, palet.en - (x + b)) + min(y, palet.boy - (y + e))
    
    # Diğer ürünlerle temas: Ne kadar fazla temas varsa o kadar iyi (yüksek = iyi)
    temas = 0
    for mevcut_urun in mevcut_urunler:
        m_konum = urun_konumlari.get(str(mevcut_urun.id), (0, 0, 0))
        m_boyut = urun_boyutlari.get(str(mevcut_urun.id), (0, 0, 0))
        
        mx, my, mz = m_konum
        mb, me, mh = m_boyut
        
        # X ekseninde temas var mı?
        x_temas = (x <= mx + mb and x + b >= mx)
        # Y ekseninde temas var mı?
        y_temas = (y <= my + me and y + e >= my)
        # Z ekseninde temas var mı?
        z_temas = (z <= mz + mh and z + h >= mz)
        
        # İki ürün arasında en az bir yüzey teması varsa
        if (x_temas and y_temas and (z == mz + mh or z + h == mz)) or \
           (x_temas and z_temas and (y == my + me or y + e == my)) or \
           (y_temas and z_temas and (x == mx + mb or x + b == mx)):
            temas += 1
    
    # Boşluk skoru: Düşük taban mesafesi, düşük kenar mesafesi, yüksek temas = iyi yerleşim
    return taban_mesafesi + kenar_mesafesi - temas * 10

def kurallara_uygun_mu(urun, konum, boyut, palet, mevcut_urunler, urun_konumlari, urun_boyutlari):
    """
    Ürünün belirtilen konumda kurallara uygun olup olmadığını kontrol eder.
    
    Kurallar:
    1. Palet sınırları içinde olmalı
    2. Diğer ürünlerle çakışmamalı
    3. Dönüş serbest değilse: ürün döndürülemez
    4. İstiflenemezse: üstüne ürün koyulmaz
    5. Ağır ürünler hafiflerin üzerine konmaz
    6. Zayıf (düşük mukavemetli) ürünler alta konmaz
    
    Returns:
        bool: Kurallara uygunsa True, değilse False
    """
    x, y, z = konum
    b, e, h = boyut
    
    # Palet sınırları kontrolü
    if (x < 0 or x + b > palet.en or 
        y < 0 or y + e > palet.boy or 
        z < 0 or z + h > palet.max_yukseklik):
        return False
    
    # Çakışma kontrolü
    for mevcut_urun in mevcut_urunler:
        m_konum = urun_konumlari.get(str(mevcut_urun.id), (0, 0, 0))
        m_boyut = urun_boyutlari.get(str(mevcut_urun.id), (0, 0, 0))
        
        mx, my, mz = m_konum
        mb, me, mh = m_boyut
        
        # İki ürün arasında çakışma var mı?
        if (x < mx + mb and x + b > mx and
            y < my + me and y + e > my and
            z < mz + mh and z + h > mz):
            return False
    
    # Dönüş kontrolü
    if not urun.donus_serbest and boyut != (urun.boy, urun.en, urun.yukseklik):
        return False
    
    # Ürünün altında kalan ürünleri kontrol et
    if z > 0:
        alt_urunler = []
        for mevcut_urun in mevcut_urunler:
            m_konum = urun_konumlari.get(str(mevcut_urun.id), (0, 0, 0))
            m_boyut = urun_boyutlari.get(str(mevcut_urun.id), (0, 0, 0))
            
            mx, my, mz = m_konum
            mb, me, mh = m_boyut
            
            # Mevcut ürün, yeni ürünün altında mı?
            if (mx < x + b and mx + mb > x and 
                my < y + e and my + me > y and 
                mz + mh == z):
                
                # Alttaki ürün istiflemeye uygun değilse
                if not mevcut_urun.istiflenebilir:
                    return False
                
                # Ağır ürün hafif ürünün üstüne konmamalı
                if urun.agirlik > mevcut_urun.agirlik * 1.5:  # 1.5 güvenlik katsayısı
                    return False
                
                # Üstteki ürünün ağırlığı alttaki ürünün mukavemetini aşmamalı
                if urun.agirlik > mevcut_urun.mukavemet:
                    return False
                
                alt_urunler.append(mevcut_urun)
        
        # Ürünün altında hiç ürün yoksa ve z > 0 ise yüzen bir ürün olur, izin verme
        if z > 0 and not alt_urunler:
            return False
    
    # Ürünün üzerinde duran ürünleri kontrol et (simülasyon için)
    for mevcut_urun in mevcut_urunler:
        m_konum = urun_konumlari.get(str(mevcut_urun.id), (0, 0, 0))
        m_boyut = urun_boyutlari.get(str(mevcut_urun.id), (0, 0, 0))
        
        mx, my, mz = m_konum
        mb, me, mh = m_boyut
        
        # Mevcut ürün, yeni ürünün üzerinde mi?
        if (mx < x + b and mx + mb > x and 
            my < y + e and my + me > y and 
            mz == z + h):
            
            # Üstteki ürün, yeni ürünün mukavemetini aşıyorsa
            if mevcut_urun.agirlik > urun.mukavemet:
                return False
            
            # Yeni ürün istiflemeye uygun değilse
            if not urun.istiflenebilir:
                return False
    
    return True

def en_iyi_mix_palet_yerlesim(urunler, palet):
    """
    Verilen ürünleri mix palete en iyi şekilde yerleştirir.
    
    Args:
        urunler (list): Yerleştirilecek ürünlerin listesi
        palet (Palet): Yerleştirilecek palet
    
    Returns:
        tuple: (yerleştirilen_ürünler, ürün_konumları, ürün_boyutları)
    """
    import time
    baslangic_zamani = time.time()
    max_sure = 30  # Maksimum 30 saniye
    
    yerlesen_urunler = []
    urun_konumlari = {}
    urun_boyutlari = {}
    
    # Belirli bir hacme ulaşana kadar veya tüm ürünleri deneyene kadar devam et
    kalan_urunler = list(urunler)  # Kopyasını oluştur
    deneme_sayisi = 0
    max_deneme = 100  # Maksimum deneme sayısı
    
    while kalan_urunler and palet.kullanilan_hacim < palet.hacim() * 0.75:  # %75 doluluk hedefi
        # Timeout kontrolü
        if time.time() - baslangic_zamani > max_sure:
            print(f"Timeout: Mix palet yerleştirme {max_sure} saniyeyi aştı. Mevcut durum kaydediliyor.")
            break
        
        deneme_sayisi += 1
        if deneme_sayisi > max_deneme:
            print(f"Maksimum deneme sayısına ulaşıldı ({max_deneme}). Mevcut durum kaydediliyor.")
            break
        en_iyi_urun = None
        en_iyi_konum = None
        en_iyi_boyut = None
        en_iyi_skor = float('inf')
        
        # Her ürün için en iyi yerleşimi dene
        for urun in kalan_urunler:
            konum, boyut = en_iyi_mix_yerlesim_bul(urun, palet, yerlesen_urunler, urun_konumlari, urun_boyutlari)
            
            if konum is not None and boyut is not None:
                # Bu ürün için boşluk skoru hesapla
                skor = hesapla_bosluk(konum, boyut, palet, yerlesen_urunler, urun_konumlari, urun_boyutlari)
                
                # Daha iyi bir yerleşim bulunduysa güncelle
                if skor < en_iyi_skor:
                    en_iyi_skor = skor
                    en_iyi_urun = urun
                    en_iyi_konum = konum
                    en_iyi_boyut = boyut
        
        # Eğer hiçbir ürün yerleşmediyse döngüyü kır
        if en_iyi_urun is None:
            break
        
        # En iyi ürünü yerleştir
        yerlesen_urunler.append(en_iyi_urun)
        urun_konumlari[str(en_iyi_urun.id)] = en_iyi_konum
        urun_boyutlari[str(en_iyi_urun.id)] = en_iyi_boyut
        
        # Paletin doluluk ve ağırlık değerlerini güncelle
        b, e, h = en_iyi_boyut
        palet.kullanilan_hacim += b * e * h
        palet.toplam_agirlik += en_iyi_urun.agirlik
        
        # Yerleşen ürünü kalan ürünlerden çıkar
        kalan_urunler.remove(en_iyi_urun)
    
    return yerlesen_urunler, urun_konumlari, urun_boyutlari 