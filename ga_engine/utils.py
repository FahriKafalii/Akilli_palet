import math
from collections import Counter


# -------------------------------------------------------------------
# 1) PALET PARAMETRELERİ
# -------------------------------------------------------------------

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


# -------------------------------------------------------------------
# 2) GÜVENLİ ATTRIBUTE OKUMA
# -------------------------------------------------------------------

def _get_attr(obj, name, default=None):
    """Hem dict hem obje için güvenli attribute okuma."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


# -------------------------------------------------------------------
# 3) ÜRÜN TEMEL ÖZELLİKLERİ
# -------------------------------------------------------------------

def urun_hacmi(urun) -> float:
    boy = _get_attr(urun, "boy", 0.0)
    en = _get_attr(urun, "en", 0.0)
    yuk = _get_attr(urun, "yukseklik", 0.0)
    return float(boy) * float(en) * float(yuk)


def urun_agirlik(urun) -> float:
    return float(_get_attr(urun, "agirlik", 0.0))


def urun_kodu(urun):
    kod = _get_attr(urun, "urun_kodu", None)
    if kod is not None:
        return kod
    return _get_attr(urun, "id", repr(urun))


def donus_serbest_mi(urun) -> bool:
    return bool(_get_attr(urun, "donus_serbest", True))


# -------------------------------------------------------------------
# 4) ROTASYON OLUŞTURMA
# -------------------------------------------------------------------

def possible_orientations_for(urun):
    """
    Ürün için olası 6 eksenli rotasyon.
    """
    boy = float(_get_attr(urun, "boy", 0.0))
    en = float(_get_attr(urun, "en", 0.0))
    yuk = float(_get_attr(urun, "yukseklik", 0.0))

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
    'En iyi rotasyon' = palete sığan + en düşük yükseklik veren rotasyon.
    """
    best_idx = 0
    best_height = math.inf
    orientations = possible_orientations_for(urun)

    for i, (b, e, h) in enumerate(orientations):
        if h <= palet_cfg.height and h < best_height:
            best_height = h
            best_idx = i

    return best_idx


# -------------------------------------------------------------------
# 5) HESAPLAMALAR: HACİM – PUAN – CLUSTER
# -------------------------------------------------------------------

def min_palet_sayisi_tez(urunler, palet_cfg: PaletConfig) -> int:
    """
    Hacme göre teorik minimum palet sayısı.
    """
    toplam_hacim = sum(urun_hacmi(u) for u in urunler)
    return max(1, math.ceil(toplam_hacim / palet_cfg.volume))


def cluster_purity(palet_urunleri) -> float:
    """
    Bir paletteki ürün tiplerinin 'aynı ürün oranı'.
    """
    if not palet_urunleri:
        return 0.0

    counts = Counter(urun_kodu(u) for u in palet_urunleri)
    en_cok = max(counts.values())
    toplam = sum(counts.values())
    return en_cok / toplam


# -------------------------------------------------------------------
# 6) BASİT PACKING (GA TEST AMAÇLI)
# -------------------------------------------------------------------

def basit_palet_paketleme(chromosome, palet_cfg: PaletConfig):
    """
    Hacim + ağırlık bazlı YALIN paketleme.
    GA motorunu test etmek için yeterli.
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

        # mevcut palet dolarsa yenisini aç
        if (
            current_items
            and (
                current_volume + v > palet_cfg.volume
                or current_weight + w > palet_cfg.max_weight
            )
        ):
            pallets.append({
                "urunler": current_items,
                "volume": current_volume,
                "weight": current_weight,
            })

            current_items = []
            current_volume = 0.0
            current_weight = 0.0

        current_items.append(urun)
        current_volume += v
        current_weight += w

    # son palet
    if current_items:
        pallets.append({
            "urunler": current_items,
            "volume": current_volume,
            "weight": current_weight,
        })

    # Doluluk hesapla
    for p in pallets:
        p["fill_ratio"] = p["volume"] / palet_cfg.volume

    return pallets


# -------------------------------------------------------------------
# 7) DUMMY CEZA HESAPLARI (Illerde 3D ile değişecek)
# -------------------------------------------------------------------

def agirlik_merkezi_kaymasi_dummy(palet) -> float:
    """3D olmadığı için şu an 0 döner."""
    return 0.0


def stacking_ihlali_sayisi_dummy(palet) -> int:
    """Stacking (ağır ürün üste) 3D yerleşim yok → 0 döner."""
    return 0


# -------------------------------------------------------------------
# 8) JSON → ÜRÜN DÖNÜŞTÜRÜCÜ (ŞİRKET VERİSİ İÇİN)
# -------------------------------------------------------------------

def convert_json_packages_to_products(json_data, UrunClass):
    """
    JSON içindeki paket (kutu) bilgilerini GA'nın ürün formatına dönüştürür.
    quantity artık kullanılmıyor!
    GA sadece package_quantity kadar kutu yerleştirecek.
    """
    urunler = []

    for item in json_data.get("details", []):
        p = item["product"]

        adet = int(item.get("package_quantity", 1))

        for _ in range(adet):
            urun = UrunClass(
                urun_kodu=str(p["code"]),
                boy=float(p["package_length"]),
                en=float(p["package_width"]),
                yukseklik=float(p["package_height"]),
                agirlik=float(p["package_weight"]),
                mukavemet=1000.0,
                donus_serbest=True,
                istiflenebilir=True,
            )
            urunler.append(urun)

    return urunler

