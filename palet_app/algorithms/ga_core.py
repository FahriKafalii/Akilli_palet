"""
GA Core Engine - Genetik Algoritma Ana Motoru
"""
import random
from typing import List

from .ga_chromosome import Chromosome
from .ga_fitness import evaluate_fitness
from .ga_utils import PaletConfig


def tournament_selection(population: List[Chromosome], k: int = 3) -> Chromosome:
    """
    K kişilik turnuva seçimi: en fit olan kazanır.
    """
    turnuva = random.sample(population, k)
    turnuva.sort(key=lambda c: c.fitness, reverse=True)
    return turnuva[0].copy()


def crossover(parent1: Chromosome, parent2: Chromosome) -> Chromosome:
    """
    Order Crossover (OX) + rotasyon genlerinin ebeveynlerden karışımı.
    """
    n = parent1.n
    sira1 = parent1.sira_gen
    sira2 = parent2.sira_gen

    # Kesim noktaları
    i = random.randint(0, n - 2)
    j = random.randint(i + 1, n - 1)

    child_sira = [-1] * n
    child_sira[i:j] = sira1[i:j]

    # Ebeveyn2'den eksik olanları sırayla doldur
    p2_filtered = [g for g in sira2 if g not in child_sira]
    idx = 0
    for pos in range(n):
        if child_sira[pos] == -1:
            child_sira[pos] = p2_filtered[idx]
            idx += 1

    # Rotasyon genleri: aynı indeksli ürüne göre ebeveynlerden rastgele
    child_rot = []
    for k in range(n):
        if random.random() < 0.5:
            child_rot.append(parent1.rot_gen[k])
        else:
            child_rot.append(parent2.rot_gen[k])

    child = Chromosome(urunler=parent1.urunler, sira_gen=child_sira, rot_gen=child_rot)
    return child


def mutate(individual: Chromosome, mutation_rate: float = 0.05):
    """
    Swap mutasyonu + Rotasyon mutasyonu.
    """
    n = individual.n

    # 1) Sıra Mutasyonu (Swap)
    if random.random() < mutation_rate:
        i = random.randint(0, n - 1)
        j = random.randint(0, n - 1)
        individual.sira_gen[i], individual.sira_gen[j] = (
            individual.sira_gen[j],
            individual.sira_gen[i],
        )

    # 2) Rotasyon Mutasyonu (Flip)
    if random.random() < mutation_rate:
        i = random.randint(0, n - 1)
        # 0 -> 1 veya 1 -> 0
        individual.rot_gen[i] = 1 - individual.rot_gen[i]


# --- DÜZELTME: tournament_k parametresi eklendi ---
def run_ga(urunler, palet_cfg: PaletConfig, population_size=30, generations=50, elitism=2, mutation_rate=0.1, tournament_k=3):
    """
    Genetik Algoritma Ana Döngüsü
    """
    if not urunler:
        return None, []

    # Başlangıç popülasyonu
    population: List[Chromosome] = [
        Chromosome(urunler=urunler) for _ in range(population_size)
    ]

    # İlk fitness hesaplaması
    for c in population:
        evaluate_fitness(c, palet_cfg)

    history = []

    for gen in range(generations):
        # Popülasyonu fitness'a göre sırala
        population.sort(key=lambda c: c.fitness, reverse=True)

        current_best = population[0]
        
        # Ortalama fitness (Takip için)
        avg_fitness = sum(c.fitness for c in population) / len(population)
        
        history.append({
            "generation": gen,
            "best_fitness": current_best.fitness,
            "avg_fitness": avg_fitness,
            "best_palet_sayisi": current_best.palet_sayisi,
            "best_doluluk": current_best.ortalama_doluluk,
        })

        # Konsola Bilgi Bas (Opsiyonel)
        if gen % 10 == 0 or gen == generations - 1:
            print(f"Gen {gen}: Best Fit={current_best.fitness:.2f}, Palet={current_best.palet_sayisi}, Doluluk={current_best.ortalama_doluluk:.2%}")

        # Yeni popülasyon
        new_population: List[Chromosome] = []

        # Elitizm
        for i in range(min(elitism, len(population))):
            new_population.append(population[i].copy())

        # Geri kalan bireyleri üret
        # Parametre olarak gelen tournament_k kullanılıyor
        while len(new_population) < population_size:
            parent1 = tournament_selection(population, k=tournament_k)
            parent2 = tournament_selection(population, k=tournament_k)

            child = crossover(parent1, parent2)
            mutate(child, mutation_rate=mutation_rate)

            evaluate_fitness(child, palet_cfg)
            new_population.append(child)

        population = new_population

    # Son değerlendirme
    population.sort(key=lambda c: c.fitness, reverse=True)
    best_solution = population[0]

    return best_solution, history