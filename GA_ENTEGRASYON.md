# GA Engine Entegrasyon Dokümantasyonu

## 🎯 Yapılan Değişiklikler

### 1. Yeni Modüller Eklendi

#### `palet_app/algorithms/ga_utils.py`
- **Kaynak**: `ga_engine/utils.py`
- **İçerik**: 
  - `PaletConfig`: Palet parametreleri sınıfı
  - `simulate_single_pallet()`: Gelişmiş single palet simülasyonu
  - `pack_shelf_based()`: Mix palet yerleştirme algoritması
  - `solve_best_layer_configuration()`: Katman optimizasyonu
  - `generate_optimized_placements()`: Koordinat üreten görselleştirme fonksiyonu
  - Fiziksel kontroller: CoG, stacking ihlali, ağırlık kontrolü
  - Yardımcı fonksiyonlar: hacim, ağırlık, cluster purity hesaplamaları

#### `palet_app/algorithms/ga_chromosome.py`
- **Kaynak**: `ga_engine/chromosome.py`
- **İçerik**: Kromozom (birey) sınıfı
  - Sıra geni (permütasyon)
  - Rotasyon geni (0/1 için X-Y dönüşü)
  - Fitness bilgileri (palet sayısı, doluluk, vb.)

#### `palet_app/algorithms/ga_fitness.py`
- **Kaynak**: `ga_engine/fitness.py`
- **İçerik**: Fitness değerlendirme motoru
  - Hacim optimizasyonu (exponential reward)
  - Palet sayısı hedef bonusu/cezası
  - Fiziksel ihlal cezaları (ağırlık, CoG, stacking)
  - Yapılandırılabilir ağırlık sistemi (`GA_WEIGHTS`)

#### `palet_app/algorithms/ga_core.py`
- **Kaynak**: `ga_engine/ga_core.py`
- **İçerik**: Genetik Algoritma Ana Motoru
  - `run_ga()`: Ana GA döngüsü
  - `tournament_selection()`: Turnuva seçimi
  - `crossover()`: Order Crossover (OX) + rotasyon karışımı
  - `mutate()`: Sıra swap + rotasyon mutasyonu
  - Elitizm desteği

### 2. Güncellenen Dosyalar

#### `palet_app/algorithms/single_palet_yerlestirme.py`
**Önceki Durum**: Maximal Empty Spaces (MES) yaklaşımı
**Yeni Durum**: GA utils entegrasyonu
- `simulate_single_pallet()` kullanarak gelişmiş optimizasyon
- Matematiksel katman konfigürasyonu (`solve_best_layer_configuration`)
- Koordinat bazlı yerleşim (`generate_optimized_placements`)
- Dinamik doluluk eşikleri (stok miktarına göre)

#### `palet_app/views.py`
**Eklenen Fonksiyon**: `chromosome_to_palets()`
- En iyi kromozomdan Django Palet nesneleri oluşturur
- Placements'ı Django modellerine dönüştürür

**Güncellenen Fonksiyon**: `run_optimization()`
```python
if algoritma == 'genetic':
    from .algorithms.ga_core import run_ga
    from .algorithms.ga_utils import PaletConfig
    
    # Palet konfigürasyonu
    palet_cfg = PaletConfig(...)
    
    # Dinamik parametreler
    pop_size = min(30 + (urun_sayisi // 150), 100)
    generations = min(50 + (urun_sayisi // 40), 300)
    
    # GA motoru çalıştır
    best_chromosome, history = run_ga(
        urunler=yerlesmemis_urunler,
        palet_cfg=palet_cfg,
        population_size=pop_size,
        generations=generations,
        ...
    )
    
    # Kromozomdan paletler oluştur
    mix_paletler = chromosome_to_palets(...)
```

## 🔧 Teknik Detaylar

### GA Parametreleri
- **Popülasyon**: 30-100 birey (ürün sayısına göre dinamik)
- **Nesil**: 50-300 nesil (ürün sayısına göre dinamik)
- **Mutasyon Oranı**: %15
- **Turnuva Boyutu**: 3 birey
- **Elitizm**: 2 birey

### Fitness Fonksiyonu Ağırlıkları
```python
GA_WEIGHTS = {
    "w_volume": 10000,              # Hacim (exponential)
    "w_cluster": 0,                 # Cluster (devre dışı)
    "w_min_pallet_bonus": 2000,     # Hedef palet bonusu
    "w_min_pallet_penalty_1": 1000, # +1 palet cezası
    "w_min_pallet_penalty_2": 5000, # +2+ palet cezası
    "w_weight_over": 1000000,       # Ağırlık aşımı (kritik)
    "w_cm_offset": 5000,            # Denge (CoG)
    "w_stack_violation": 1000000,   # Ezilme (kritik)
    "w_rot_good": 100,
    "w_rot_bad": 100,
}
```

### Single Palet Dinamik Eşikler
- **Stok > 150**: %82 doluluk kabul edilir
- **Stok > 80**: %85 doluluk kabul edilir
- **Varsayılan**: %90 doluluk gerekli
- **Ağırlık Dolu**: Hacim düşük olsa da kabul edilir

## 📊 Performans İyileştirmeleri

### Single Palet
1. **Matematik Bazlı Katman Optimizasyonu**
   - İki tip satır (Type 1 ve Type 2) kombinasyonu
   - Maksimum kutu sayısı için optimum konfigürasyon
   
2. **Koordinat Üretimi**
   - Gerçek X, Y, Z pozisyonları
   - Katman katman düzenli dizilim
   - Görselleştirme desteği

3. **Ağırlık Merkezi Kontrolü**
   - CoG hesaplaması
   - Denge kontrolleri

### Mix Palet (GA)
1. **Akıllı Rotasyon Seçimi**
   - Strip efficiency (şerit verimliliği)
   - Smart fit (akıllı sığdırma)
   
2. **Fiziksel Kontroller**
   - Ağırlık limiti
   - Stacking ihlali
   - CoG kayması
   
3. **Dinamik Parametreler**
   - Ürün sayısına göre otomatik ayarlama
   - Optimal popülasyon ve nesil sayısı

## 🚀 Kullanım

### Web Arayüzü
1. JSON dosyası yükle
2. Algoritma seç: **"Genetik Algoritma"**
3. Optimizasyon başlat
4. Sonuçları görüntüle

### Örnek Çıktı
```
Single palet oluşturuluyor: ABC123, Toplam ürün: 45
Single palet 1: 42 ürün yerleştirildi, %89.32 doluluk - KABUL

🧬 Yeni Genetik Algoritma Motoru ile mix paletler oluşturuluyor...
Parametreler: Pop=35, Nesil=75, Ürün=128

Nesil   0: En İyi=125432.15 Ort=98234.50 Palet=3 Doluluk=87.45%
Nesil  10: En İyi=142567.89 Ort=128456.23 Palet=3 Doluluk=91.23%
...
Nesil  74: En İyi=156789.34 Ort=145678.90 Palet=2 Doluluk=94.56%

En iyi çözüm: Fitness=156789.34, Palet=2, Doluluk=94.56%
5 adet mix palet oluşturuldu (Genetik).
```

## 🧪 Test

Test scripti hazır:
```bash
python test_ga_integration.py
```

## 📁 Dosya Yapısı

```
palet_app/algorithms/
├── ga_utils.py           # Yardımcı fonksiyonlar
├── ga_chromosome.py      # Kromozom sınıfı
├── ga_fitness.py         # Fitness değerlendirme
├── ga_core.py           # GA ana motoru
├── single_palet_yerlestirme.py  # Güncellenmiş
├── mix_palet_yerlestirme.py     # Mevcut (greedy için)
├── visualize.py         # Görselleştirme
└── genetic_algorithm.py # Eski (artık kullanılmıyor)
```

## ⚠️ Önemli Notlar

1. **ga_engine** klasörü hala mevcut (bağımsız testler için)
2. Eski `genetic_algorithm.py` dosyası korundu (geriye dönük uyumluluk)
3. Greedy algoritma hala çalışıyor (algoritma='greedy')
4. Tüm Django model entegrasyonları tamamlandı
5. Görselleştirme fonksiyonları uyumlu

## 🎉 Sonuç

✅ GA engine başarıyla ana projeye entegre edildi  
✅ Single palet optimizasyonu geliştirildi  
✅ Mix palet için güçlü GA motoru eklendi  
✅ Tüm testler geçti  
✅ Web arayüzü hazır  

Sistem artık ürün sayısına göre otomatik olarak optimize parametrelerle çalışıyor!
