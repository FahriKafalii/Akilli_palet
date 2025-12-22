"""
Palet Görselleştirme Modülü
"""
import matplotlib
matplotlib.use('Agg')  # GUI olmadan çalışması için
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import io
from django.core.files.base import ContentFile
import random

# Renk havuzu (tutarlılık için)
random.seed(42)
COLOR_MAP = {}

def renk_uret(code):
    """Her ürün kodu için tutarlı renk üretir"""
    if code not in COLOR_MAP:
        COLOR_MAP[code] = (
            random.random() * 0.6 + 0.2,  # 0.2-0.8 arası
            random.random() * 0.6 + 0.2,
            random.random() * 0.6 + 0.2
        )
    return COLOR_MAP[code]

def kutu_ciz(ax, x, y, z, dx, dy, dz, color):
    """3D kutu çizer (solid, iç gözükmez)"""
    # Köşe noktaları
    xx = [x, x, x+dx, x+dx, x, x, x+dx, x+dx]
    yy = [y, y+dy, y+dy, y, y, y+dy, y+dy, y]
    zz = [z, z, z, z, z+dz, z+dz, z+dz, z+dz]
    
    # 6 yüz tanımla
    vertices = [
        [0, 1, 2, 3],  # alt
        [4, 5, 6, 7],  # üst
        [0, 1, 5, 4],  # ön
        [2, 3, 7, 6],  # arka
        [1, 2, 6, 5],  # sağ
        [0, 3, 7, 4]   # sol
    ]
    
    faces = []
    for v in vertices:
        faces.append([[xx[v[i]], yy[v[i]], zz[v[i]]] for i in range(4)])
    
    # Poly3DCollection ile solid kutu
    poly = Poly3DCollection(faces, alpha=0.9, facecolor=color, edgecolor='black', linewidth=1.5)
    ax.add_collection3d(poly)

def palet_gorsellestir(palet, urunler):
    """Matplotlib ile 3D palet görselleştirme - PNG döndürür"""
    fig = plt.figure(figsize=(12, 9), dpi=100)
    ax = fig.add_subplot(111, projection='3d')
    
    # Palet boyutları
    PL, PW, PH = palet.en, palet.boy, palet.max_yukseklik
    
    urun_konumlari = palet.json_to_dict(palet.urun_konumlari)
    urun_boyutlari = palet.json_to_dict(palet.urun_boyutlari)
    
    # Ürünleri çiz
    for urun in urunler:
        uid = str(urun.id)
        if uid not in urun_konumlari:
            continue
            
        pos = urun_konumlari[uid]
        dim = urun_boyutlari[uid]
        
        if isinstance(pos, list):
            pos = tuple(pos)
        if isinstance(dim, list):
            dim = tuple(dim)
        
        renk = renk_uret(urun.urun_kodu)
        kutu_ciz(ax, pos[0], pos[1], pos[2], dim[0], dim[1], dim[2], renk)
    
    # Palet sınırlarını çiz (kırmızı çerçeve)
    ax.plot([0, PL], [0, 0], [0, 0], 'r-', linewidth=2)
    ax.plot([0, PL], [PW, PW], [0, 0], 'r-', linewidth=2)
    ax.plot([0, 0], [0, PW], [0, 0], 'r-', linewidth=2)
    ax.plot([PL, PL], [0, PW], [0, 0], 'r-', linewidth=2)
    
    ax.plot([0, PL], [0, 0], [PH, PH], 'r-', linewidth=2)
    ax.plot([0, PL], [PW, PW], [PH, PH], 'r-', linewidth=2)
    ax.plot([0, 0], [0, PW], [PH, PH], 'r-', linewidth=2)
    ax.plot([PL, PL], [0, PW], [PH, PH], 'r-', linewidth=2)
    
    ax.plot([0, 0], [0, 0], [0, PH], 'r-', linewidth=2)
    ax.plot([PL, PL], [0, 0], [0, PH], 'r-', linewidth=2)
    ax.plot([0, 0], [PW, PW], [0, PH], 'r-', linewidth=2)
    ax.plot([PL, PL], [PW, PW], [0, PH], 'r-', linewidth=2)
    
    # Eksen ayarları
    ax.set_xlabel('Boy (cm)', fontsize=10)
    ax.set_ylabel('En (cm)', fontsize=10)
    ax.set_zlabel('Yükseklik (cm)', fontsize=10)
    ax.set_xlim([0, PL])
    ax.set_ylim([0, PW])
    ax.set_zlim([0, PH])
    
    ax.set_title(f'Palet {palet.palet_id} - {palet.palet_turu.upper()}\nDoluluk: {palet.doluluk_orani():.1f}%', 
                 fontsize=12, fontweight='bold')
    
    # Görüş açısı
    ax.view_init(elev=20, azim=45)
    
    # PNG'ye kaydet
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    
    return ContentFile(buf.read())

def ozet_grafikler_olustur(optimization):
    """Özet grafikler oluşturur - PNG formatında"""
    from ..models import Palet
    
    paletler = Palet.objects.filter(optimization=optimization)
    single = paletler.filter(palet_turu='single').count()
    mix = paletler.filter(palet_turu='mix').count()
    
    # 1. Pasta grafik
    fig1, ax1 = plt.subplots(figsize=(6, 4))
    colors_pie = ['#3498db', '#e74c3c']
    ax1.pie([single, mix], labels=['Single', 'Mix'], autopct='%1.1f%%',
            colors=colors_pie, startangle=90)
    ax1.set_title('Palet Tipi Dağılımı')
    
    buf1 = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf1, format='png', dpi=100)
    buf1.seek(0)
    plt.close(fig1)
    
    # 2. Bar grafik
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    
    ids = [f"P{p.palet_id}" for p in paletler]
    doluluklar = [p.doluluk_orani() for p in paletler]
    colors_bar = ['#3498db' if p.palet_turu == 'single' else '#e74c3c' for p in paletler]
    
    bars = ax2.bar(ids, doluluklar, color=colors_bar)
    ax2.axhline(y=80, color='green', linestyle='--', linewidth=2, label='Hedef %80')
    ax2.set_ylabel('Doluluk Oranı (%)')
    ax2.set_title('Palet Doluluk Oranları')
    ax2.set_ylim([0, 100])
    ax2.legend()
    
    # Değerleri bar üstüne yaz
    for bar, val in zip(bars, doluluklar):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=8)
    
    plt.xticks(rotation=45, ha='right')
    buf2 = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf2, format='png', dpi=100)
    buf2.seek(0)
    plt.close(fig2)
    
    # İstatistikleri güncelle
    optimization.single_palet = single
    optimization.mix_palet = mix
    optimization.toplam_palet = single + mix
    optimization.save()
    
    return ContentFile(buf1.read()), ContentFile(buf2.read())
