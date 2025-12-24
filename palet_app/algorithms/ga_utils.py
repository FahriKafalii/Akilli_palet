import math
import json

# -------------------------------------------------------------------
# 1) VERİ YAPILARI VE PARSER
# -------------------------------------------------------------------

class PaletConfig:
    """Palet parametreleri (JSON'dan beslenir)."""
    def __init__(self, length, width, height, max_weight):
        self.length = float(length)
        self.width = float(width)
        self.height = float(height)
        self.max_weight = float(max_weight)

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height

class UrunData:
    """Sistem içinde dolaşacak standart Ürün Objesi."""
    def __init__(self, urun_id, code, boy, en, yukseklik, agirlik, quantity=1, is_package=False):
        self.id = urun_id
        self.urun_kodu = code
        self.boy = float(boy)
        self.en = float(en)
        self.yukseklik = float(yukseklik)
        self.agirlik = float(agirlik)
        self.quantity = quantity
        self.is_package = is_package 
        self.donus_serbest = True 
        self.mukavemet = 99999 

    def __repr__(self):
        return f"<Urun {self.urun_kodu} ({self.boy}x{self.en}x{self.yukseklik})>"

def parse_json_input(json_data):
    """JSON verisini okur ve sistem nesnelerine çevirir."""
    c = json_data.get("container", {})
    palet_cfg = PaletConfig(
        length=c.get("length", 120),
        width=c.get("width", 100),
        height=c.get("height", 180),
        max_weight=c.get("weight", 1250)
    )

    all_products = []
    for detail in json_data.get("details", []):
        p_info = detail.get("product", {})
        qty_to_produce = detail.get("quantity", 0)
        
        # Koli mi Adet mi kontrolü
        pkg_qty = detail.get("package_quantity")
        if pkg_qty is not None and pkg_qty > 0:
            final_boy = p_info.get("package_length", 0)
            final_en = p_info.get("package_width", 0)
            final_yuk = p_info.get("package_height", 0)
            final_agirlik = p_info.get("package_weight", 0)
            is_pkg = True
        else:
            final_boy = p_info.get("unit_length", 0)
            final_en = p_info.get("unit_width", 0)
            final_yuk = p_info.get("unit_height", 0)
            final_agirlik = p_info.get("unit_weight", 0)
            is_pkg = False

        for _ in range(int(qty_to_produce)):
            u = UrunData(
                urun_id=p_info.get("id"),
                code=p_info.get("code"),
                boy=final_boy,
                en=final_en,
                yukseklik=final_yuk,
                agirlik=final_agirlik,
                is_package=is_pkg
            )
            all_products.append(u)

    return palet_cfg, all_products

def group_products_smart(urunler):
    """Code + Boyut + Ağırlık kombinasyonuna göre gruplar."""
    groups = {}
    for u in urunler:
        key = (u.urun_kodu, u.boy, u.en, u.yukseklik, u.agirlik)
        if key not in groups:
            groups[key] = []
        groups[key].append(u)
    return groups

# -------------------------------------------------------------------
# 2) YARDIMCI FONKSİYONLAR
# -------------------------------------------------------------------

def urun_hacmi(urun) -> float:
    return urun.boy * urun.en * urun.yukseklik

def urun_agirlik(urun) -> float:
    return urun.agirlik

def possible_orientations_for(urun):
    if not urun.donus_serbest:
        return [(urun.boy, urun.en, urun.yukseklik)]
    return [
        (urun.boy, urun.en, urun.yukseklik),
        (urun.en, urun.boy, urun.yukseklik),
    ]

# -------------------------------------------------------------------
# 3) SINGLE PALET SİMÜLASYON MANTIĞI (DEĞİŞTİ BURASI)
# -------------------------------------------------------------------

def solve_best_layer_configuration(palet_L, palet_W, item_L, item_W):
    """Kata en çok sığdıran konfigürasyonu bulur."""
    best_count = 0
    best_cfg = (0, 0)
    
    # Sadece Tip 1
    c1 = int(palet_L // item_L)
    r1 = int(palet_W // item_W)
    if c1 * r1 > best_count:
        best_count = c1 * r1
        best_cfg = (r1, 0)
        
    # Sadece Tip 2
    c2 = int(palet_L // item_W)
    r2 = int(palet_W // item_L)
    if c2 * r2 > best_count:
        best_count = c2 * r2
        best_cfg = (0, r2)

    return best_count, best_cfg

def simulate_single_pallet(urun_listesi, palet_cfg: PaletConfig):
    """
    Tek bir palet simüle eder.
    AĞIRLIK KRİTERİ KALDIRILDI -> SADECE HACİM %85
    """
    if not urun_listesi:
        return {"can_be_single": False, "pack_count": 0, "fill_ratio": 0}
    
    u0 = urun_listesi[0]
    PL, PW, PH = palet_cfg.length, palet_cfg.width, palet_cfg.height
    max_w = palet_cfg.max_weight
    
    # 1. Katman Hesabı
    items_per_layer, _ = solve_best_layer_configuration(PL, PW, u0.boy, u0.en)
    if items_per_layer == 0:
        return {"can_be_single": False, "pack_count": 0}

    # 2. Yükseklik Hesabı
    max_layers = int(PH // u0.yukseklik)
    
    # 3. Toplam Kapasite
    capacity_by_vol = items_per_layer * max_layers
    
    if u0.agirlik > 0:
        capacity_by_weight = int(max_w // u0.agirlik)
    else:
        capacity_by_weight = 999999
        
    # Paletin alabileceği maksimum ürün (Fiziksel Limit)
    # Ağırlık limitini yine de hesaplıyoruz ki palet kırılmasın.
    pallet_capacity = min(capacity_by_vol, capacity_by_weight)
    
    current_stock = len(urun_listesi)
    pack_count = min(current_stock, pallet_capacity)
    
    # BAŞARI KRİTERLERİ (GÜNCELLENDİ)
    total_vol_used = pack_count * urun_hacmi(u0)
    fill_ratio = total_vol_used / palet_cfg.volume
    
    is_success = False
    
    # --- YENİ KURAL: Sadece Hacim %85+ ---
    if fill_ratio >= 0.85:
        is_success = True
    else:
        # Ağırlık dolsa bile, hacim dolmadıysa Single sayma, Mix'e at.
        is_success = False

    return {
        "can_be_single": is_success,
        "pack_count": pack_count,
        "fill_ratio": fill_ratio
    }

# -------------------------------------------------------------------
# 4) MIX PALET (SHELF) MANTIĞI
# -------------------------------------------------------------------
def pack_shelf_based(urunler, rot_gen, palet_cfg: PaletConfig):
    """GA Motoru için Shelf (Raf) yerleştirme."""
    pallets = []
    current_items = []
    
    x, y, z = 0.0, 0.0, 0.0
    current_weight = 0.0
    
    current_shelf_height = 0.0
    current_shelf_y = 0.0    
    
    L, W, H = palet_cfg.length, palet_cfg.width, palet_cfg.height
    
    for idx, urun in enumerate(urunler):
        r = 0
        if rot_gen and idx < len(rot_gen):
            r = rot_gen[idx]
        
        dims = possible_orientations_for(urun)
        if r >= len(dims): r = 0
        u_l, u_w, u_h = dims[r]
        u_wgt = urun.agirlik
        
        # Yeni Palet Kontrolü (Ağırlık)
        if current_weight + u_wgt > palet_cfg.max_weight:
            pallets.append({"items": current_items, "weight": current_weight})
            current_items = []
            current_weight = 0.0
            x, y, z = 0.0, 0.0, 0.0
            current_shelf_height, current_shelf_y = 0.0, 0.0

        # Basit Shelf Mantığı (Yerleşim)
        # 1. Rafa sığıyor mu?
        if x + u_l > L:
            x = 0
            y += current_shelf_y if current_shelf_y > 0 else u_w
            current_shelf_y = 0 
            
        # 2. Katmana sığıyor mu?
        if y + u_w > W:
            x = 0
            y = 0
            z += current_shelf_height if current_shelf_height > 0 else u_h
            current_shelf_height = 0
            
        # 3. Palete sığıyor mu?
        if z + u_h > H:
             pallets.append({"items": current_items, "weight": current_weight})
             current_items = []
             current_weight = 0.0
             x, y, z = 0.0, 0.0, 0.0
             current_shelf_height, current_shelf_y = 0.0, 0.0

        # Yerleştir
        current_items.append({
            "urun": urun,
            "x": x, "y": y, "z": z,
            "L": u_l, "W": u_w, "H": u_h
        })
        current_weight += u_wgt
        
        # Pointer güncelle
        x += u_l
        if u_h > current_shelf_height: current_shelf_height = u_h
        if u_w > current_shelf_y: current_shelf_y = u_w
        
    if current_items:
        pallets.append({"items": current_items, "weight": current_weight})
        
    return pallets


def basit_palet_paketleme(chromosome, palet_cfg: PaletConfig):
    """
    Kromozomdan paletleri oluşturur.
    Kromozom: (urunler, rotations) tuple'ı
    
    Returns:
        list: Her palet için placements içeren dict listesi
    """
    urunler, rotations = chromosome
    
    # Pack shelf based kullanarak paletleri oluştur
    pallets = pack_shelf_based(urunler, rotations, palet_cfg)
    
    # Formatı views.py'nin beklediği şekle dönüştür
    result = []
    for pallet in pallets:
        placements = []
        for item in pallet['items']:
            placements.append({
                'urun': item['urun'],
                'x': item['x'],
                'y': item['y'],
                'z': item['z'],
                'L': item['L'],
                'W': item['W'],
                'H': item['H']
            })
        result.append({
            'placements': placements,
            'weight': pallet['weight']
        })
    
    return result