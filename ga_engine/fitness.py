from dataclasses import dataclass

from .utils import (
    PaletConfig,
    basit_palet_paketleme,
    min_palet_sayisi_tez,
    cluster_purity,
    agirlik_merkezi_kaymasi_dummy,
    stacking_ihlali_sayisi_dummy,
    theoretical_best_rot_index,
)


# Dışarıdan kolay ayarlanabilsin diye weights dict
GA_WEIGHTS = {
    "w_volume": 1500,
    "w_cluster": 1200,
    "w_min_pallet_bonus": 800,
    "w_min_pallet_penalty_1": 300,
    "w_min_pallet_penalty_2": 1000,
    "w_weight_over": 5000,
    "w_height_over": 5000,  # şu an kullanılmıyor (yükseklik hesabı basit pakette yok)
    "w_collision": 4000,  # çakışma yok → 0
    "w_stack_violation": 1500,
    "w_rot_good": 300,
    "w_rot_bad": 300,
    "w_cm_offset": 200,
}


@dataclass
class FitnessResult:
    fitness: float
    palet_sayisi: int
    ortalama_doluluk: float


def evaluate_fitness(chromosome, palet_cfg: PaletConfig) -> FitnessResult:
    """
    Mix GA için fitness hesaplar.
    Bu versiyon basitleştirilmiş bir 1D paketleme kullanır.
    """
    pallets = basit_palet_paketleme(chromosome, palet_cfg)

    if not pallets:
        chromosome.fitness = -1e9
        chromosome.palet_sayisi = 0
        chromosome.ortalama_doluluk = 0.0
        return FitnessResult(chromosome.fitness, 0, 0.0)

    P_GA = len(pallets)
    P_min = min_palet_sayisi_tez(chromosome.urunler, palet_cfg)

    # --------- ÖDÜLLER ---------
    reward = 0.0
    penalties = 0.0

    # Palet bazlı ödüller / cezalar
    toplam_doluluk = 0.0
    for palet in pallets:
        doluluk = palet.get("fill_ratio", 0.0)
        toplam_doluluk += doluluk
        purity = cluster_purity(palet["urunler"])

        # Hacim & cluster ödülü
        reward += GA_WEIGHTS["w_volume"] * doluluk
        reward += GA_WEIGHTS["w_cluster"] * purity

        # Ağırlık aşımı kontrolü (teoride basit_paketleme buna izin vermiyor)
        weight_over = max(0.0, palet["weight"] - palet_cfg.max_weight)
        if weight_over > 0:
            penalties += GA_WEIGHTS["w_weight_over"] * (weight_over / 10.0)

        # Ağırlık merkezi (şu an dummy = 0)
        cm_offset = agirlik_merkezi_kaymasi_dummy(palet)
        penalties += GA_WEIGHTS["w_cm_offset"] * cm_offset

        # Stacking ihlali (dummy)
        stack_viol = stacking_ihlali_sayisi_dummy(palet)
        penalties += GA_WEIGHTS["w_stack_violation"] * stack_viol

        # Çakışma / yükseklik bu basit versiyonda yok → 0 sayıyoruz

    ort_doluluk = toplam_doluluk / P_GA

    # Palet sayısı terimi
    if P_GA == P_min:
        reward += GA_WEIGHTS["w_min_pallet_bonus"]
    elif P_GA == P_min + 1:
        penalties += GA_WEIGHTS["w_min_pallet_penalty_1"]
    elif P_GA >= P_min + 2:
        penalties += GA_WEIGHTS["w_min_pallet_penalty_2"]

    # Rotasyon uygunluğu ödül/cezası (ürün bazlı)
    # (Basit yaklaşım: ideal rotasyonu "en düşük yükseklik" veren rotasyon kabul ettik)
    rot_reward = 0.0
    for gene_idx, urun_idx in enumerate(chromosome.sira_gen):
        urun = chromosome.urunler[urun_idx]
        best_idx = theoretical_best_rot_index(urun, palet_cfg)
        chosen = chromosome.rot_gen[gene_idx]

        if chosen == best_idx:
            rot_reward += GA_WEIGHTS["w_rot_good"]
        else:
            rot_reward -= GA_WEIGHTS["w_rot_bad"]

    reward += rot_reward

    fitness = reward - penalties

    chromosome.fitness = fitness
    chromosome.palet_sayisi = P_GA
    chromosome.ortalama_doluluk = ort_doluluk

    return FitnessResult(fitness, P_GA, ort_doluluk)
