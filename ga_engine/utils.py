import math
from collections import Counter, defaultdict


class PaletConfig:
    """
    Palet parametreleri (test için basit yapı).
    Gerçek projede container_info'dan beslenebilir.
    """

    def __init__(self, length=120.0, width=100.0, height=180.0, max_weight=1250.0):
        self.length = float(length)
        self.width = float(width)
        self.height = float(height)
        self.max_weight = float(max_weight)

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height


def _get_attr(obj, name, default=None):
    """Hem dict hem obje için güvenli attribute okuma."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def urun_hacmi(urun) -> float:
    boy = _get_attr(urun, "boy", 0.0)
    en = _get_attr(urun, "en", 0.0)
    yuk = _get_attr(urun, "yukseklik", 0.0)
    return float(boy) * float(en) * float(yuk)


def urun_agirlik(urun) -> float:
    return float(_get_attr(urun, "agirlik", 0.0))


def urun_mukavemet(urun) -> float:
    return float(_get_attr(urun, "mukavemet", 0.0))


def urun_kodu(urun):
    kod = _get_attr(urun, "urun_kodu", None)
    if kod is not None:
        return kod
    # fallback: id veya repr
    return _get_attr(urun, "id", repr(urun))


def donus_serbest_mi(urun) -> bool:
    return bool(_get_attr(urun, "donus_serbest", True))


def possible_orientations_for(urun):
    """
    Ürün için olası rotasyon boyutları.
    Gerçek projede Urun.possible_orientations() varsa onu kullanabiliriz.
    Burada basit 6 permütasyon mantığı kullanılıyor.
    """
    boy = float(_get_attr(urun, "boy", 0.0))
    en = float(_get_attr(urun, "en", 0.0))
    yuk = float(_get_attr(urun, "yukseklik", 0.0))

    # Eğer modelde possible_orientations fonksiyonu varsa onu kullan
    fn = getattr(urun, "possible_orientations", None)
    if callable(fn):
        return list(fn())

    if not donus_serbest_mi(urun):
        return [(boy, en, yuk)]

    return [
        (boy, en, yuk),
        (boy, yuk, en),
        (en, boy, yuk),
        (en, yuk, boy),
        (yuk, boy, en),
        (yuk, en, boy),
    ]


def theoretical_best_rot_index(urun, palet_cfg: PaletConfig) -> int:
    """
    'İyi rotasyon' için basit bir kriter:
    - Palet yüksekliğine sığan,
    - ve en düşük yükseklik veren rotasyonu seçiyoruz.
    """
    best_idx = 0
    best_height = math.inf
    orientations = possible_orientations_for(urun)

    for i, (b, e, h) in enumerate(orientations):
        if h <= palet_cfg.height and h < best_height:
            best_height = h
            best_idx = i

    return best_idx


def min_palet_sayisi_tez(urunler, palet_cfg: PaletConfig) -> int:
    """
    Hacme göre teorik minimum palet sayısı.
    """
    toplam_hacim = sum(urun_hacmi(u) for u in urunler)
    if palet_cfg.volume <= 0:
        return 1
    return max(1, math.ceil(toplam_hacim / palet_cfg.volume))


def cluster_purity(palet_urunleri) -> float:
    """
    Bir paletteki ürün tiplerinin 'aynı ürün oranı' (purity).
    Adet bazlı hesaplıyoruz.
    """
    if not palet_urunleri:
        return 0.0
    counts = Counter(urun_kodu(u) for u in palet_urunleri)
    en_cok = max(counts.values())
    toplam = sum(counts.values())
    return en_cok / toplam


def basit_palet_paketleme(chromosome, palet_cfg: PaletConfig):
    """
    Çok basitleştirilmiş bir paketleme:
    - Paletleri sadece hacim + ağırlık sınırına göre doldurur.
    - 3D koordinat hesabı yok, amaç GA tasarımını test etmek.
    Dönen:
        pallets: [
          {
            "urunler": [urun, ...],
            "volume": float,
            "weight": float,
          }, ...
        ]
    """
    urunler = chromosome.urunler
    pallets = []

    current_items = []
    current_volume = 0.0
    current_weight = 0.0

    for idx in chromosome.sira_gen:
        urun = urunler[idx]
        v = urun_hacmi(urun)
        w = urun_agirlik(urun)

        # Yeni ürün mevcut palete sığmazsa yeni palet aç
        if (
            current_items
            and (
                current_volume + v > palet_cfg.volume
                or current_weight + w > palet_cfg.max_weight
            )
        ):
            pallets.append(
                {
                    "urunler": current_items,
                    "volume": current_volume,
                    "weight": current_weight,
                }
            )
            current_items = []
            current_volume = 0.0
            current_weight = 0.0

        current_items.append(urun)
        current_volume += v
        current_weight += w

    # son paleti ekle
    if current_items:
        pallets.append(
            {
                "urunler": current_items,
                "volume": current_volume,
                "weight": current_weight,
            }
        )

    # Doluluk oranlarını ekle
    for p in pallets:
        p["fill_ratio"] = p["volume"] / palet_cfg.volume if palet_cfg.volume > 0 else 0.0

    return pallets


def agirlik_merkezi_kaymasi_dummy(palet) -> float:
    """
    Şu an 3D koordinat olmadığından ağırlık merkezi hesabı yapmıyoruz.
    Burası gelecekte geliştirilebilir; şimdilik 0 döndürür.
    """
    return 0.0


def stacking_ihlali_sayisi_dummy(palet) -> int:
    """
    Gerçek stacking (ağır ürün alta) hesabı için 3D bilgi gerekir.
    Şimdilik 0 döner; yapı hazır tutuluyor.
    """
    return 0
