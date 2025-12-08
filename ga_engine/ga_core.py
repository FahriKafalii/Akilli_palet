import random
from typing import List

from .chromosome import Chromosome
from .fitness import evaluate_fitness
from .utils import PaletConfig


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

    # Rotasyon genleri: aynı indeksli ürüne göre ebeveynlerden seçim
    child_rot = [0] * n
    for pos, urun_idx in enumerate(child_sira):
        r1 = parent1.rot_gen[parent1.sira_gen.index(urun_idx)]
        r2 = parent2.rot_gen[parent2.sira_gen.index(urun_idx)]
        child_rot[pos] = random.choice([r1, r2])

    return Chromosome(parent1.urunler, sira_gen=child_sira, rot_gen=child_rot)


def mutate(chromosome: Chromosome, mutation_rate: float = 0.15):
    """
    İki tip mutasyon:
    - Sıra swap
    - Rotasyon değişimi
    """
    n = chromosome.n

    # SIRA MUTASYONU
    if random.random() < mutation_rate and n > 1:
        i, j = random.sample(range(n), 2)
        chromosome.sira_gen[i], chromosome.sira_gen[j] = (
            chromosome.sira_gen[j],
            chromosome.sira_gen[i],
        )
        chromosome.rot_gen[i], chromosome.rot_gen[j] = (
            chromosome.rot_gen[j],
            chromosome.rot_gen[i],
        )

    # ROTASYON MUTASYONU
    if random.random() < mutation_rate and n > 0:
        k = random.randint(0, n - 1)
        chromosome.rot_gen[k] = random.randint(0, 5)


def run_ga(
    urunler,
    palet_cfg: PaletConfig,
    population_size: int = 60,
    generations: int = 200,
    mutation_rate: float = 0.15,
    tournament_k: int = 3,
    elitism: int = 2,
):
    """
    GA motoru:
      - Giriş: MIX havuzundaki ürünler
      - Çıkış: En iyi kromozom + history
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

        best = population[0]
        history.append(
            {
                "generation": gen,
                "best_fitness": best.fitness,
                "palet_sayisi": best.palet_sayisi,
                "ortalama_doluluk": best.ortalama_doluluk,
            }
        )

        # Yeni popülasyon
        new_population: List[Chromosome] = []

        # Elitizm
        for i in range(min(elitism, len(population))):
            new_population.append(population[i].copy())

        # Geri kalan bireyleri üret
        while len(new_population) < population_size:
            parent1 = tournament_selection(population, k=tournament_k)
            parent2 = tournament_selection(population, k=tournament_k)

            child = crossover(parent1, parent2)
            mutate(child, mutation_rate=mutation_rate)

            evaluate_fitness(child, palet_cfg)
            new_population.append(child)

        population = new_population

    population.sort(key=lambda c: c.fitness, reverse=True)
    best_overall = population[0]

    return best_overall, history
