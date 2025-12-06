# Akıllı Palet Yerleştirme Sistemi - Web Arayüzü

Bu proje, Python ile Django framework'ü kullanarak geliştirilmiş, 3D bin packing algoritması ile çalışan bir palet yerleştirme uygulamasıdır.

## Özellikler

- Farklı tiplerde palet desteği (Avrupa, ISO Standart, Asya, ABD Paletleri)
- Ürünlerin özelliklerine göre (boyut, ağırlık, istifleme) otomatik yerleştirme
- Tek tipte ürün paletleri (Single) ve karışık ürün paletleri (Mix) oluşturma
- 3D görselleştirme ve istatistikler
- Web tabanlı kullanıcı arayüzü
- Arka planda çalışan optimizasyon işlemi

## Kurulum

```bash
# Gerekli bağımlılıkları yükle
pip install -r requirements.txt

# Veritabanını oluştur
python manage.py migrate

#Enviroment Aktif et python surumu 3.11.9
source env/Scripts/activate

# Sunucuyu başlat
python manage.py runserver
```

## Kullanım

1. Ana sayfadan JSON formatında ürün verisini yükleyin
2. Palet tipini seçin (Avrupa, ISO, Asya, ABD)
3. İşleniyor ekranında canlı olarak optimizasyon sürecini takip edin
4. Tamamlandığında analiz sayfasında sonuçları görüntüleyin
5. Paletleri tek tek inceleyin ve 3D görselleri görüntüleyin

## Proje Yapısı

```
DjangoPaletProjesi/
├── core/                   # Django projesinin çekirdek ayarları
├── palet_app/              # Ana uygulama kodu
│   ├── algorithms/         # Palet yerleştirme algoritmaları
│   ├── models/             # Veritabanı modelleri
│   ├── templates/          # HTML şablonları
│   └── views.py            # Görünüm fonksiyonları               
├── templates/              # Temel HTML şablonları
├── manage.py               # Django yönetim betiği
└── requirements.txt        # Bağımlılıklar
```

## Örnek Veri

Proje, test için `urun_verisi_tam.json` dosyasını içerir. Bu dosyayı kullanarak sistemin nasıl çalıştığını test edebilirsiniz.

