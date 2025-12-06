"""
Palet yerleştirme görselleştirme fonksiyonları
"""
import io
import matplotlib
matplotlib.use('Agg')  # GUI olmadan çalışması için
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import random
from django.core.files.base import ContentFile

def renk_uret(sayi=None):
    """Rastgele parlak bir renk üretir."""
    if sayi is not None:
        # Belirli bir sayı için her zaman aynı rengi üret (tutarlılık için)
        random.seed(sayi)
        r = random.uniform(0.4, 0.8)
        g = random.uniform(0.4, 0.8)
        b = random.uniform(0.4, 0.8)
        random.seed()  # Reset seed
        return (r, g, b)
    else:
        r = random.uniform(0.4, 0.8)
        g = random.uniform(0.4, 0.8)
        b = random.uniform(0.4, 0.8)
        return (r, g, b)

def kutu_olustur(konum, boyut, renk):
    """
    3D kutu oluşturur. Köşe noktalarını hesaplar.
    
    Args:
        konum (tuple): (x, y, z) şeklinde konum.
        boyut (tuple): (boy, en, yükseklik) şeklinde boyut.
        renk (tuple): (r, g, b) şeklinde renk.
    
    Returns:
        tuple: Kutu köşeleri ve renk bilgisi.
    """
    x, y, z = konum
    b, e, h = boyut
    
    # Kutunun köşe koordinatlarını hesapla
    koseler = np.array([
        # Tabanı oluşturan köşeler
        [x, y, z],
        [x + b, y, z],
        [x + b, y + e, z],
        [x, y + e, z],
        # Tavanı oluşturan köşeler
        [x, y, z + h],
        [x + b, y, z + h],
        [x + b, y + e, z + h],
        [x, y + e, z + h]
    ])
    
    # Kutunun yüzlerini tanımla (her yüz 4 köşeden oluşur)
    yuzler = [
        [koseler[0], koseler[1], koseler[2], koseler[3]],  # Taban
        [koseler[4], koseler[5], koseler[6], koseler[7]],  # Tavan
        [koseler[0], koseler[1], koseler[5], koseler[4]],  # Ön
        [koseler[2], koseler[3], koseler[7], koseler[6]],  # Arka
        [koseler[0], koseler[3], koseler[7], koseler[4]],  # Sol
        [koseler[1], koseler[2], koseler[6], koseler[5]]   # Sağ
    ]
    
    return yuzler, renk

def palet_gorsellestir(palet, urunler, title=None):
    """
    Bir paletin 3D görselleştirmesini yapar ve bu görseli kaydeder.
    
    Args:
        palet: Palet nesnesi
        urunler: Paletin içindeki ürünler listesi
        title: Grafiğin başlığı
    
    Returns:
        ContentFile: Oluşturulan görsel (PNG formatında)
    """
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    if title:
        ax.set_title(title, fontsize=14, pad=20)
    else:
        # Palet türünü Türkçe'ye çevir
        palet_turu_display = "Single" if palet.palet_turu == 'single' else "Mix"
        ax.set_title(f"Palet {palet.palet_id}: {palet_turu_display} - Doluluk: {palet.doluluk_orani():.2f}%", fontsize=14, pad=20)
    
    # Paletin sınırlarını çiz (wireframe olarak)
    palet_sinirlar = np.array([
        [0, 0, 0],
        [palet.en, 0, 0],
        [palet.en, palet.boy, 0],
        [0, palet.boy, 0],
        [0, 0, palet.max_yukseklik],
        [palet.en, 0, palet.max_yukseklik],
        [palet.en, palet.boy, palet.max_yukseklik],
        [0, palet.boy, palet.max_yukseklik]
    ])
    
    # Paletim kenarlarını çiz
    kenarlar = [
        [palet_sinirlar[0], palet_sinirlar[1]],
        [palet_sinirlar[1], palet_sinirlar[2]],
        [palet_sinirlar[2], palet_sinirlar[3]],
        [palet_sinirlar[3], palet_sinirlar[0]],
        
        [palet_sinirlar[4], palet_sinirlar[5]],
        [palet_sinirlar[5], palet_sinirlar[6]],
        [palet_sinirlar[6], palet_sinirlar[7]],
        [palet_sinirlar[7], palet_sinirlar[4]],
        
        [palet_sinirlar[0], palet_sinirlar[4]],
        [palet_sinirlar[1], palet_sinirlar[5]],
        [palet_sinirlar[2], palet_sinirlar[6]],
        [palet_sinirlar[3], palet_sinirlar[7]]
    ]
    
    for kenari in kenarlar:
        xs, ys, zs = zip(*kenari)
        ax.plot(xs, ys, zs, 'k--', alpha=0.3)
    
    # Paletin tabanını çiz
    taban_noktalari = [
        [0, 0, 0],
        [palet.en, 0, 0],
        [palet.en, palet.boy, 0],
        [0, palet.boy, 0]
    ]
    ax.add_collection3d(Poly3DCollection([taban_noktalari], color='brown', alpha=0.3))
    
    # Ürün renkleri için sözlük - ürün koduna göre tutarlı renk ataması
    urun_renkleri = {}
    
    # JSON formatındaki konum ve boyut bilgilerini dict'e dönüştür
    urun_konumlari = palet.json_to_dict(palet.urun_konumlari)
    urun_boyutlari = palet.json_to_dict(palet.urun_boyutlari)
    
    # Ürünleri çiz
    for i, urun in enumerate(urunler):
        if str(urun.id) not in urun_konumlari or str(urun.id) not in urun_boyutlari:
            continue
            
        konum = urun_konumlari[str(urun.id)]
        boyut = urun_boyutlari[str(urun.id)]
        
        # Tuple'a dönüştür (JSON'dan geldiği için liste olabilir)
        if isinstance(konum, list):
            konum = tuple(konum)
        if isinstance(boyut, list):
            boyut = tuple(boyut)
        
        # Ürün kodu aynı olan ürünler aynı renkte olsun
        if urun.urun_kodu not in urun_renkleri:
            urun_renkleri[urun.urun_kodu] = renk_uret(hash(urun.urun_kodu))
        
        renk = urun_renkleri[urun.urun_kodu]
        yuzler, _ = kutu_olustur(konum, boyut, renk)
        
        # Kutuyu çiz
        ax.add_collection3d(Poly3DCollection(yuzler, facecolors=renk, edgecolors='black', alpha=0.7))
        
        # Ürünün merkezine numara yaz
        x, y, z = konum
        b, e, h = boyut
        merkez_x, merkez_y, merkez_z = x + b/2, y + e/2, z + h/2
        ax.text(merkez_x, merkez_y, merkez_z, f"{i+1}", fontsize=8, ha='center', va='center')
    
    # Eksen etiketleri - font boyutunu artır
    ax.set_xlabel('X (cm)', fontsize=12)
    ax.set_ylabel('Y (cm)', fontsize=12)
    ax.set_zlabel('Z (cm)', fontsize=12)
    
    # Eksen tick'lerinin font boyutunu da artır
    ax.tick_params(axis='x', labelsize=10)
    ax.tick_params(axis='y', labelsize=10)
    ax.tick_params(axis='z', labelsize=10)
    
    # Eşit oran ayarla
    ax.set_box_aspect([palet.en, palet.boy, palet.max_yukseklik])
    
    # Görüntü sınırlarını ayarla
    ax.set_xlim(0, palet.en)
    ax.set_ylim(0, palet.boy)
    ax.set_zlim(0, palet.max_yukseklik)
    
    # Görseli bir dosya nesnesine kaydet
    buf = io.BytesIO()
    plt.tight_layout(pad=2.0)
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    # ContentFile olarak döndür (Django'nun model.ImageField'ı için)
    return ContentFile(buf.getvalue())

def ozet_grafikler_olustur(optimization):
    """
    Optimizasyon sonuçlarını gösteren özet grafikler oluşturur:
    1. Palet tipi dağılımı (Pasta grafik)
    2. Doluluk oranları (Çubuk grafik)
    
    Args:
        optimization: Optimizasyon nesnesi
    
    Returns:
        tuple: (pie_chart, bar_chart) ContentFile nesneleri
    """
    from ..models import Palet
    
    # Veritabanından paletleri çek
    paletler = Palet.objects.filter(optimization=optimization)
    
    # Palet tiplerine göre grupla
    single_paletler = paletler.filter(palet_turu='single')
    mix_paletler = paletler.filter(palet_turu='mix')
    
    # Pasta grafik (Palet tipi dağılımı)
    fig_pie, ax_pie = plt.subplots(figsize=(8, 6))
    
    labels = ['Single Palet', 'Mix Palet']
    sizes = [single_paletler.count(), mix_paletler.count()]
    colors = ['#66b3ff', '#ff9999']
    
    if sum(sizes) > 0:  # Eğer palet varsa
        ax_pie.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    else:
        ax_pie.text(0.5, 0.5, "Veri bulunamadı", ha='center', va='center')
        
    ax_pie.axis('equal')
    ax_pie.set_title('Palet Tipi Dağılımı')
    
    # Pasta grafiği kaydet
    buf_pie = io.BytesIO()
    fig_pie.tight_layout()
    fig_pie.savefig(buf_pie, format='png', dpi=100)
    plt.close(fig_pie)
    buf_pie.seek(0)
    
    # Çubuk grafik (Doluluk oranları)
    fig_bar, ax_bar = plt.subplots(figsize=(10, 6))
    
    single_ids = [f"S{palet.palet_id}" for palet in single_paletler]
    mix_ids = [f"M{palet.palet_id}" for palet in mix_paletler]
    
    single_doluluk = [palet.doluluk_orani() for palet in single_paletler]
    mix_doluluk = [palet.doluluk_orani() for palet in mix_paletler]
    
    if single_ids:
        ax_bar.bar(single_ids, single_doluluk, color='#66b3ff', label='Single Palet')
    
    if mix_ids:
        ax_bar.bar(mix_ids, mix_doluluk, color='#ff9999', label='Mix Palet')
    
    ax_bar.axhline(y=85, color='g', linestyle='--', label='Single Hedef (%85)')
    ax_bar.axhline(y=75, color='r', linestyle='--', label='Mix Hedef (%75)')
    
    ax_bar.set_xlabel('Palet ID')
    ax_bar.set_ylabel('Doluluk Oranı (%)')
    ax_bar.set_title('Paletlerin Doluluk Oranları')
    
    if single_ids or mix_ids:
        ax_bar.legend()
    else:
        ax_bar.text(0.5, 0.5, "Veri bulunamadı", transform=ax_bar.transAxes, 
                    ha='center', va='center')
    
    # Çubuk grafiği kaydet
    buf_bar = io.BytesIO()
    fig_bar.tight_layout()
    fig_bar.savefig(buf_bar, format='png', dpi=100)
    plt.close(fig_bar)
    buf_bar.seek(0)
    
    # Optimization nesnesini güncelle
    optimization.single_palet = single_paletler.count()
    optimization.mix_palet = mix_paletler.count()
    optimization.toplam_palet = paletler.count()
    optimization.save()
    
    return ContentFile(buf_pie.getvalue()), ContentFile(buf_bar.getvalue()) 