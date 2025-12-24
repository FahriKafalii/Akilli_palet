#!/usr/bin/env python
"""
0114.json ile optimizasyon testi
"""
import os
import sys
import django
import json

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from palet_app.models import Optimization, Palet, Urun
from palet_app.algorithms.ga_core import run_ga
from palet_app.algorithms.ga_utils import PaletConfig, UrunData
from palet_app.algorithms.single_palet_yerlestirme import single_palet_yerlestirme_main

def test_optimization():
    """0114.json dosyası ile optimizasyon testi"""
    
    # 1. JSON dosyasını oku
    print("=" * 80)
    print("0114.JSON İLE OPTİMİZASYON TESTİ")
    print("=" * 80)
    
    with open('test_data/0114.json', 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    container_info = {
        'length': json_data['container']['length'],
        'width': json_data['container']['width'],
        'height': json_data['container']['height'],
        'weight': json_data['container']['weight']
    }
    
    print(f"\nContainer: {container_info['length']}x{container_info['width']}x{container_info['height']} cm, {container_info['weight']} kg")
    print(f"Container Hacim: {container_info['length'] * container_info['width'] * container_info['height']:,.0f} cm³")
    
    # 2. Ürünleri hazırla
    print("\n" + "=" * 80)
    print("ÜRÜN VERİLERİ HAZIRLANIYOR")
    print("=" * 80)
    
    urunler = []
    toplam_hacim = 0
    toplam_agirlik = 0
    
    for idx, detail in enumerate(json_data['details']):
        product = detail['product']
        quantity = detail['quantity']
        package_qty = detail.get('package_quantity')
        
        # Koli mi yoksa adet mi?
        if package_qty is not None and package_qty > 0:
            # Koli
            final_boy = product['package_length']
            final_en = product['package_width']
            final_yuk = product['package_height']
            final_agirlik = product['package_weight']
            adet = int(package_qty)
            tip = "KOLİ"
        else:
            # Adet (KG'den dönüştür)
            unit_weight = product['unit_weight']
            adet = int(quantity / unit_weight) if unit_weight > 0 else 0
            final_boy = product['unit_length']
            final_en = product['unit_width']
            final_yuk = product['unit_height']
            final_agirlik = unit_weight
            tip = "ADET"
        
        print(f"\n{idx+1}. Ürün: {product['code']} ({tip})")
        print(f"   Boyut: {final_boy}x{final_en}x{final_yuk} cm, {final_agirlik} kg")
        print(f"   Adet: {adet}")
        
        for i in range(adet):
            urun = Urun(
                id=len(urunler) + 1,
                urun_kodu=product['code'],
                urun_adi=f"{product['code']}_{idx}_{i}",
                boy=final_boy,
                en=final_en,
                yukseklik=final_yuk,
                agirlik=final_agirlik,
                mukavemet=100000,
                donus_serbest=True,
                istiflenebilir=True
            )
            urunler.append(urun)
            toplam_hacim += (final_boy * final_en * final_yuk)
            toplam_agirlik += final_agirlik
    
    print("\n" + "=" * 80)
    print(f"TOPLAM: {len(urunler)} adet ürün")
    print(f"Toplam Hacim: {toplam_hacim:,.0f} cm³")
    print(f"Toplam Ağırlık: {toplam_agirlik:,.2f} kg")
    
    container_hacim = container_info['length'] * container_info['width'] * container_info['height']
    teorik_min_palet = int(toplam_hacim / container_hacim) + 1
    print(f"Teorik Minimum Palet: {teorik_min_palet}")
    print("=" * 80)
    
    # 3. Optimizasyon objesi oluştur
    optimization = Optimization.objects.create(
        algoritma='genetic',
        container_length=container_info['length'],
        container_width=container_info['width'],
        container_height=container_info['height'],
        container_weight=container_info['weight']
    )
    
    # Ürünleri kaydet
    for urun in urunler:
        urun.save()
    
    # 4. Single Palet Optimizasyonu
    print("\n" + "=" * 80)
    print("SINGLE PALET OPTİMİZASYONU")
    print("=" * 80)
    
    single_paletler, mix_pool = single_palet_yerlestirme_main(urunler, container_info, optimization)
    
    print(f"\nSingle Palet: {len(single_paletler)} adet")
    print(f"Mix Pool: {len(mix_pool)} ürün")
    
    # 5. Mix Palet (Genetik Algoritma)
    if mix_pool:
        print("\n" + "=" * 80)
        print("MIX PALET (GENETİK ALGORİTMA)")
        print("=" * 80)
        
        palet_cfg = PaletConfig(
            length=container_info['length'],
            width=container_info['width'],
            height=container_info['height'],
            max_weight=container_info['weight']
        )
        
        # UrunData'ya çevir
        urun_data_listesi = []
        for urun in mix_pool:
            urun_data = UrunData(
                urun_id=urun.id,
                code=urun.urun_kodu,
                boy=urun.boy,
                en=urun.en,
                yukseklik=urun.yukseklik,
                agirlik=urun.agirlik,
                quantity=1,
                is_package=False
            )
            urun_data.donus_serbest = urun.donus_serbest
            urun_data.mukavemet = urun.mukavemet
            urun_data_listesi.append(urun_data)
        
        print(f"\nGA Parametreleri:")
        print(f"  - Ürün Sayısı: {len(urun_data_listesi)}")
        print(f"  - Population: 100")
        print(f"  - Generations: 200")
        print(f"  - Mutation Rate: 0.2")
        print(f"  - Tournament K: 4")
        print(f"  - Elitism: 3")
        
        # GA'yı çalıştır
        print("\nGA başlatılıyor...")
        best_chromosome, history = run_ga(
            urunler=urun_data_listesi,
            palet_cfg=palet_cfg,
            population_size=100,
            generations=200,
            mutation_rate=0.2,
            tournament_k=4,
            elitism=3
        )
        
        if best_chromosome:
            print("\n" + "=" * 80)
            print("GA SONUÇLARI")
            print("=" * 80)
            print(f"En İyi Fitness: {best_chromosome.fitness:,.2f}")
            print(f"Palet Sayısı: {best_chromosome.palet_sayisi}")
            print(f"Ortalama Doluluk: {best_chromosome.ortalama_doluluk:.2%}")
        else:
            print("\n❌ GA çözüm üretemedi!")
    
    # 6. Genel Sonuçlar
    print("\n" + "=" * 80)
    print("OPTİMİZASYON ÖZETİ")
    print("=" * 80)
    
    paletler = Palet.objects.filter(optimization=optimization)
    single_count = paletler.filter(palet_turu='single').count()
    mix_count = paletler.filter(palet_turu='mix').count()
    toplam_palet = single_count + mix_count
    
    print(f"\nToplam Palet: {toplam_palet}")
    print(f"  - Single: {single_count}")
    print(f"  - Mix: {mix_count}")
    print(f"\nTeorik Minimum: {teorik_min_palet}")
    print(f"Optimizasyon Oranı: {(teorik_min_palet / toplam_palet * 100):.1f}%" if toplam_palet > 0 else "N/A")
    
    # Doluluk oranları
    print("\n" + "-" * 80)
    print("PALET DETAYLARI")
    print("-" * 80)
    
    for palet in paletler.order_by('palet_id'):
        doluluk = palet.doluluk_orani()
        agirlik_oran = (palet.toplam_agirlik / palet.max_agirlik * 100) if palet.max_agirlik > 0 else 0
        
        print(f"\nPalet {palet.palet_id} ({palet.palet_turu.upper()}):")
        print(f"  Doluluk: {doluluk:.1f}%")
        print(f"  Ağırlık: {palet.toplam_agirlik:.1f} kg ({agirlik_oran:.1f}%)")
        print(f"  Hacim: {palet.kullanilan_hacim:,.0f} / {palet.hacim():,.0f} cm³")
    
    print("\n" + "=" * 80)
    print("TEST TAMAMLANDI")
    print("=" * 80)
    
    # Cleanup
    optimization.delete()
    Urun.objects.all().delete()

if __name__ == '__main__':
    test_optimization()
