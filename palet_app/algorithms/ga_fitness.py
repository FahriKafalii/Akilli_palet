from dataclasses import dataclass
from .ga_utils import PaletConfig, pack_shelf_based, urun_hacmi

# --- TERAZİ AYARLARI (SENİN İSTEĞİNE GÖRE REVIZE EDİLDİ) ---
GA_WEIGHTS = {
    "w_volume": 5000,           # Hacim doldurma puanı (Düşürüldü)
    "w_min_pallet_bonus": 10000,# Palet sayısı azaltma bonusu (ARTIRILDI - Kritik Öncelik)
    "w_min_pallet_penalty": 5000, # Fazla palet cezası
    "w_weight_over": 1000000,   # Ağırlık aşımı (Ölümcül Ceza)
    "w_stack_violation": 1000000 # İstifleme hatası (Ölümcül Ceza)
}

@dataclass
class FitnessResult:
    fitness: float
    palet_sayisi: int
    ortalama_doluluk: float

def evaluate_fitness(chromosome, palet_cfg: PaletConfig) -> FitnessResult:
    """
    Kromozomun başarısını ölçer.
    """
    # 1. Yerleştirme Motorunu Çalıştır
    pallets = pack_shelf_based(chromosome.urunler, chromosome.rot_gen, palet_cfg)
    
    if not pallets:
        chromosome.fitness = -1e9
        return FitnessResult(-1e9, 0, 0.0)

    P_GA = len(pallets)
    total_volume_score = 0
    total_penalty = 0
    
    # 2. Paletleri Değerlendir
    total_fill_ratio = 0
    
    for p in pallets:
        # Doluluk Hesabı
        p_vol = sum(i["L"] * i["W"] * i["H"] for i in p["items"])
        fill_ratio = p_vol / palet_cfg.volume
        total_fill_ratio += fill_ratio
        
        # Puan: Doluluğun karesi (Dolu paletleri daha çok ödüllendir)
        total_volume_score += GA_WEIGHTS["w_volume"] * (fill_ratio ** 2)
        
        # Ağırlık Cezası
        if p["weight"] > palet_cfg.max_weight:
            total_penalty += GA_WEIGHTS["w_weight_over"]
            
    avg_doluluk = total_fill_ratio / P_GA if P_GA > 0 else 0

    # 3. Palet Sayısı Primi (En Önemli Kısım)
    # Teorik minimum (Hacimsel Alt Sınır)
    total_load_vol = sum(urun_hacmi(u) for u in chromosome.urunler)
    theo_min = int(total_load_vol // palet_cfg.volume) + 1
    
    if P_GA <= theo_min:
        # Beklenen veya daha az palet çıktıysa BÜYÜK ÖDÜL
        total_volume_score += GA_WEIGHTS["w_min_pallet_bonus"] * (theo_min - P_GA + 1)
    else:
        # Fazladan her palet için ceza
        extra = P_GA - theo_min
        total_penalty += GA_WEIGHTS["w_min_pallet_penalty"] * extra

    # Sonuç
    final_fitness = total_volume_score - total_penalty
    
    chromosome.fitness = final_fitness
    chromosome.palet_sayisi = P_GA
    chromosome.ortalama_doluluk = avg_doluluk
    
    return FitnessResult(final_fitness, P_GA, avg_doluluk)