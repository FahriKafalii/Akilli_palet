"""
Genetik Algoritma ile 3D Palet Yerleştirme
"""
import random
import time
import copy


class Birey:
    """
    Bir yerleştirme çözümünü temsil eden birey (kromozom)
    """
    def __init__(self, urunler, sira=None):
        self.urunler = urunler
        if sira is None:
            # Rastgele sıralama
            self.sira = list(range(len(urunler)))
            random.shuffle(self.sira)
        else:
            self.sira = sira
        
        self.fitness = 0.0
        self.palet_sayisi = 0
        self.doluluk_orani = 0.0
        self.yerlesmemis_urun_sayisi = 0


def fitness_hesapla(birey, container_info, optimization):
    """
    Bireyin fitness (uygunluk) değerini hesaplar.
    
    Fitness = (Doluluk Oranı × 0.4) + (Az Palet × 0.3) + (Az Yerleşmemiş × 0.3)
    
    Args:
        birey: Değerlendirilecek birey
        container_info: Container bilgileri
        optimization: Optimizasyon nesnesiç
    
    Returns:
        float: Fitness değeri (yüksek = iyi)
    """
    from ..models import Palet
    
    # Bireyin sırasına göre ürünleri sırala
    sirali_urunler = [birey.urunler[i] for i in birey.sira]
    
    # Yerleştirme simülasyonu
    paletler = []
    palet_id = 1
    max_palet = 20  # Fitness hesaplaması için maksimum
    
    kalan_urunler = list(sirali_urunler)
    
    while len(kalan_urunler) > 0 and len(paletler) < max_palet:
        # Yeni palet oluştur
        palet = Palet(
            optimization=optimization,
            palet_id=palet_id,
            palet_tipi=None,
            palet_turu='mix',
            custom_en=container_info.get('width', 100),
            custom_boy=container_info.get('length', 120),
            custom_max_yukseklik=container_info.get('height', 180),
            custom_max_agirlik=container_info.get('weight', 1250)
        )
        
        # Bu palete ürün yerleştir (hızlı versiyon)
        yerlesen_urunler, _, _ = hizli_yerlesim(kalan_urunler[:10], palet)  # İlk 10 ürün
        
        if len(yerlesen_urunler) > 0:
            paletler.append(palet)
            palet_id += 1
            
            for urun in yerlesen_urunler:
                if urun in kalan_urunler:
                    kalan_urunler.remove(urun)
        else:
            break
    
    # Fitness hesapla
    if len(paletler) == 0:
        birey.fitness = 0.0
        birey.palet_sayisi = 0
        birey.doluluk_orani = 0.0
        birey.yerlesmemis_urun_sayisi = len(kalan_urunler)
        return 0.0
    
    # Ortalama doluluk oranı
    toplam_doluluk = sum(p.doluluk_orani() for p in paletler)
    ortalama_doluluk = toplam_doluluk / len(paletler)
    
    # Fitness bileşenleri
    doluluk_skoru = ortalama_doluluk / 100.0  # 0-1 arası
    palet_skoru = 1.0 / (len(paletler) + 1)  # Az palet = yüksek skor
    yerlesmemis_skoru = 1.0 - (len(kalan_urunler) / len(birey.urunler))  # Az yerleşmemiş = yüksek
    
    fitness = (doluluk_skoru * 0.4) + (palet_skoru * 0.3) + (yerlesmemis_skoru * 0.3)
    
    # Birey bilgilerini güncelle
    birey.fitness = fitness
    birey.palet_sayisi = len(paletler)
    birey.doluluk_orani = ortalama_doluluk
    birey.yerlesmemis_urun_sayisi = len(kalan_urunler)
    
    return fitness


def hizli_yerlesim(urunler, palet):
    """
    Hızlı yerleştirme (fitness hesabı için basitleştirilmiş)
    
    Returns:
        tuple: (yerleştirilen_ürünler, konumlar, boyutlar)
    """
    yerlesen_urunler = []
    urun_konumlari = {}
    urun_boyutlari = {}
    
    current_x = 0
    current_y = 0
    current_z = 0
    max_z_bu_katmanda = 0
    
    for urun in urunler:
        # Basit yerleştirme: yan yana diz
        boyut = (urun.boy, urun.en, urun.yukseklik)
        b, e, h = boyut
        
        # Palete sığıyor mu?
        if current_x + b > palet.en:
            # Yeni satır
            current_x = 0
            current_y += e
            
        if current_y + e > palet.boy:
            # Yeni katman
            current_x = 0
            current_y = 0
            current_z += max_z_bu_katmanda
            max_z_bu_katmanda = 0
        
        # Yükseklik kontrolü
        if current_z + h > palet.max_yukseklik:
            break
        
        # Ağırlık kontrolü
        if palet.toplam_agirlik + urun.agirlik > palet.max_agirlik:
            break
        
        # Yerleştir
        konum = (current_x, current_y, current_z)
        yerlesen_urunler.append(urun)
        urun_konumlari[str(urun.id)] = konum
        urun_boyutlari[str(urun.id)] = boyut
        
        palet.kullanilan_hacim += b * e * h
        palet.toplam_agirlik += urun.agirlik
        
        current_x += b
        max_z_bu_katmanda = max(max_z_bu_katmanda, h)
    
    return yerlesen_urunler, urun_konumlari, urun_boyutlari


def secim(populasyon, elitizm_orani=0.2):
    """
    Turnuva seçimi (Tournament Selection)
    
    Args:
        populasyon: Birey listesi
        elitizm_orani: En iyi bireylerin doğrudan geçme oranı
    
    Returns:
        list: Seçilen bireyler
    """
    # Fitness'e göre sırala
    populasyon_sirali = sorted(populasyon, key=lambda x: x.fitness, reverse=True)
    
    # Elitleri doğrudan al
    elit_sayisi = int(len(populasyon) * elitizm_orani)
    secilmis = populasyon_sirali[:elit_sayisi]
    
    # Geri kalanını turnuva ile seç
    turnuva_boyutu = 3
    while len(secilmis) < len(populasyon):
        # Rastgele turnuva grubu oluştur
        turnuva = random.sample(populasyon, min(turnuva_boyutu, len(populasyon)))
        # En iyi fitness'e sahip olanı seç
        kazanan = max(turnuva, key=lambda x: x.fitness)
        secilmis.append(kazanan)
    
    return secilmis


def caprazlama(ebeveyn1, ebeveyn2):
    """
    Order Crossover (OX) - Sıra çaprazlama
    
    Args:
        ebeveyn1, ebeveyn2: Ebeveyn bireyler
    
    Returns:
        tuple: (çocuk1, çocuk2)
    """
    n = len(ebeveyn1.sira)
    
    # Rastgele iki kesim noktası seç
    kesim1 = random.randint(0, n - 2)
    kesim2 = random.randint(kesim1 + 1, n)
    
    # Çocuk 1 oluştur
    cocuk1_sira = [-1] * n
    cocuk1_sira[kesim1:kesim2] = ebeveyn1.sira[kesim1:kesim2]
    
    # Ebeveyn2'den eksik olanları ekle
    ebeveyn2_sira = [x for x in ebeveyn2.sira if x not in cocuk1_sira]
    idx = 0
    for i in range(n):
        if cocuk1_sira[i] == -1:
            cocuk1_sira[i] = ebeveyn2_sira[idx]
            idx += 1
    
    # Çocuk 2 oluştur (simetrik)
    cocuk2_sira = [-1] * n
    cocuk2_sira[kesim1:kesim2] = ebeveyn2.sira[kesim1:kesim2]
    
    ebeveyn1_sira = [x for x in ebeveyn1.sira if x not in cocuk2_sira]
    idx = 0
    for i in range(n):
        if cocuk2_sira[i] == -1:
            cocuk2_sira[i] = ebeveyn1_sira[idx]
            idx += 1
    
    cocuk1 = Birey(ebeveyn1.urunler, cocuk1_sira)
    cocuk2 = Birey(ebeveyn2.urunler, cocuk2_sira)
    
    return cocuk1, cocuk2


def mutasyon(birey, mutasyon_orani=0.1):
    """
    Swap Mutation - Rastgele iki pozisyonu değiştir
    
    Args:
        birey: Mutasyona uğrayacak birey
        mutasyon_orani: Mutasyon olasılığı
    """
    if random.random() < mutasyon_orani:
        # Rastgele iki pozisyon seç
        idx1 = random.randint(0, len(birey.sira) - 1)
        idx2 = random.randint(0, len(birey.sira) - 1)
        
        # Yer değiştir
        birey.sira[idx1], birey.sira[idx2] = birey.sira[idx2], birey.sira[idx1]


def genetik_algoritma_mix_palet(urunler, container_info, optimization, 
                                populasyon_boyutu=30,
                                nesil_sayisi=50,
                                mutasyon_orani=0.15,
                                max_sure=120):
    """
    Genetik Algoritma ile Mix Palet Yerleştirme
    
    Args:
        urunler: Yerleştirilecek ürünler
        container_info: Container bilgileri
        optimization: Optimizasyon nesnesi
        populasyon_boyutu: Popülasyondaki birey sayısı
        nesil_sayisi: Kaç nesil evrim geçireceği
        mutasyon_orani: Mutasyon olasılığı
        max_sure: Maksimum çalışma süresi (saniye)
    
    Returns:
        Birey: En iyi çözüm
    """
    print(f"🧬 Genetik Algoritma başlatılıyor...")
    print(f"   Popülasyon: {populasyon_boyutu}, Nesil: {nesil_sayisi}")
    print(f"   Ürün sayısı: {len(urunler)}")
    
    baslangic_zamani = time.time()
    
    # İlk popülasyonu oluştur
    populasyon = []
    for i in range(populasyon_boyutu):
        birey = Birey(urunler)
        fitness_hesapla(birey, container_info, optimization)
        populasyon.append(birey)
        
        if i % 10 == 0:
            print(f"   İlk popülasyon: {i}/{populasyon_boyutu}")
    
    en_iyi_birey = max(populasyon, key=lambda x: x.fitness)
    print(f"   İlk en iyi fitness: {en_iyi_birey.fitness:.4f}")
    
    # Evrim döngüsü
    for nesil in range(nesil_sayisi):
        # Timeout kontrolü
        if time.time() - baslangic_zamani > max_sure:
            print(f"⏱ Timeout: {max_sure} saniye aşıldı. En iyi çözüm döndürülüyor.")
            break
        
        # Seçim
        secilmis_populasyon = secim(populasyon)
        
        # Yeni nesil oluştur
        yeni_populasyon = []
        
        # Elitleri koru
        elit_sayisi = int(populasyon_boyutu * 0.1)
        elitler = sorted(populasyon, key=lambda x: x.fitness, reverse=True)[:elit_sayisi]
        yeni_populasyon.extend(elitler)
        
        # Çaprazlama ve mutasyon
        while len(yeni_populasyon) < populasyon_boyutu:
            # Rastgele iki ebeveyn seç
            ebeveyn1 = random.choice(secilmis_populasyon)
            ebeveyn2 = random.choice(secilmis_populasyon)
            
            # Çaprazlama
            if random.random() < 0.8:  # %80 çaprazlama olasılığı
                cocuk1, cocuk2 = caprazlama(ebeveyn1, ebeveyn2)
            else:
                cocuk1 = Birey(urunler, ebeveyn1.sira[:])
                cocuk2 = Birey(urunler, ebeveyn2.sira[:])
            
            # Mutasyon
            mutasyon(cocuk1, mutasyon_orani)
            mutasyon(cocuk2, mutasyon_orani)
            
            # Fitness hesapla
            fitness_hesapla(cocuk1, container_info, optimization)
            fitness_hesapla(cocuk2, container_info, optimization)
            
            yeni_populasyon.append(cocuk1)
            if len(yeni_populasyon) < populasyon_boyutu:
                yeni_populasyon.append(cocuk2)
        
        populasyon = yeni_populasyon
        
        # En iyi bireyi güncelle
        nesil_en_iyisi = max(populasyon, key=lambda x: x.fitness)
        if nesil_en_iyisi.fitness > en_iyi_birey.fitness:
            en_iyi_birey = nesil_en_iyisi
            print(f"✨ Nesil {nesil + 1}: YENİ EN İYİ! Fitness: {en_iyi_birey.fitness:.4f}, "
                  f"Palet: {en_iyi_birey.palet_sayisi}, Doluluk: {en_iyi_birey.doluluk_orani:.1f}%")
        elif nesil % 5 == 0:
            print(f"   Nesil {nesil + 1}: En iyi fitness: {en_iyi_birey.fitness:.4f}, "
                  f"Ortalama: {sum(b.fitness for b in populasyon)/len(populasyon):.4f}")
    
    sure = time.time() - baslangic_zamani
    print(f"🏁 Genetik Algoritma tamamlandı! Süre: {sure:.1f}s")
    print(f"   En iyi fitness: {en_iyi_birey.fitness:.4f}")
    print(f"   Palet sayısı: {en_iyi_birey.palet_sayisi}")
    print(f"   Doluluk oranı: {en_iyi_birey.doluluk_orani:.1f}%")
    print(f"   Yerleşmeyen ürün: {en_iyi_birey.yerlesmemis_urun_sayisi}")
    
    return en_iyi_birey


def genetik_sonuc_uygula(en_iyi_birey, container_info, optimization, baslangic_palet_id=1):
    """
    Genetik algoritmanın bulduğu en iyi sıralamayı gerçek yerleştirmeye uygular
    
    Args:
        en_iyi_birey: Genetik algoritmadan gelen en iyi çözüm
        container_info: Container bilgileri
        optimization: Optimizasyon nesnesi
        baslangic_palet_id: Başlangıç palet ID'si
    
    Returns:
        list: Yerleştirilen paletler
    """
    from .mix_palet_yerlestirme import en_iyi_mix_palet_yerlesim
    from ..models import Palet
    
    print(f"📦 En iyi sıralama uygulanıyor...")
    
    # Bireyin sırasına göre ürünleri sırala
    sirali_urunler = [en_iyi_birey.urunler[i] for i in en_iyi_birey.sira]
    
    yerlestirilmis_paletler = []
    palet_id = baslangic_palet_id
    max_palet_sayisi = 50
    
    while len(sirali_urunler) > 0 and len(yerlestirilmis_paletler) < max_palet_sayisi:
        print(f"   Palet {palet_id} oluşturuluyor. Kalan ürün: {len(sirali_urunler)}")
        
        # Yeni palet oluştur
        palet = Palet(
            optimization=optimization,
            palet_id=palet_id,
            palet_tipi=None,
            palet_turu='mix',
            custom_en=container_info.get('width', 100),
            custom_boy=container_info.get('length', 120),
            custom_max_yukseklik=container_info.get('height', 180),
            custom_max_agirlik=container_info.get('weight', 1250)
        )
        palet.save()
        
        # Bu palete yerleştir (detaylı algoritma ile)
        yerlesen_urunler, urun_konumlari, urun_boyutlari = en_iyi_mix_palet_yerlesim(sirali_urunler, palet)
        
        if palet.doluluk_orani() >= 50.0 or len(yerlesen_urunler) > 0:
            palet.urun_konumlari = urun_konumlari
            palet.urun_boyutlari = urun_boyutlari
            
            if len(set(urun.urun_kodu for urun in yerlesen_urunler)) == 1:
                palet.palet_turu = 'single'
            
            palet.save()
            yerlestirilmis_paletler.append(palet)
            palet_id += 1
            
            # Yerleşen ürünleri listeden çıkar
            for urun in yerlesen_urunler:
                if urun in sirali_urunler:
                    sirali_urunler.remove(urun)
        else:
            palet.delete()
            break
    
    print(f"✅ Toplam {len(yerlestirilmis_paletler)} palet oluşturuldu")
    
    return yerlestirilmis_paletler
