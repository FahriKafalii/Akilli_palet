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

def palet_gorsellestir(palet, urunler, save_to_file=True):
    """
    Matplotlib ile 3D palet görselleştirme
    
    Args:
        palet: Django Palet modeli
        urunler: Ürün listesi
        save_to_file: True ise PNG olarak kaydeder ve path döndürür
        
    Returns:
        ContentFile (PNG) eğer save_to_file=True
    """
    fig = plt.figure(figsize=(12, 9), dpi=100)
    ax = fig.add_subplot(111, projection='3d')
    
    # Palet boyutları
    PL, PW, PH = palet.boy, palet.en, palet.max_yukseklik
    
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
    
    if save_to_file:
        return ContentFile(buf.read())
    return buf

def ozet_grafikler_olustur(optimization):
    """Özet grafikler oluşturur - Interaktif HTML formatında (Plotly)"""
    from ..models import Palet
    
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
    except ImportError:
        # Plotly yoksa boş döndür
        return None, None
    
    paletler = Palet.objects.filter(optimization=optimization)
    single = paletler.filter(palet_turu='single').count()
    mix = paletler.filter(palet_turu='mix').count()
    
    # İstatistikleri güncelle
    optimization.single_palet = single
    optimization.mix_palet = mix
    optimization.toplam_palet = single + mix
    optimization.save()
    
    # 1. Pasta grafik
    fig1 = go.Figure(data=[go.Pie(
        labels=['Single', 'Mix'],
        values=[single, mix],
        hole=0.3,
        marker=dict(colors=['#3498db', '#e74c3c']),
        textinfo='label+percent',
        textfont_size=14
    )])
    
    fig1.update_layout(
        title=dict(text='Palet Tipi Dağılımı', x=0.5, xanchor='center'),
        height=350,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    pie_chart_html = pio.to_html(fig1, full_html=False, include_plotlyjs='cdn')
    
    # 2. Bar grafik
    ids = [f"P{p.palet_id}" for p in paletler]
    doluluklar = [p.doluluk_orani() for p in paletler]
    colors_bar = ['#3498db' if p.palet_turu == 'single' else '#e74c3c' for p in paletler]
    
    fig2 = go.Figure()
    
    fig2.add_trace(go.Bar(
        x=ids,
        y=doluluklar,
        marker_color=colors_bar,
        text=[f'{d:.1f}%' for d in doluluklar],
        textposition='outside',
        textfont_size=10,
        name='Doluluk'
    ))
    
    # Hedef çizgi ekle
    fig2.add_hline(y=80, line_dash="dash", line_color="green", 
                   annotation_text="Hedef %80", annotation_position="right")
    
    fig2.update_layout(
        title=dict(text='Palet Doluluk Oranları', x=0.5, xanchor='center'),
        yaxis_title='Doluluk Oranı (%)',
        yaxis_range=[0, 105],
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False
    )
    
    bar_chart_html = pio.to_html(fig2, full_html=False, include_plotlyjs='cdn')
    
    return pie_chart_html, bar_chart_html
