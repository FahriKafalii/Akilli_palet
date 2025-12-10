import json
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import random
import sys
import os

# ---------------------------------------------------------
# AYARLAR
# ---------------------------------------------------------
# Eğer script ga_engine içinden çalışıyorsa bir üst klasöre bakması gerekebilir
# Garanti olsun diye mutlak yol veya relative kontrol yapalım
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Eğer ga_engine içindeysek bir üst klasörde sonuc.json vardır
JSON_FILE = os.path.join(BASE_DIR, "..", "sonuc.json")

# Eğer dosya orada yoksa, script ana dizinden çağrılmıştır, direkt isme bakalım
if not os.path.exists(JSON_FILE):
    JSON_FILE = "sonuc.json"

random.seed(42)
COLOR_MAP = {}

def get_color(code):
    if code not in COLOR_MAP:
        COLOR_MAP[code] = (random.uniform(0.2, 0.9), random.uniform(0.2, 0.9), random.uniform(0.2, 0.9))
    return COLOR_MAP[code]

def load_data():
    if not os.path.exists(JSON_FILE):
        print(f"HATA: '{JSON_FILE}' bulunamadı!")
        print("Lütfen önce 'python -m ga_engine.main' komutunu çalıştırın.")
        sys.exit(1)
        
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Global değişkenler (Butonlar erişebilsin diye)
current_idx = 0
pallets = []
data = {}
ax = None
fig = None

def draw_current_pallet(event=None):
    global current_idx, ax, fig
    
    # Mevcut çizimi temizle
    ax.clear()
    
    pallet = pallets[current_idx]
    items = pallet.get("items", [])
    
    # Palet Genel Bilgileri
    p_id = pallet["pallet_id"]
    p_type = pallet["type"]
    p_fill = pallet.get("fill_ratio", 0)
    
    # Palet Boyutları
    p_dims = data["summary"]["pallet_dimensions"]
    PL, PW, PH = p_dims["length"], p_dims["width"], p_dims["height"]

    # Başlık
    ax.set_title(f"Palet {current_idx + 1}/{len(pallets)}\nID: {p_id} ({p_type}) - Doluluk: %{p_fill*100:.2f}", fontsize=12)

    # 1. PALET SINIRLARI
    corners = [
        [0, 0, 0], [PL, 0, 0], [PL, PW, 0], [0, PW, 0],
        [0, 0, PH], [PL, 0, PH], [PL, PW, PH], [0, PW, PH]
    ]
    edges = [
        [0,1], [1,2], [2,3], [3,0],
        [4,5], [5,6], [6,7], [7,4],
        [0,4], [1,5], [2,6], [3,7]
    ]
    
    for edge in edges:
        p1, p2 = corners[edge[0]], corners[edge[1]]
        ax.plot3D([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]], 'k--', lw=0.5, alpha=0.3)

    # 2. KUTULARI ÇİZ
    used_codes = set()
    for item in items:
        x, y, z = item["x"], item["y"], item["z"]
        dx, dy, dz = item["L"], item["W"], item["H"]
        code = item["code"]
        
        color = get_color(code)
        used_codes.add(code)

        ax.bar3d(x, y, z, dx, dy, dz, color=color, alpha=0.85, edgecolor='k', linewidth=0.5, shade=True)

    # 3. AYARLAR
    ax.set_xlabel('Boy (cm)')
    ax.set_ylabel('En (cm)')
    ax.set_zlabel('Yükseklik (cm)')
    
    ax.set_xlim([0, PL])
    ax.set_ylim([0, PW])
    ax.set_zlim([0, PH])
    
    try:
        ax.set_box_aspect((PL, PW, PH))
    except:
        pass

    # Çizimi güncelle
    plt.draw()

def next_pallet(event):
    global current_idx
    if current_idx < len(pallets) - 1:
        current_idx += 1
        draw_current_pallet()
    else:
        print("Zaten son palettesiniz.")

def prev_pallet(event):
    global current_idx
    if current_idx > 0:
        current_idx -= 1
        draw_current_pallet()
    else:
        print("Zaten ilk palettesiniz.")

def main():
    global pallets, data, ax, fig, current_idx
    
    data = load_data()
    pallets = data["pallets"]
    
    if not pallets:
        print("Gösterilecek palet yok!")
        return

    # Mix paletlere hızlı geçmek için başlangıcı ayarlayabilirsin
    # current_idx = 0 
    
    # Grafik Penceresini Hazırla
    fig = plt.figure(figsize=(12, 9))
    # Alt tarafta butonlar için yer bırak (bottom=0.2)
    plt.subplots_adjust(bottom=0.2)
    
    ax = fig.add_subplot(111, projection='3d')

    # Butonları Ekle
    # [x, y, genişlik, yükseklik]
    axprev = plt.axes([0.3, 0.05, 0.15, 0.075])
    axnext = plt.axes([0.55, 0.05, 0.15, 0.075])
    
    bnext = Button(axnext, 'Sonraki >>')
    bprev = Button(axprev, '<< Önceki')
    
    bnext.on_clicked(next_pallet)
    bprev.on_clicked(prev_pallet)

    # İlk paleti çiz
    draw_current_pallet()
    
    print("="*40)
    print(f"📦 GALERİ MODU BAŞLATILDI")
    print(f"Toplam Palet: {len(pallets)}")
    print("Penceredeki butonları kullanarak gezebilirsiniz.")
    print("="*40)

    plt.show()

if __name__ == "__main__":
    main()