import math
from collections import Counter

# -------------------------------------------------------------------
# 1) PALET PARAMETRELERİ
# -------------------------------------------------------------------

class PaletConfig:
    """
    Palet parametreleri.
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
# 2) TEMEL YARDIMCILAR
# -------------------------------------------------------------------

def _get_attr(obj, name, default=None):
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

def urun_kodu(urun):
    kod = _get_attr(urun, "urun_kodu", None)
    if kod is not None:
        return kod
    return _get_attr(urun, "id", repr(urun))

def donus_serbest_mi(urun) -> bool:
    return bool(_get_attr(urun, "donus_serbest", True))

def possible_orientations_for(urun):
    """
    KURAL: Ürün yan yatamaz (Z sabit). Sadece X-Y dönebilir.
    """
    boy = float(_get_attr(urun, "boy", 0.0))
    en = float(_get_attr(urun, "en", 0.0))
    yuk = float(_get_attr(urun, "yukseklik", 0.0))

    if not donus_serbest_mi(urun):
        return [(boy, en, yuk)]

    return [
        (boy, en, yuk),  # 0: Orijinal
        (en, boy, yuk),  # 1: 90 derece
    ]

def theoretical_best_rot_index(urun, palet_cfg: PaletConfig) -> int:
    return 0


# -------------------------------------------------------------------
# 3) FİZİKSEL YERLEŞTİRME MOTORU (SHELF-BASED + SMART FIT)
# -------------------------------------------------------------------

def pack_shelf_based(urunler, rot_gen, palet_cfg: PaletConfig):
    """
    Raf mantığıyla (X -> Y -> Z) fiziksel yerleşim yapar.
    GÜNCELLEME: 'Smart Fit' - Eğer kutu mevcut boşluğa sığmıyorsa
    döndürüp sığdırmayı dener.
    """
    pallets = []
    
    current_items = []     
    current_weight = 0.0
    
    x, y, z = 0.0, 0.0, 0.0
    current_layer_height = 0.0
    shelf_width = 0.0

    L, W, H = palet_cfg.length, palet_cfg.width, palet_cfg.height
    
    for idx, urun in enumerate(urunler):
        # 1. Gen'den gelen varsayılan rotasyonu al
        rot_idx = 0
        if rot_gen and idx < len(rot_gen):
            rot_idx = rot_gen[idx]
        
        dims_list = possible_orientations_for(urun)
        if rot_idx >= len(dims_list): rot_idx = 0
        
        # Varsayılan boyutlar
        u_len, u_wid, u_hgt = dims_list[rot_idx]
        u_wgt = urun_agirlik(urun)

        # ---------------------------------------------------------
        # AKILLI ROTASYON KONTROLÜ (Smart Fit)
        # ---------------------------------------------------------
        # Eğer mevcut rafa (X ekseni) sığmıyorsa ama döndürünce sığıyorsa, döndür!
        
        remaining_x = L - x
        # Sığmıyorsa VE Alternatif rotasyon varsa
        if (u_len > remaining_x) and (len(dims_list) > 1):
            # Diğer rotasyonu dene (boy ve en yer değiştirir)
            alt_len, alt_wid, alt_hgt = dims_list[1 - rot_idx] # 0 ise 1, 1 ise 0
            
            if alt_len <= remaining_x:
                # Başarılı! Döndürülmüş hali kullan
                u_len, u_wid, u_hgt = alt_len, alt_wid, alt_hgt
        # ---------------------------------------------------------

        # 2. Palet Ağırlık Kontrolü
        if current_weight + u_wgt > palet_cfg.max_weight:
            pallets.append(finalize_pallet(current_items, current_weight, palet_cfg))
            current_items = []
            current_weight = 0.0
            x, y, z = 0.0, 0.0, 0.0
            current_layer_height = 0.0
            shelf_width = 0.0

        # 3. X Kontrol (Raf boyu)
        if x + u_len > L:
            # Sığmadı, mecburen yeni rafa geç
            x = 0.0
            y += shelf_width
            shelf_width = 0.0 

        # 4. Y Kontrol (Katman eni)
        if y + u_wid > W:
            # Sığmadı, mecburen üst kata geç
            x = 0.0
            y = 0.0
            z += current_layer_height
            current_layer_height = 0.0
            shelf_width = 0.0

        # 5. Z Kontrol (Palet yüksekliği)
        if z + u_hgt > H:
            # Sığmadı, paleti kapat
            pallets.append(finalize_pallet(current_items, current_weight, palet_cfg))
            current_items = []
            current_weight = 0.0
            x, y, z = 0.0, 0.0, 0.0
            current_layer_height = 0.0
            shelf_width = 0.0
        
        # 6. Yerleştir
        placement_info = {
            "urun": urun,
            "x": x, "y": y, "z": z,
            "L": u_len, "W": u_wid, "H": u_hgt,
            "weight": u_wgt
        }
        current_items.append(placement_info)
        
        current_weight += u_wgt
        x += u_len
        
        if u_wid > shelf_width: shelf_width = u_wid
        if u_hgt > current_layer_height: current_layer_height = u_hgt

    if current_items:
        pallets.append(finalize_pallet(current_items, current_weight, palet_cfg))

    return pallets

def finalize_pallet(items, total_weight, palet_cfg):
    total_vol = sum(i["L"] * i["W"] * i["H"] for i in items)
    fill_ratio = total_vol / palet_cfg.volume
    cog_x, cog_y = calculate_cog(items, total_weight)
    
    raw_products = [i["urun"] for i in items]
    
    return {
        "urunler": raw_products,
        "placements": items, 
        "volume": total_vol,
        "weight": total_weight,
        "fill_ratio": fill_ratio,
        "cog_x": cog_x,
        "cog_y": cog_y
    }

def calculate_cog(items, total_weight):
    if total_weight == 0: return 0, 0
    mx, my = 0, 0
    for item in items:
        cx = item["x"] + (item["L"] / 2)
        cy = item["y"] + (item["W"] / 2)
        mx += cx * item["weight"]
        my += cy * item["weight"]
    return mx / total_weight, my / total_weight


# -------------------------------------------------------------------
# 4) ANALİZ VE CEZA FONKSİYONLARI (DİNAMİK)
# -------------------------------------------------------------------

def check_overlap(r1, r2):
    return (max(0, min(r1["x"]+r1["L"], r2["x"]+r2["L"]) - max(r1["x"], r2["x"])) * max(0, min(r1["y"]+r1["W"], r2["y"]+r2["W"]) - max(r1["y"], r2["y"]))) > 0

def agirlik_merkezi_kaymasi_dummy(palet, palet_cfg: PaletConfig) -> float:
    """
    Palet merkezinden ne kadar saptığını hesaplar.
    DİNAMİK: Palet boyutunu config'den alır.
    """
    target_x = palet_cfg.length / 2.0
    target_y = palet_cfg.width / 2.0
    
    cog_x = palet.get("cog_x", target_x)
    cog_y = palet.get("cog_y", target_y)
    
    dx = abs(cog_x - target_x)
    dy = abs(cog_y - target_y)
    
    return math.sqrt(dx**2 + dy**2)

def stacking_ihlali_sayisi_dummy(palet) -> int:
    placements = palet.get("placements", [])
    if not placements: return 0
    violations = 0
    sorted_items = sorted(placements, key=lambda k: k["z"])
    
    for i in range(len(sorted_items)):
        upper = sorted_items[i]
        for j in range(i):
            lower = sorted_items[j]
            if abs((lower["z"] + lower["H"]) - upper["z"]) < 1.0:
                if check_overlap(upper, lower):
                    if upper["weight"] > lower["weight"] * 1.5:
                        violations += 1
    return violations

def basit_palet_paketleme(chromosome, palet_cfg: PaletConfig):
    return pack_shelf_based(chromosome.urunler, chromosome.rot_gen, palet_cfg)


# -------------------------------------------------------------------
# 5) SINGLE PALET SİMÜLASYONU
# -------------------------------------------------------------------

def simulate_single_pallet(urun_listesi, palet_cfg: PaletConfig):
    if not urun_listesi:
        return {"can_be_single": False, "used": [], "remaining": [], "fill_ratio": 0.0}

    # Senaryo A: Hepsi Düz
    rot_gen_0 = [0] * len(urun_listesi)
    pallets_0 = pack_shelf_based(urun_listesi, rot_gen_0, palet_cfg)
    p0 = pallets_0[0] if pallets_0 else None
    
    # Senaryo B: Hepsi Dönük
    rot_gen_1 = [1] * len(urun_listesi)
    pallets_1 = pack_shelf_based(urun_listesi, rot_gen_1, palet_cfg)
    p1 = pallets_1[0] if pallets_1 else None
    
    best_p = p0
    used_items = p0["urunler"] if p0 else []
    
    if p1 and len(p1["urunler"]) > len(used_items):
        best_p = p1
        used_items = p1["urunler"]

    if not best_p:
        return {"can_be_single": False, "used": [], "remaining": urun_listesi, "fill_ratio": 0.0}

    used_count = len(used_items)
    used = urun_listesi[:used_count]
    remaining = urun_listesi[used_count:]
    fill_ratio = best_p["fill_ratio"]
    
    # DİNAMİK CoG Hesabı
    cog_off = agirlik_merkezi_kaymasi_dummy(best_p, palet_cfg)
    
    return {
        "can_be_single": fill_ratio >= 0.90,
        "used": used,
        "remaining": remaining,
        "fill_ratio": fill_ratio,
        "cog_offset": cog_off,
        "placements": best_p["placements"]
    }


# -------------------------------------------------------------------
# 6) DİĞERLERİ
# -------------------------------------------------------------------

def min_palet_sayisi_tez(urunler, palet_cfg: PaletConfig) -> int:
    toplam_hacim = sum(urun_hacmi(u) for u in urunler)
    if palet_cfg.volume <= 0: return 1
    return max(1, math.ceil(toplam_hacim / palet_cfg.volume))

def cluster_purity(palet_urunleri) -> float:
    if not palet_urunleri: return 0.0
    counts = Counter(urun_kodu(u) for u in palet_urunleri)
    return max(counts.values()) / sum(counts.values())

def convert_json_packages_to_products(json_data, UrunClass):
    urunler = []
    
    # JSON içindeki "details" listesini dönüyoruz
    for item in json_data.get("details", []):
        p = item["product"]
        
        # package_quantity değerini al (Varsa paket sayısı, yoksa None)
        pkg_qty = item.get("package_quantity")
        
        # --- SENARYO A: KOLİ MANTIK (package_quantity Doluysa) ---
        # Örn: package_quantity = 25 ise -> 25 tane Koli oluştur.
        if pkg_qty is not None and int(pkg_qty) > 0:
            adet = int(pkg_qty)  # Düzeltme: Burada yazan sayı kadar koli var.
            
            # Boyutlar: PACKAGE (Koli) boyutlarını alıyoruz
            # Eğer JSON'da koli boyutları yoksa (0 gelirse), unit boyutlarına bakmayalım,
            # lojistikte koli boyutu kritik. 
            boy = float(p.get("package_length") or 0)
            en  = float(p.get("package_width") or 0)
            yuk = float(p.get("package_height") or 0)
            agr = float(p.get("package_weight") or 0)
            
            # (İsteğe bağlı log) 
            # print(f"Koli Modu: {p['code']} ürününden {adet} adet koli eklendi.")

        # --- SENARYO B: TEKİL ÜRÜN MANTIK (package_quantity Null ise) ---
        # Örn: quantity = 160 ise -> 160 tane Tekil Ürün oluştur.
        else:
            # Adet: Normal "quantity" değerini al
            adet = int(float(item.get("quantity", 1)))
            
            # Boyutlar: UNIT (Birim/Küçük) boyutlarını alıyoruz
            boy = float(p.get("unit_length") or 0)
            en  = float(p.get("unit_width") or 0)
            yuk = float(p.get("unit_height") or 0)
            agr = float(p.get("unit_weight") or 0)

            # (İsteğe bağlı log)
            # print(f"Tekil Mod: {p['code']} ürününden {adet} adet tekil ürün eklendi.")

        # Mukavemet (Varsa al yoksa 1000 kg varsay)
        max_stack = p.get("package_max_stack_weight")
        mukavemet = float(max_stack) if max_stack is not None else 1000.0

        # Belirlenen adet kadar ürünü listeye ekle
        for _ in range(adet):
            urun = UrunClass(
                urun_kodu=str(p["code"]),
                boy=boy,
                en=en,
                yukseklik=yuk,
                agirlik=agr,
                mukavemet=mukavemet,
                donus_serbest=True,
                istiflenebilir=True,
            )
            urunler.append(urun)
            
    return urunler

def group_by_product_code(urunler):
    gruplar = {}
    for u in urunler:
        kod = urun_kodu(u)
        gruplar.setdefault(kod, []).append(u)
    return gruplar