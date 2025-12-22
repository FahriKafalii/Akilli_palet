import json
import os
import tempfile
from threading import Thread
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import Urun, Palet, Optimization
from .algorithms.single_palet_yerlestirme import single_palet_yerlestirme
from .algorithms.mix_palet_yerlestirme import mix_palet_yerlestirme
from .algorithms.visualize import palet_gorsellestir_html, ozet_grafikler_html, renk_uret


def chromosome_to_palets(chromosome, palet_cfg, optimization, baslangic_id):
    """
    En iyi kromozomdan Django Palet nesneleri oluşturur.
    
    Args:
        chromosome: En iyi GA kromozomu
        palet_cfg: Palet konfigürasyonu
        optimization: Django Optimization nesnesi
        baslangic_id: Başlangıç palet ID'si
        
    Returns:
        list: Oluşturulan Django Palet nesnelerinin listesi
    """
    from .algorithms.ga_utils import basit_palet_paketleme
    from .models import Palet
    
    # Kromozomdan paletleri oluştur
    pallets = basit_palet_paketleme(chromosome, palet_cfg)
    
    django_paletler = []
    palet_id = baslangic_id
    
    for palet_data in pallets:
        # Yeni Django Palet objesi oluştur
        palet = Palet(
            optimization=optimization,
            palet_id=palet_id,
            palet_tipi=None,
            palet_turu='mix',
            custom_en=palet_cfg.width,
            custom_boy=palet_cfg.length,
            custom_max_yukseklik=palet_cfg.height,
            custom_max_agirlik=palet_cfg.max_weight
        )
        
        # Yerleşim bilgilerini hazırla
        urun_konumlari = {}
        urun_boyutlari = {}
        
        for placement in palet_data['placements']:
            urun = placement['urun']
            urun_id = str(urun.id)
            
            urun_konumlari[urun_id] = [
                placement['x'],
                placement['y'],
                placement['z']
            ]
            
            urun_boyutlari[urun_id] = [
                placement['L'],
                placement['W'],
                placement['H']
            ]
        
        palet.urun_konumlari = urun_konumlari
        palet.urun_boyutlari = urun_boyutlari
        palet.save()
        
        django_paletler.append(palet)
        palet_id += 1
    
    return django_paletler



def upload_result(request):
    """AJAX ile yüklenen JSON dosyasını işler"""
    if request.method != 'POST' or 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'Dosya yüklenemedi.'}, status=400)
    
    uploaded_file = request.FILES['file']
    
    # Dosyanın JSON olduğunu kontrol et
    if not uploaded_file.name.lower().endswith('.json'):
        return JsonResponse({'success': False, 'error': 'Yalnızca JSON dosyaları kabul edilir.'}, status=400)
    
    # Dosyayı geçici olarak kaydet
    temp_file_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
    
    with open(temp_file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    
    # JSON dosyasını valide et
    try:
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            yuklenen_veri = json.load(f)
        
        # Geçici dosyayı sil
        os.remove(temp_file_path)
        
        # Yeni JSON formatını parse et
        urun_verileri = []
        
        # Yeni format kontrolü: {"id": ..., "container": {...}, "details": [...]}
        if isinstance(yuklenen_veri, dict) and 'details' in yuklenen_veri:
            detaylar = yuklenen_veri.get('details', [])
            container_info = yuklenen_veri.get('container', {})
            # JSON üst düzeyindeki id bilgisini palet_id olarak ekle
            try:
                palet_id = yuklenen_veri.get('id')
                if palet_id is not None:
                    container_info['palet_id'] = palet_id
            except Exception:
                pass

            # Container bilgilerini session'a kaydet (ileride kullanmak için)
            request.session['container_info'] = container_info
            
            def to_float(x, default=0.0):
                try:
                    return float(x) if x is not None else default
                except (TypeError, ValueError):
                    return default
            
            # Her bir detail kaydını işle
            for detail in detaylar:
                product = detail.get('product', {})
                package_quantity = detail.get('package_quantity', 1)
                quantity = detail.get('quantity', 0)
                
                # Ürün kodunu al
                code = product.get('code', product.get('id', 'UNKNOWN'))
                
                # Paket boyutlarını al (package_length, package_width, package_height)
                package_length = to_float(product.get('package_length'))
                package_width = to_float(product.get('package_width'))
                package_height = to_float(product.get('package_height'))
                package_weight = to_float(product.get('package_weight'))
                
                # Birim boyutlarını al (unit_length, unit_width, unit_height)
                unit_length = to_float(product.get('unit_length'))
                unit_width = to_float(product.get('unit_width'))
                unit_height = to_float(product.get('unit_height'))
                unit_weight = to_float(product.get('unit_weight'))
                
                # Mukavemet bilgisi
                mukavemet = to_float(product.get('package_max_stack_weight'), default=100000)
                
                # Eğer mukavemet null ise yüksek bir değer ata
                if mukavemet == 0:
                    mukavemet = 100000
                
                # Her bir paket için ayrı bir kayıt oluştur
                for i in range(package_quantity):
                    urun_listesi_item = {
                        'urun_kodu': str(code),
                        'urun_adi': f"{code}",
                        'boy': package_length,
                        'en': package_width,
                        'yukseklik': package_height,
                        'agirlik': package_weight,
                        'mukavemet': mukavemet,
                        'donus_serbest': True,
                        'istiflenebilir': True,
                        'package_quantity': package_quantity,
                        'quantity': to_float(quantity),
                        'unit_length': unit_length,
                        'unit_width': unit_width,
                        'unit_height': unit_height,
                        'unit_weight': unit_weight
                    }
                    urun_verileri.append(urun_listesi_item)
        
        # Eski format kontrolü (geriye dönük uyumluluk)
        elif isinstance(yuklenen_veri, list):
            urun_verileri = yuklenen_veri
        else:
            return JsonResponse({'success': False, 'error': 'Geçersiz JSON formatı. Desteklenen format: {"details": [...]}'}, status=400)

        # Verileri doğrula
        if not isinstance(urun_verileri, list) or len(urun_verileri) == 0:
            return JsonResponse({'success': False, 'error': 'Geçersiz JSON formatı. Ürün listesi boş veya hatalı.'}, status=400)
        
        # Gerekli alanları kontrol et
        required_fields = ['urun_kodu', 'urun_adi', 'boy', 'en', 'yukseklik', 'agirlik']
        for urun in urun_verileri:
            for field in required_fields:
                if field not in urun:
                    return JsonResponse({'success': False, 'error': f'Eksik alan: {field}'}, status=400)
        
        # Verileri session'a kaydet
        request.session['urun_verileri'] = urun_verileri
        
        # Başarılı sonuç dön
        return JsonResponse({
            'success': True, 
            'message': f'Toplam {len(urun_verileri)} ürün yüklendi.',
            'next_url': reverse('palet_app:urun_listesi')
        })
        
    except json.JSONDecodeError:
        # Geçici dosyayı sil
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return JsonResponse({'success': False, 'error': 'Geçersiz JSON formatı.'}, status=400)
    except Exception as e:
        # Geçici dosyayı sil
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return JsonResponse({'success': False, 'error': f'Hata: {str(e)}'}, status=400)

# Palet seçim sayfası - KALDIRILDI (Container bilgisi JSON'dan alınıyor)

# Ürün listesi sayfası
def urun_listesi(request):
    """Yüklenen ürünleri listeler"""
    # Verilerin session'da olup olmadığını kontrol et
    if 'urun_verileri' not in request.session:
        return redirect('palet_app:home')
    
    urun_verileri = request.session.get('urun_verileri', [])
    container_info = request.session.get('container_info', {})
    
    # Ürünleri grupla (aynı ürün koduna sahip olanlar)
    urun_gruplari = {}
    for urun in urun_verileri:
        kod = urun['urun_kodu']
        if kod not in urun_gruplari:
            urun_gruplari[kod] = {
                'urun_kodu': kod,
                'urun_adi': urun['urun_adi'],
                'boy': urun['boy'],
                'en': urun['en'],
                'yukseklik': urun['yukseklik'],
                'agirlik': urun['agirlik'],
                'mukavemet': urun.get('mukavemet', 'N/A'),
                'adet': 0,
                'toplam_agirlik': 0,
                'toplam_hacim': 0
            }
        urun_gruplari[kod]['adet'] += 1
        urun_gruplari[kod]['toplam_agirlik'] += urun['agirlik']
        urun_gruplari[kod]['toplam_hacim'] += (urun['boy'] * urun['en'] * urun['yukseklik'])
    
    # Listeye çevir ve sırala
    urun_listesi = sorted(urun_gruplari.values(), key=lambda x: x['urun_kodu'])
    
    context = {
        'urun_listesi': urun_listesi,
        'toplam_urun_cesidi': len(urun_listesi),
        'toplam_paket': len(urun_verileri),
        'container_info': container_info
    }
    
    return render(request, 'palet_app/urun_listesi.html', context)

# Arka planda çalışacak optimizasyon işlemi
def run_optimization(urun_verileri, container_info, optimization_id, algoritma='greedy'):
    """
    Arka planda çalışacak optimizasyon işlemi. Bu fonksiyon bir thread içinde çalışır.
    
    Args:
        urun_verileri: Ürün verileri listesi
        container_info: Container bilgileri dict (length, width, height, weight)
        optimization_id: Optimizasyon ID'si
        algoritma: 'greedy' veya 'genetic'
    """
    try:
        # Optimizasyon objesi
        optimization = Optimization.objects.get(id=optimization_id)
        
        # Adım 1: Ürünleri veritabanına kaydet
        optimization.islem_adimi_ekle("Ürün verileri yükleniyor...")
        
        urunler = []
        for veri in urun_verileri:
            urun = Urun(
                urun_kodu=veri["urun_kodu"],
                urun_adi=veri["urun_adi"],
                boy=veri["boy"],
                en=veri["en"],
                yukseklik=veri["yukseklik"],
                agirlik=veri["agirlik"],
                mukavemet=veri.get("mukavemet", 100000),
                donus_serbest=veri.get("donus_serbest", True),
                istiflenebilir=veri.get("istiflenebilir", True)
            )
            urun.save()
            urunler.append(urun)
        
        # Adım 2: Single palet yerleştirme
        optimization.islem_adimi_ekle("Single paletler oluşturuluyor...")
        single_paletler, yerlesmemis_urunler = single_palet_yerlestirme(urunler, container_info, optimization)
        
        
        # Adım 3: Mix palet yerleştirme
        if algoritma == 'genetic':
            from .algorithms.ga_core import run_ga
            from .algorithms.ga_utils import PaletConfig, basit_palet_paketleme
            
            optimization.islem_adimi_ekle("🧬 Yeni Genetik Algoritma Motoru ile mix paletler oluşturuluyor...")
            optimization.islem_adimi_ekle("Bu işlem ürün sayısına göre 1-3 dakika sürebilir...")
            
            # Palet konfigürasyonu oluştur
            palet_cfg = PaletConfig(
                length=container_info['length'],
                width=container_info['width'],
                height=container_info['height'],
                max_weight=container_info['weight']
            )
            
            # Ürün sayısına göre dinamik parametreler
            urun_sayisi = len(yerlesmemis_urunler)
            pop_size = min(30 + (urun_sayisi // 150), 100)
            generations = min(50 + (urun_sayisi // 40), 300)
            
            optimization.islem_adimi_ekle(f"Parametreler: Pop={pop_size}, Nesil={generations}, Ürün={urun_sayisi}")
            
            # GA motorunu çalıştır
            best_chromosome, history = run_ga(
                urunler=yerlesmemis_urunler,
                palet_cfg=palet_cfg,
                population_size=pop_size,
                generations=generations,
                mutation_rate=0.15,
                tournament_k=3,
                elitism=2
            )
            
            if best_chromosome:
                optimization.islem_adimi_ekle(
                    f"En iyi çözüm: Fitness={best_chromosome.fitness:.2f}, "
                    f"Palet={best_chromosome.palet_sayisi}, "
                    f"Doluluk={best_chromosome.ortalama_doluluk:.2%}"
                )
                
                # En iyi kromozomdan paletleri oluştur
                mix_paletler = chromosome_to_palets(
                    best_chromosome, 
                    palet_cfg, 
                    optimization, 
                    len(single_paletler) + 1
                )
                optimization.islem_adimi_ekle(f"{len(mix_paletler)} adet mix palet oluşturuldu (Genetik).")
            else:
                optimization.islem_adimi_ekle("GA çözüm üretemedi, Greedy yönteme geçiliyor...")
                mix_paletler = mix_palet_yerlestirme(yerlesmemis_urunler, container_info, optimization, len(single_paletler) + 1)
                optimization.islem_adimi_ekle(f"{len(mix_paletler)} adet mix palet oluşturuldu (Greedy).")
        else:
            optimization.islem_adimi_ekle("Mix paletler oluşturuluyor (Greedy)...")
            mix_paletler = mix_palet_yerlestirme(yerlesmemis_urunler, container_info, optimization, len(single_paletler) + 1)
            optimization.islem_adimi_ekle(f"{len(mix_paletler)} adet mix palet oluşturuldu.")
        
        # Adım 4: İstatistikleri güncelle (Görselleştirme artık on-the-fly yapılıyor)
        optimization.islem_adimi_ekle("İstatistikler hesaplanıyor...")
        
        # Tüm paletleri birleştir
        tum_paletler = list(single_paletler) + list(mix_paletler)
        
        # Palet istatistiklerini güncelle
        from .models import Palet
        paletler = Palet.objects.filter(optimization=optimization)
        single = paletler.filter(palet_turu='single').count()
        mix = paletler.filter(palet_turu='mix').count()
        optimization.single_palet = single
        optimization.mix_palet = mix
        optimization.toplam_palet = single + mix
        optimization.save()
        
        # Yerleştirilemeyen ürünleri kaydet
        son_yerlesmeyen_urunler = []
        for urun in urunler:
            yerlestirilmis = False
            for palet in tum_paletler:
                urun_konumlari = palet.json_to_dict(palet.urun_konumlari)
                if str(urun.id) in urun_konumlari:
                    yerlestirilmis = True
                    break
            
            if not yerlestirilmis:
                son_yerlesmeyen_urunler.append({
                    'id': urun.id,
                    'urun_kodu': urun.urun_kodu,
                    'urun_adi': urun.urun_adi,
                    'boy': urun.boy,
                    'en': urun.en,
                    'yukseklik': urun.yukseklik,
                    'agirlik': urun.agirlik
                })
        
        optimization.yerlesmemis_urunler = son_yerlesmeyen_urunler
        
        # Optimizasyonu tamamla
        optimization.islem_adimi_ekle("Optimizasyon tamamlandı.")
        optimization.tamamla()
        
    except Exception as e:
        # Hata durumunda
        import traceback
        error_detail = traceback.format_exc()
        print(f"HATA: {str(e)}")
        print(f"DETAY: {error_detail}")
        
        try:
            optimization = Optimization.objects.get(id=optimization_id)
            optimization.islem_adimi_ekle(f"Hata: {str(e)}")
            # Tamamen hatalı olduğunu belirt
            durum = optimization.get_islem_durumu()
            durum['current_step'] = -1  # Hata durumu
            optimization.islem_durumu = json.dumps(durum)
            optimization.save()
        except Exception as inner_e:
            print(f"Inner exception: {str(inner_e)}")

# İşleniyor sayfası
def processing(request):
    """İşlem simülasyonu sayfası"""
    # Verilerin session'da olup olmadığını kontrol et
    if 'urun_verileri' not in request.session:
        return redirect('palet_app:home')
    
    # Container bilgisi var mı kontrol et
    container_info = request.session.get('container_info')
    if not container_info:
        return redirect('palet_app:home')
    
    return render(request, 'palet_app/processing.html')

# Yerleştirme başlatma API'si
def start_placement(request):
    """Yerleştirme işlemini başlatır"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Yalnızca POST istekleri kabul edilir.'}, status=400)
    
    # Gerekli verileri kontrol et
    if 'urun_verileri' not in request.session:
        return JsonResponse({'success': False, 'error': 'Ürün verileri bulunamadı.'}, status=400)
    
    # Container bilgisini al (JSON'dan gelen)
    container_info = request.session.get('container_info')
    if not container_info:
        return JsonResponse({'success': False, 'error': 'Container bilgisi bulunamadı.'}, status=400)
    
    # Algoritma seçimini al (POST'tan)
    import json as json_module
    try:
        body = json_module.loads(request.body)
        algoritma = body.get('algoritma', 'greedy')
    except:
        algoritma = 'greedy'
    
    # Container bilgilerini al
    container_length = container_info.get('length', 120)
    container_width = container_info.get('width', 100)
    container_height = container_info.get('height', 180)
    container_weight = container_info.get('weight', 1250)
    
    with transaction.atomic():
        # Optimizasyon objesi oluştur (dinamik container bilgileriyle)
        optimization = Optimization.objects.create(
            palet_tipi=None,  # Artık sabit palet tipi kullanmıyoruz
            container_length=container_length,
            container_width=container_width,
            container_height=container_height,
            container_weight=container_weight,
            algoritma=algoritma,  # Algoritmayı kaydet
            islem_durumu=json.dumps({
                "current_step": 0,
                "total_steps": 5,
                "messages": []
            })
        )
        
        # Optimizasyon ID'sini session'a kaydet
        request.session['optimization_id'] = optimization.id
        request.session['algoritma'] = algoritma  # Algoritma bilgisini kaydet
        
        # Container bilgilerini dict olarak hazırla
        container_dict = {
            'length': container_length,
            'width': container_width,
            'height': container_height,
            'weight': container_weight
        }
        
        # İşlemi background thread'de başlat
        thread = Thread(target=run_optimization, args=(request.session['urun_verileri'], container_dict, optimization.id, algoritma))
        thread.daemon = True
        thread.start()
    
    return JsonResponse({
        'success': True,
        'message': 'Optimizasyon başlatıldı.',
        'optimization_id': optimization.id,
        'status_url': reverse('palet_app:optimization_status')
    })

# Optimizasyon durumu API
def optimization_status(request):
    """Optimizasyon durumunu döndürür"""
    # Optimizasyon ID'sini al
    optimization_id = request.session.get('optimization_id')
    if not optimization_id:
        return JsonResponse({'success': False, 'error': 'Optimizasyon bulunamadı.'}, status=400)
    
    try:
        # Optimizasyon durumunu kontrol et
        optimization = Optimization.objects.get(id=optimization_id)
        durum = optimization.get_islem_durumu()
        
        # Eğer işlem tamamlandıysa, analiz sayfasına yönlendir
        if optimization.tamamlandi:
            return JsonResponse({
                'success': True,
                'completed': True,
                'next_url': reverse('palet_app:analysis')
            })
        
        return JsonResponse({
            'success': True,
            'completed': False,
            'current_step': durum.get('current_step', 0),
            'total_steps': durum.get('total_steps', 5),
            'messages': durum.get('messages', [])
        })
        
    except Optimization.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Optimizasyon bulunamadı.'}, status=400)

# Analiz sayfası
def analysis(request):
    """Optimizasyon sonuçlarını gösterir"""
    # Optimizasyon ID'sini al
    optimization_id = request.session.get('optimization_id')
    if not optimization_id:
        return redirect('palet_app:home')
    
    try:
        # Optimizasyon objesi
        optimization = get_object_or_404(Optimization, id=optimization_id)
        
        # Eğer optimizasyon henüz tamamlanmadıysa, işleniyor sayfasına yönlendir
        if not optimization.tamamlandi:
            return redirect('palet_app:processing')
        
        # Paletleri al
        paletler = Palet.objects.filter(optimization=optimization).order_by('palet_id')
        
        # Interaktif grafikleri on-the-fly oluştur
        pie_chart_html, bar_chart_html = ozet_grafikler_html(optimization)
        
        context = {
            'optimization': optimization,
            'paletler': paletler,
            'single_oran': optimization.single_palet / optimization.toplam_palet * 100 if optimization.toplam_palet > 0 else 0,
            'mix_oran': optimization.mix_palet / optimization.toplam_palet * 100 if optimization.toplam_palet > 0 else 0,
            'yerlesmemis_urunler': optimization.yerlesmemis_urunler,
            'pie_chart_html': pie_chart_html,
            'bar_chart_html': bar_chart_html
        }
        
        return render(request, 'palet_app/analysis.html', context)
        
    except Optimization.DoesNotExist:
        return redirect('palet_app:home')

# Palet detay sayfası
def palet_detail(request, palet_id):
    """Tek bir palet detayını gösterir"""
    # Optimizasyon ID'sini al
    optimization_id = request.session.get('optimization_id')
    if not optimization_id:
        return redirect('palet_app:home')
    
    try:
        # Optimizasyon objesi
        optimization = get_object_or_404(Optimization, id=optimization_id)
        
        # Eğer optimizasyon henüz tamamlanmadıysa, işleniyor sayfasına yönlendir
        if not optimization.tamamlandi:
            return redirect('palet_app:processing')
        
        # Paleti al
        palet = get_object_or_404(Palet, optimization=optimization, palet_id=palet_id)
        
        # Tüm paletleri al (önceki/sonraki navigasyonu için)
        tum_paletler = Palet.objects.filter(optimization=optimization).order_by('palet_id')
        palet_ids = list(tum_paletler.values_list('palet_id', flat=True))
        
        # Önceki/sonraki palet ID'lerini belirle
        current_index = palet_ids.index(palet_id)
        prev_id = palet_ids[current_index - 1] if current_index > 0 else None
        next_id = palet_ids[current_index + 1] if current_index < len(palet_ids) - 1 else None
        
        # Bu palette hangi ürünlerin olduğunu bul
        urun_konumlari = palet.json_to_dict(palet.urun_konumlari)
        urun_boyutlari = palet.json_to_dict(palet.urun_boyutlari)
        
        urun_ids = [int(id) for id in urun_konumlari.keys()]
        urunler = list(Urun.objects.filter(id__in=urun_ids))
        
        # Interaktif 3D görselleştirme HTML'i oluştur
        palet_3d_html = palet_gorsellestir_html(palet, urunler)
        
        # Ürün kodlarına göre renk sözlüğü oluştur (görselleştirme ile aynı mantık)
        urun_renkleri = {}
        for urun in urunler:
            if urun.urun_kodu not in urun_renkleri:
                urun_renkleri[urun.urun_kodu] = renk_uret(urun.urun_kodu)
        
        # Ürün detaylarını hazırla
        urun_detaylari = []
        for urun in urunler:
            konum = urun_konumlari.get(str(urun.id), [0, 0, 0])
            boyut = urun_boyutlari.get(str(urun.id), [0, 0, 0])
            
            # Liste ise tuple'a dönüştür
            if isinstance(konum, list):
                konum = tuple(konum)
            if isinstance(boyut, list):
                boyut = tuple(boyut)
            
            # Renk bilgisini al (RGB 0-1 aralığında)
            renk_rgb = urun_renkleri.get(urun.urun_kodu, (0.5, 0.5, 0.5))
            # RGB'yi 0-255 aralığına çevir
            renk_rgb_255 = (int(renk_rgb[0] * 255), int(renk_rgb[1] * 255), int(renk_rgb[2] * 255))
                
            urun_detaylari.append({
                'urun': urun,
                'konum': konum,
                'boyut': boyut,
                'renk_rgb': renk_rgb_255
            })
        
        context = {
            'palet': palet,
            'urun_detaylari': urun_detaylari,
            'prev_id': prev_id,
            'next_id': next_id,
            'total_palets': len(palet_ids),
            'palet_3d_html': palet_3d_html
        }
        
        return render(request, 'palet_app/palet_detail.html', context)
        
    except Exception as e:
        return HttpResponseBadRequest(f"Hata: {str(e)}")



# Ana sayfa
def home_view(request):
    return render(request, 'palet_app/home.html')  # Ana sayfa şablonunu render et
