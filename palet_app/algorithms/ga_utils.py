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
    """
    REFACTORED: Mixed-Orientation Tiling Algorithm.
    
    Iterates through possible row counts for orientation A (item_L x item_W),
    then fills remaining space with orientation B (item_W x item_L).
    
    Returns:
        tuple: (total_items_per_layer, layout_description, mixed_config)
               layout_description: Human-readable string
               mixed_config: {'type_a_rows': int, 'type_b_rows': int, 'cols_a': int, 'cols_b': int}
    """
    best_count = 0
    best_layout_desc = ""
    best_config = {'type_a_rows': 0, 'type_b_rows': 0, 'cols_a': 0, 'cols_b': 0, 'orientation': 0}
    
    # Strategy 1: 100% Orientation A (item_L along X, item_W along Y)
    cols_a = int(palet_L // item_L)
    rows_a_max = int(palet_W // item_W)
    
    if cols_a > 0 and rows_a_max > 0:
        count = cols_a * rows_a_max
        if count > best_count:
            best_count = count
            best_layout_desc = f"{rows_a_max} rows of {cols_a} items ({item_L}×{item_W})"
            best_config = {
                'type_a_rows': rows_a_max,
                'type_b_rows': 0,
                'cols_a': cols_a,
                'cols_b': 0,
                'orientation': 0
            }
    
    # Strategy 2: 100% Orientation B (item_W along X, item_L along Y)
    cols_b = int(palet_L // item_W)
    rows_b_max = int(palet_W // item_L)
    
    if cols_b > 0 and rows_b_max > 0:
        count = cols_b * rows_b_max
        if count > best_count:
            best_count = count
            best_layout_desc = f"{rows_b_max} rows of {cols_b} items ({item_W}×{item_L})"
            best_config = {
                'type_a_rows': 0,
                'type_b_rows': rows_b_max,
                'cols_a': 0,
                'cols_b': cols_b,
                'orientation': 1
            }
    
    # Strategy 3: MIXED-ORIENTATION TILING
    # Try i rows of Orientation A, fill remaining space with Orientation B
    if cols_a > 0 and cols_b > 0:
        for i in range(1, rows_a_max + 1):
            # i rows of Orientation A
            count_a = cols_a * i
            used_width_a = i * item_W
            
            # Remaining width
            remaining_width = palet_W - used_width_a
            
            # How many rows of Orientation B fit in remaining space?
            rows_b_possible = int(remaining_width // item_L)
            count_b = cols_b * rows_b_possible
            
            total_count = count_a + count_b
            
            if total_count > best_count:
                best_count = total_count
                best_layout_desc = (f"{i} rows Type-A ({cols_a} items @ {item_L}×{item_W}) + "
                                   f"{rows_b_possible} rows Type-B ({cols_b} items @ {item_W}×{item_L})")
                best_config = {
                    'type_a_rows': i,
                    'type_b_rows': rows_b_possible,
                    'cols_a': cols_a,
                    'cols_b': cols_b,
                    'orientation': 2  # Mixed
                }
    
    # Also try reverse: i rows of Orientation B, fill with Orientation A
    if cols_a > 0 and cols_b > 0:
        for i in range(1, rows_b_max + 1):
            count_b = cols_b * i
            used_width_b = i * item_L
            remaining_width = palet_W - used_width_b
            
            rows_a_possible = int(remaining_width // item_W)
            count_a = cols_a * rows_a_possible
            
            total_count = count_a + count_b
            
            if total_count > best_count:
                best_count = total_count
                best_layout_desc = (f"{i} rows Type-B ({cols_b} items @ {item_W}×{item_L}) + "
                                   f"{rows_a_possible} rows Type-A ({cols_a} items @ {item_L}×{item_W})")
                best_config = {
                    'type_a_rows': rows_a_possible,
                    'type_b_rows': i,
                    'cols_a': cols_a,
                    'cols_b': cols_b,
                    'orientation': 3  # Mixed reverse
                }
    
    return best_count, best_layout_desc, best_config

def generate_grid_placement(items_to_place, palet_cfg: PaletConfig):
    """
    REFACTORED: Supports Mixed-Orientation Grid Placement.
    
    Generates actual X,Y,Z coordinates for grid layouts, including
    mixed-orientation tiling (Type-A rows + Type-B rows).
    
    Args:
        items_to_place: List of UrunData (same type)
        palet_cfg: Pallet configuration
        
    Returns:
        list: Placements with {'urun', 'x', 'y', 'z', 'L', 'W', 'H'}
    """
    if not items_to_place:
        return []
    
    u0 = items_to_place[0]
    PL, PW, PH = palet_cfg.length, palet_cfg.width, palet_cfg.height
    
    # Get optimal layer configuration (with mixed-orientation support)
    items_per_layer, layout_desc, layer_config = solve_best_layer_configuration(
        PL, PW, u0.boy, u0.en
    )
    
    if items_per_layer == 0:
        return []
    
    item_H = u0.yukseklik
    max_layers = int(PH // item_H)
    
    placements = []
    item_idx = 0
    
    # Extract configuration
    type_a_rows = layer_config['type_a_rows']
    type_b_rows = layer_config['type_b_rows']
    cols_a = layer_config['cols_a']
    cols_b = layer_config['cols_b']
    orientation = layer_config['orientation']
    
    # Determine dimensions for Type-A and Type-B
    if orientation in [0, 2, 3]:  # Type-A: item_L x item_W
        item_L_a, item_W_a = u0.boy, u0.en
    else:
        item_L_a, item_W_a = u0.en, u0.boy
    
    if orientation in [1, 2, 3]:  # Type-B: item_W x item_L
        item_L_b, item_W_b = u0.en, u0.boy
    else:
        item_L_b, item_W_b = u0.boy, u0.en
    
    for layer in range(max_layers):
        z = layer * item_H
        y_offset = 0
        
        # Place Type-A rows
        for row in range(type_a_rows):
            y = y_offset + row * item_W_a
            
            for col in range(cols_a):
                if item_idx >= len(items_to_place):
                    return placements
                
                x = col * item_L_a
                
                placements.append({
                    'urun': items_to_place[item_idx],
                    'x': x,
                    'y': y,
                    'z': z,
                    'L': item_L_a,
                    'W': item_W_a,
                    'H': item_H
                })
                item_idx += 1
        
        # Update Y offset for Type-B rows
        y_offset += type_a_rows * item_W_a
        
        # Place Type-B rows
        for row in range(type_b_rows):
            y = y_offset + row * item_W_b
            
            for col in range(cols_b):
                if item_idx >= len(items_to_place):
                    return placements
                
                x = col * item_L_b
                
                placements.append({
                    'urun': items_to_place[item_idx],
                    'x': x,
                    'y': y,
                    'z': z,
                    'L': item_L_b,
                    'W': item_W_b,
                    'H': item_H
                })
                item_idx += 1
    
    return placements

def simulate_single_pallet(urun_listesi, palet_cfg: PaletConfig):
    """
    REFACTORED: Efficiency-Based Single Pallet Simulation.
    
    KEY CHANGE: Evaluates product suitability based on CAPACITY efficiency,
    not current stock. A product is suitable for Single Pallet if its optimal
    tiling configuration achieves >= 90% pallet utilization.
    
    Returns:
        dict: {
            'can_be_single': bool,  # True if Efficiency >= 0.90
            'capacity': int,        # Max items that fit (volume & weight constrained)
            'pack_count': int,      # min(stock, capacity)
            'efficiency': float,    # (Capacity × ItemVolume) / PalletVolume
            'layout_desc': str,     # Human-readable tiling description
            'reason': str           # Decision explanation
        }
    """
    if not urun_listesi:
        return {
            "can_be_single": False,
            "capacity": 0,
            "pack_count": 0,
            "efficiency": 0,
            "layout_desc": "",
            "reason": "Empty product list"
        }
    
    u0 = urun_listesi[0]
    PL, PW, PH = palet_cfg.length, palet_cfg.width, palet_cfg.height
    max_w = palet_cfg.max_weight
    
    # 1. Calculate OPTIMAL LAYER CONFIGURATION (Mixed-Orientation Tiling)
    items_per_layer, layout_desc, layer_config = solve_best_layer_configuration(
        PL, PW, u0.boy, u0.en
    )
    
    if items_per_layer == 0:
        return {
            "can_be_single": False,
            "capacity": 0,
            "pack_count": 0,
            "efficiency": 0,
            "layout_desc": "No valid configuration",
            "reason": "Product dimensions exceed pallet size"
        }
    
    # 2. Calculate MAX LAYERS (Height Constraint)
    max_layers = int(PH // u0.yukseklik)
    
    if max_layers == 0:
        return {
            "can_be_single": False,
            "capacity": 0,
            "pack_count": 0,
            "efficiency": 0,
            "layout_desc": layout_desc,
            "reason": "Product height exceeds pallet height"
        }
    
    # 3. Calculate CAPACITY (Volume-based)
    capacity_by_volume = items_per_layer * max_layers
    
    # 4. Calculate CAPACITY (Weight-based)
    if u0.agirlik > 0:
        capacity_by_weight = int(max_w / u0.agirlik)
    else:
        capacity_by_weight = 999999
    
    # 5. Final CAPACITY = min(volume_capacity, weight_capacity)
    capacity = min(capacity_by_volume, capacity_by_weight)
    
    # 6. Calculate EFFICIENCY (This is the KEY metric)
    # Efficiency = (Capacity × ItemVolume) / PalletVolume
    item_volume = urun_hacmi(u0)
    pallet_volume = palet_cfg.volume
    efficiency = (capacity * item_volume) / pallet_volume
    
    # 7. DECISION RULE: Efficiency >= 90%
    is_suitable = (efficiency >= 0.90)
    
    # 8. Calculate actual pack_count (for current stock)
    current_stock = len(urun_listesi)
    pack_count = min(current_stock, capacity)
    
    # 9. Generate detailed reason
    if is_suitable:
        if capacity_by_volume < capacity_by_weight:
            constraint = "volume-limited"
        elif capacity_by_weight < capacity_by_volume:
            constraint = "weight-limited"
        else:
            constraint = "perfectly balanced"
        
        reason = (f"✅ Efficiency: {efficiency*100:.1f}% ({constraint}) | "
                 f"Capacity: {capacity} items | Layout: {layout_desc}")
    else:
        reason = (f"❌ Efficiency: {efficiency*100:.1f}% < 90% threshold | "
                 f"Capacity: {capacity} items | Layout: {layout_desc}")
    
    return {
        "can_be_single": is_suitable,
        "capacity": capacity,
        "pack_count": pack_count,
        "efficiency": efficiency,
        "layout_desc": layout_desc,
        "reason": reason
    }

# -------------------------------------------------------------------
# 4) MIX PALET (SHELF) MANTIĞI - ADVANCED HEURISTICS
# -------------------------------------------------------------------

class FreeRectangle:
    """Boş dikdörtgen alanı temsil eder (Maximal Rectangles için)"""
    def __init__(self, x, y, z, length, width, height):
        self.x = x
        self.y = y
        self.z = z
        self.length = length
        self.width = width
        self.height = height
        self.volume = length * width * height
    
    def can_fit(self, item_l, item_w, item_h):
        """Ürün bu alana sığar mı?"""
        return (self.length >= item_l and 
                self.width >= item_w and 
                self.height >= item_h)
    
    def __repr__(self):
        return f"Rect({self.x},{self.y},{self.z} | {self.length}×{self.width}×{self.height})"

def split_rectangle(rect, item_l, item_w, item_h):
    """
    Guillotine Cut: Yerleştirme sonrası kalan alanı böler.
    
    Returns:
        list: Yeni oluşan boş dikdörtgenler
    """
    new_rects = []
    
    # X ekseni boyunca kalan (sağ taraf)
    if rect.length > item_l:
        new_rects.append(FreeRectangle(
            rect.x + item_l, rect.y, rect.z,
            rect.length - item_l, rect.width, rect.height
        ))
    
    # Y ekseni boyunca kalan (arka taraf)
    if rect.width > item_w:
        new_rects.append(FreeRectangle(
            rect.x, rect.y + item_w, rect.z,
            item_l, rect.width - item_w, rect.height
        ))
    
    # Z ekseni boyunca kalan (üst taraf)
    if rect.height > item_h:
        new_rects.append(FreeRectangle(
            rect.x, rect.y, rect.z + item_h,
            item_l, item_w, rect.height - item_h
        ))
    
    return new_rects

def find_best_rectangle(free_rects, item_l, item_w, item_h):
    """
    En uygun boş dikdörtgeni bulur (Best-Fit-Decreasing stratejisi).
    
    Returns:
        FreeRectangle or None
    """
    best_rect = None
    min_volume_diff = float('inf')
    
    for rect in free_rects:
        if rect.can_fit(item_l, item_w, item_h):
            # En sıkı sığan alanı tercih et (minimum boşluk)
            volume_diff = rect.volume - (item_l * item_w * item_h)
            
            if volume_diff < min_volume_diff:
                min_volume_diff = volume_diff
                best_rect = rect
    
    return best_rect

def pack_maximal_rectangles(urunler, rot_gen, palet_cfg: PaletConfig):
    """
    Maximal Rectangles Algorithm - Industry Standard 3D Bin Packing.
    
    Avantajları:
    - Boş alanları daha verimli kullanır
    - Guillotine cuts ile optimal bölme
    - Fill ratio ~%3-5 daha yüksek
    
    Args:
        urunler: Yerleştirilecek ürünler
        rot_gen: Rotasyon genleri (0 veya 1)
        palet_cfg: Palet konfigürasyonu
        
    Returns:
        list: Paletler (her biri items ve weight içerir)
    """
    pallets = []
    current_pallet = {
        'items': [],
        'weight': 0.0,
        'free_rects': [FreeRectangle(
            0, 0, 0, 
            palet_cfg.length, palet_cfg.width, palet_cfg.height
        )]
    }
    
    for idx, urun in enumerate(urunler):
        # Rotasyon genine göre boyutları al
        r = rot_gen[idx] if idx < len(rot_gen) else 0
        dims = possible_orientations_for(urun)
        if r >= len(dims): r = 0
        u_l, u_w, u_h = dims[r]
        u_wgt = urun.agirlik
        
        # Ağırlık kontrolü - yeni palet gerekli mi?
        if current_pallet['weight'] + u_wgt > palet_cfg.max_weight:
            if current_pallet['items']:
                pallets.append({
                    'items': current_pallet['items'],
                    'weight': current_pallet['weight']
                })
            
            # Yeni palet başlat
            current_pallet = {
                'items': [],
                'weight': 0.0,
                'free_rects': [FreeRectangle(
                    0, 0, 0,
                    palet_cfg.length, palet_cfg.width, palet_cfg.height
                )]
            }
        
        # En iyi boş alanı bul
        best_rect = find_best_rectangle(current_pallet['free_rects'], u_l, u_w, u_h)
        
        if best_rect is None:
            # Mevcut palete sığmıyor, yeni palet aç
            if current_pallet['items']:
                pallets.append({
                    'items': current_pallet['items'],
                    'weight': current_pallet['weight']
                })
            
            current_pallet = {
                'items': [],
                'weight': 0.0,
                'free_rects': [FreeRectangle(
                    0, 0, 0,
                    palet_cfg.length, palet_cfg.width, palet_cfg.height
                )]
            }
            
            best_rect = current_pallet['free_rects'][0]
        
        # Ürünü yerleştir
        current_pallet['items'].append({
            'urun': urun,
            'x': best_rect.x,
            'y': best_rect.y,
            'z': best_rect.z,
            'L': u_l,
            'W': u_w,
            'H': u_h
        })
        current_pallet['weight'] += u_wgt
        
        # Boş alanları güncelle (Guillotine Cut)
        current_pallet['free_rects'].remove(best_rect)
        new_rects = split_rectangle(best_rect, u_l, u_w, u_h)
        current_pallet['free_rects'].extend(new_rects)
        
        # Çakışan dikdörtgenleri temizle (optional optimization)
        current_pallet['free_rects'] = remove_redundant_rectangles(
            current_pallet['free_rects']
        )
    
    # Son paleti ekle
    if current_pallet['items']:
        pallets.append({
            'items': current_pallet['items'],
            'weight': current_pallet['weight']
        })
    
    return pallets

def remove_redundant_rectangles(rects):
    """
    Birbirinin içinde olan dikdörtgenleri kaldırır.
    Küçük olanı sil, büyüğü tut (daha geniş arama alanı).
    """
    filtered = []
    
    for i, rect1 in enumerate(rects):
        is_contained = False
        
        for j, rect2 in enumerate(rects):
            if i == j:
                continue
            
            # rect1, rect2'nin içinde mi?
            if (rect2.x <= rect1.x and 
                rect2.y <= rect1.y and 
                rect2.z <= rect1.z and
                rect2.x + rect2.length >= rect1.x + rect1.length and
                rect2.y + rect2.width >= rect1.y + rect1.width and
                rect2.z + rect2.height >= rect1.z + rect1.height):
                is_contained = True
                break
        
        if not is_contained:
            filtered.append(rect1)
    
    return filtered

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