"""
GA Fitness Değerlendirme Modülü
"""
from dataclasses import dataclass

# --- DÜZELTME: .utils yerine .ga_utils ---
from .ga_utils import (
    PaletConfig,
    basit_palet_paketleme,
    min_palet_sayisi_tez,
    cluster_purity,
    agirlik_merkezi_kaymasi_dummy,
    stacking_ihlali_sayisi_dummy,
)

# AŞAMA 3: GERÇEKÇİ FITNESS AYARLARI
GA_WEIGHTS = {
    "w_volume": 10000,
    "w_cluster": 0,
    "w_min_pallet_bonus": 2000,
    "w_min_pallet_penalty_1": 1000,
    "w_min_pallet_penalty_2": 5000,
    "w_weight_over": 1000000,
    "w_cm_offset": 5000,
    "w_stack_violation": 1000000,
    "w_rot_good": 100,
    "w_rot_bad": 100,
}

@dataclass
class FitnessResult:
    fitness: float
    palet_sayisi: int
    ortalama_doluluk: float


def evaluate_fitness(chromosome, palet_cfg: PaletConfig) -> FitnessResult:
    # --- KRİTİK: basit_palet_paketleme fonksiyonu ga_utils içindeki SHELF algoritmasını çağırır ---
    pallets = basit_palet_paketleme(chromosome, palet_cfg)

    if not pallets:
        chromosome.fitness = -1e9
        chromosome.palet_sayisi = 0
        chromosome.ortalama_doluluk = 0.0
        return FitnessResult(chromosome.fitness, 0, 0.0)

    P_GA = len(pallets)
    # Tez/Formül bazlı min palet sayısı tahmini
    P_min = min_palet_sayisi_tez(chromosome.urunler, palet_cfg)

    reward = 0.0
    penalties = 0.0
    toplam_doluluk = 0.0

    # Palet bazlı işlemler
    for palet in pallets:
        doluluk = palet.get("fill_ratio", 0.0)
        toplam_doluluk += doluluk

        purity = cluster_purity(palet["urunler"])
        reward += GA_WEIGHTS["w_volume"] * (doluluk ** 2)
        reward += GA_WEIGHTS["w_cluster"] * purity

        # Ağırlık Aşımı
        weight_over = max(0.0, palet["weight"] - palet_cfg.max_weight)
        if weight_over > 0:
            penalties += GA_WEIGHTS["w_weight_over"] * (weight_over / 10.0)

        # Ağırlık Merkezi (CoG) Cezası
        cm_offset = agirlik_merkezi_kaymasi_dummy(palet, palet_cfg)
        if cm_offset > 10.0: # 10 cm'den fazla kayma varsa ceza başlar
            penalties += GA_WEIGHTS["w_cm_offset"] * (cm_offset / 5.0)

        # Stacking İhlali Cezası
        stack_viol = stacking_ihlali_sayisi_dummy(palet)
        if stack_viol > 0:
            penalties += GA_WEIGHTS["w_stack_violation"] * stack_viol

    ort_doluluk = toplam_doluluk / P_GA

    # Palet sayısı ödül/cezası
    if P_GA == P_min:
        reward += GA_WEIGHTS["w_min_pallet_bonus"]
    elif P_GA == P_min + 1:
        penalties += GA_WEIGHTS["w_min_pallet_penalty_1"]
    elif P_GA >= P_min + 2:
        penalties += GA_WEIGHTS["w_min_pallet_penalty_2"]

    # FINAL FITNESS
    fitness = reward - penalties

    chromosome.fitness = fitness
    chromosome.palet_sayisi = P_GA
    chromosome.ortalama_doluluk = ort_doluluk

    return FitnessResult(fitness, P_GA, ort_doluluk)