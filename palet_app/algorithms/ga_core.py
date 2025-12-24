"""
GA Core Engine - Genetik Algoritma Ana Motoru
"""
import random
from typing import List

from .ga_chromosome import Chromosome
from .ga_fitness import evaluate_fitness, adapt_weights, get_weights
from .ga_utils import PaletConfig, urun_hacmi


def tournament_selection(population: List[Chromosome], k: int = 3) -> Chromosome:
    """
    K kişilik turnuva seçimi: en fit olan kazanır.
    """
    turnuva = random.sample(population, k)
    turnuva.sort(key=lambda c: c.fitness, reverse=True)
    return turnuva[0].copy()


def crossover(parent1: Chromosome, parent2: Chromosome) -> Chromosome:
    """
    Order Crossover (OX) - SEQUENCE-ONLY MODE.
    
    Auto-Orientation eliminates need for rotation gene crossover.
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

    child = Chromosome(urunler=parent1.urunler, sira_gen=child_sira)
    return child


def mutate(individual: Chromosome, mutation_rate: float = 0.05):
    """
    Swap mutasyonu - SEQUENCE-ONLY MODE.
    
    Auto-Orientation eliminates need for rotation mutation.
    """
    n = individual.n

    # Sıra Mutasyonu (Swap)
    if random.random() < mutation_rate:
        i = random.randint(0, n - 1)
        j = random.randint(0, n - 1)
        individual.sira_gen[i], individual.sira_gen[j] = (
            individual.sira_gen[j],
            individual.sira_gen[i],
        )


def create_seeded_chromosome(urunler, seed_type='volume'):
    """
    Heuristik tohum kromozomu oluşturur - SEQUENCE-ONLY.
    
    Args:
        urunler: Ürün listesi
        seed_type: 'volume' (hacim sıralaması) veya 'weight' (ağırlık sıralaması)
    
    Returns:
        Chromosome: Heuristik sıralı kromozom (Auto-Orientation)
    """
    n = len(urunler)
    
    # Ürün indekslerini sıralama kriterine göre sırala
    if seed_type == 'volume':
        # Hacim = Boy × En × Yükseklik (azalan sırada)
        indexed_items = [(i, urun_hacmi(urunler[i])) for i in range(n)]
        indexed_items.sort(key=lambda x: x[1], reverse=True)
    elif seed_type == 'weight':
        # Ağırlık (azalan sırada)
        indexed_items = [(i, urunler[i].agirlik) for i in range(n)]
        indexed_items.sort(key=lambda x: x[1], reverse=True)
    else:
        raise ValueError(f"Geçersiz seed_type: {seed_type}")
    
    # Sıralı indeksleri al
    sira_gen = [item[0] for item in indexed_items]
    
    return Chromosome(urunler=urunler, sira_gen=sira_gen)


def create_block_sorted_chromosome(urunler):
    """
    BLOCK-AWARE Seeding: Aynı boyutlu ürünleri gruplar - SEQUENCE-ONLY.
    
    Büyük öğelerin (45x35x30) dağılmasını önler, bunun yerine 'duvar gibi'
    istiflenmeleri için bloklar halinde sıralar.
    
    Args:
        urunler: Ürün listesi
    
    Returns:
        Chromosome: Blok sıralı kromozom (Auto-Orientation)
    """
    n = len(urunler)
    
    # Ürünleri boyutlarına göre grupla (boy, en, yükseklik)
    groups = {}
    for i in range(n):
        # Boyut imzasını oluştur (rotasyon bağımsız)
        dims = tuple(sorted([urunler[i].boy, urunler[i].en, urunler[i].yukseklik]))
        if dims not in groups:
            groups[dims] = []
        groups[dims].append(i)
    
    # Grupları boyutlarına göre sırala (büyükten küçüğe)
    sorted_groups = sorted(groups.items(), key=lambda x: x[0][0] * x[0][1] * x[0][2], reverse=True)
    
    # Bloklar halinde sırala (aynı boyutlar yan yana)
    sira_gen = []
    for dims, indices in sorted_groups:
        # Aynı boyuttaki tüm öğeleri ekle (blok oluşturur)
        sira_gen.extend(indices)
    
    return Chromosome(urunler=urunler, sira_gen=sira_gen)


def create_height_sorted_chromosome(urunler):
    """
    HEIGHT-AWARE Seeding: Ürünleri YÜKSEKLİĞE (Z-axis) göre gruplar - SEQUENCE-ONLY.
    
    CRITICAL: 30cm ve 35cm yükseklikli ürünlerin karışmasını önler.
    Aynı yükseklikteki ürünleri birlikte yerleştirerek düz 'katmanlar'
    oluşturur. Bu 'merdiven etkisi'ni ortadan kaldırır ve yoğun istif sağlar.
    
    Args:
        urunler: Ürün listesi
    
    Returns:
        Chromosome: Yükseklik-sıralı kromozom (Auto-Orientation)
    """
    n = len(urunler)
    
    # Ürünleri YÜKSEKLİĞE göre grupla
    height_groups = {}
    for i in range(n):
        height = urunler[i].yukseklik
        if height not in height_groups:
            height_groups[height] = []
        height_groups[height].append(i)
    
    # Grupları yüksekliğe göre sırala (büyükten küçüğe - en yüksek önce)
    sorted_heights = sorted(height_groups.items(), key=lambda x: x[0], reverse=True)
    
    # Yükseklik gruplarını sırayla ekle (level layer oluşturur)
    sira_gen = []
    for height, indices in sorted_heights:
        # Aynı yükseklikteki tüm ürünleri ekle
        sira_gen.extend(indices)
    
    return Chromosome(urunler=urunler, sira_gen=sira_gen)


# --- ADAPTIVE GA: Otomatik Parametre Ayarlama ---
def run_ga(urunler, palet_cfg: PaletConfig, population_size=None, generations=None, elitism=None, mutation_rate=0.4, tournament_k=2):
    """
    Genetik Algoritma Ana Döngüsü - ADAPTIVE WEIGHTS & PARAMETERS
    
    None parametreler ürün sayısına göre otomatik ayarlanır.
    """
    if not urunler:
        return None, []

    n_urun = len(urunler)
    
    # 🚀 LIGHT & FAST MODE for n_urun > 100 (Auto-Orientation)
    if n_urun > 100:
        population_size = 50   # LIGHT: Reduced from 100 (motor does the heavy lifting)
        generations = 100      # FAST: Reduced from 200 (30-second target)
        mutation_rate = 0.4    # High diversity in smaller population
        tournament_k = 2
        print(f"⚡ LIGHT & FAST MODE (Auto-Orientation): n_urun={n_urun} > 100")
        print(f"   Parameters: pop=50, gen=100, mut=0.4, tournament_k=2")
    else:
        # 🔧 ADAPTIVE: Ürün sayısına göre parametreleri otomatik ayarla
        if population_size is None:
            population_size = 50
        if generations is None:
            generations = 30
    
    if elitism is None:
        elitism = max(2, int(population_size * 0.05))  # %5 elitism
    
    print(f"🧬 GA Parametreler:")
    print(f"   Ürün Sayısı: {n_urun}")
    print(f"   Population: {population_size}")
    print(f"   Generations: {generations}")
    print(f"   Elitism: {elitism}")
    print(f"   Mutation Rate: {mutation_rate}")
    print(f"   Tournament K: {tournament_k}")

    # Teorik minimum palet sayısını hesapla (adaptive weights için)
    total_load_vol = sum(urun_hacmi(u) for u in urunler)
    theo_min_pallets = max(1, int(total_load_vol / palet_cfg.volume) + 1)
    
    # 🧬 HEIGHT-AWARE INITIAL POPULATION (Anti-Staircase)
    population: List[Chromosome] = []
    
    # HEIGHT SEEDS: %40 Yükseklik-Sıralı (30cm ve 35cm ayrı katmanlar)
    num_height_seeds = max(1, int(population_size * 0.40))
    print(f"📏 Creating {num_height_seeds} HEIGHT-sorted seeds (anti-staircase effect)...")
    for _ in range(num_height_seeds):
        population.append(create_height_sorted_chromosome(urunler))
    
    # RANDOM EXPLORATION: Kalan %60 tamamen rastgele (AI keşfi)
    num_random = population_size - len(population)
    print(f"🎲 Creating {num_random} RANDOM individuals for AI discovery...")
    for _ in range(num_random):
        population.append(Chromosome(urunler=urunler))
    
    print(f"✅ Total population: {len(population)} (Height: {num_height_seeds}, Random: {num_random})")

    # İlk fitness hesaplaması
    for c in population:
        evaluate_fitness(c, palet_cfg)

    history = []
    
    # Anti-Stagnation: Genetik Şok için takip değişkenleri
    best_fitness_tracker = float('-inf')
    generations_without_improvement = 0

    for gen in range(generations):
        # Popülasyonu fitness'a göre sırala
        population.sort(key=lambda c: c.fitness, reverse=True)

        current_best = population[0]
        
        # � LOCAL SEARCH (Hill Climbing): Fine-tune the best solution
        # Focus on re-sorting segments by height to flatten packing surface
        if gen % 5 == 0:  # Every 5 generations to avoid overhead
            original_fitness = current_best.fitness
            best_local = current_best.copy()
            
            for _ in range(10):  # 10 local search attempts
                candidate = current_best.copy()
                
                # 70% chance: Height-aware segment re-sort
                if random.random() < 0.7:
                    # Select a random segment (10-20% of items)
                    segment_size = max(5, int(candidate.n * 0.15))
                    start_idx = random.randint(0, max(0, candidate.n - segment_size))
                    end_idx = min(start_idx + segment_size, candidate.n)
                    
                    # Extract segment indices
                    segment_items = candidate.sira_gen[start_idx:end_idx]
                    
                    # Re-sort this segment by HEIGHT (tallest first)
                    segment_with_heights = [(idx, urunler[idx].yukseklik) for idx in segment_items]
                    segment_with_heights.sort(key=lambda x: x[1], reverse=True)
                    
                    # Replace segment with height-sorted version
                    for i, (idx, _) in enumerate(segment_with_heights):
                        candidate.sira_gen[start_idx + i] = idx
                else:
                    # 30% chance: Standard swap mutation (sequence-only)
                    i = random.randint(0, candidate.n - 1)
                    j = random.randint(0, candidate.n - 1)
                    candidate.sira_gen[i], candidate.sira_gen[j] = candidate.sira_gen[j], candidate.sira_gen[i]
                
                # Evaluate the tweaked solution
                evaluate_fitness(candidate, palet_cfg)
                
                # If better, update local best
                if candidate.fitness > best_local.fitness:
                    best_local = candidate.copy()
            
            # If local search found improvement, replace current_best in population
            if best_local.fitness > original_fitness:
                population[0] = best_local
                current_best = best_local
                print(f"  🔍 Height-Aware Local Search improved: {original_fitness:.2f} → {best_local.fitness:.2f}")
        
        # �🔧 ANTI-STAGNATION: Durgunluk tespiti
        if current_best.fitness > best_fitness_tracker:
            best_fitness_tracker = current_best.fitness
            generations_without_improvement = 0
        else:
            generations_without_improvement += 1
        
        # 💥 GENETİK ŞOK: 20 nesil iyileşme yoksa popülasyonun %50'sini SİRALİ tohumlarla değiştir
        if generations_without_improvement >= 20 and gen < generations - 5:
            print(f"  💥 GENETİK ŞOK! {generations_without_improvement} nesil iyileşme yok - Popülasyonun %50'si SIRALI tohumlarla değiştiriliyor...")
            num_to_replace = int(population_size * 0.5)
            half = num_to_replace // 2
            
            # Elite'leri koru, geri kalanları sıralı tohumlarla değiştir
            idx = elitism
            
            # %50 Hacim-Sıralı tohumlar
            for _ in range(half):
                if idx < len(population):
                    population[idx] = create_seeded_chromosome(urunler, seed_type='volume')
                    evaluate_fitness(population[idx], palet_cfg)
                    idx += 1
            
            # %50 Ağırlık-Sıralı tohumlar
            remaining = num_to_replace - half
            for _ in range(remaining):
                if idx < len(population):
                    population[idx] = create_seeded_chromosome(urunler, seed_type='weight')
                    evaluate_fitness(population[idx], palet_cfg)
                    idx += 1
            
            print(f"  ✅ {num_to_replace} sıralı tohum eklendi ({half} hacim, {remaining} ağırlık) - Elite {elitism} korundu")
            generations_without_improvement = 0  # Sayacı sıfırla
        
        # 🔧 ADAPTIVE: Her 5 generation'da bir ağırlıkları ayarla
        if gen % 5 == 0 and gen > 0:
            adapt_weights(current_best, theo_min_pallets)
        
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