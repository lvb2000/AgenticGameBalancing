import random
import matplotlib.pyplot as plt
from collections import defaultdict

class Character:
    def __init__(self, name, attack_power, health, healing, attack_cooldown, healing_cooldown):
        self.name = name
        self.attack_power = attack_power
        self.healing = healing
        self.max_health = health
        self.health = health
        # Support both 'cooldown' (legacy) and 'attack_cooldown' parameters
        self.attack_cooldown = attack_cooldown
        self.healing_cooldown = healing_cooldown
        # Track time until next action
        self.time_until_attack = 0.0
        self.time_until_heal = 0.0

    def attack(self):
        # Add miss chance (10% chance to miss - increased for broader optimum)
        if random.random() < 0.05:
            return 0
        
        # Basic damage calculation + Gaussian (normal) noise around attack_power
        base_damage = int(random.gauss(self.attack_power, 8))
        
        
        return max(0, base_damage)  # Ensure non-negative damage
    
    def heal(self):
        # Add miss chance (10% chance to miss - increased for broader optimum)
        if random.random() < 0.05:
            return self.health

        # Heal with some randomness around healing amount
        heal_variance = random.gauss(1.0, 0.2)  # Gaussian noise, mean=1.0, stdev=0.2 (roughly covers ±20% with >95% prob)
        healing_amount = int(self.healing * heal_variance)

        self.health = min(self.health + healing_amount, self.max_health) # Ensure health doesn't exceed max_health

def run_simulation(char_a_params, char_b_params, num_matches=1000, track_health=False):
    wins_a = 0
    wins_b = 0
    TICK_LENGTH = 0.1
    
    # Track health over time if requested
    health_history_a = defaultdict(list)  # tick -> list of health values
    health_history_b = defaultdict(list)  # tick -> list of health values
    
    for _ in range(num_matches):
        a = Character(name="A", **char_a_params)
        b = Character(name="B", **char_b_params)
        
        current_time = 0.0
        tick_count = 0
        
        while a.health > 0 and b.health > 0:
            # Track health at this tick if requested
            if track_health:
                health_history_a[tick_count].append(a.health)
                health_history_b[tick_count].append(b.health)
            
            # Process each character's actions based on their cooldowns
            # Character A
            if a.time_until_attack <= 0:
                damage = a.attack()
                b.health -= damage
                a.time_until_attack = a.attack_cooldown
            
            if a.time_until_heal <= 0 and a.healing > 0:
                a.heal()
                a.time_until_heal = a.healing_cooldown
            
            # Character B
            if b.time_until_attack <= 0:
                damage = b.attack()
                a.health -= damage
                b.time_until_attack = b.attack_cooldown
            
            if b.time_until_heal <= 0 and b.healing > 0:
                b.heal()
                b.time_until_heal = b.healing_cooldown
            
            # Advance time by one tick
            current_time += TICK_LENGTH
            tick_count += 1
            a.time_until_attack -= TICK_LENGTH
            a.time_until_heal -= TICK_LENGTH
            b.time_until_attack -= TICK_LENGTH
            b.time_until_heal -= TICK_LENGTH

        # Award wins only if character has positive health
        # If both are dead (health <= 0), neither gets a point (tie)
        if a.health > b.health and a.health > 0:
            wins_a += 1
        elif b.health > a.health and b.health > 0:
            wins_b += 1
        # If both are dead or equal, it's a tie (no points awarded)
            
    # Calculate win rate: wins_a / (wins_a + wins_b) * 100, excluding ties
    # If there are no decisive matches (all ties), return 50% as neutral
    total_decisive_matches = wins_a + wins_b
    if total_decisive_matches > 0:
        win_rate_a = (wins_a / total_decisive_matches) * 100
    else:
        win_rate_a = 50.0  # All matches were ties, return neutral 50%
    
    if track_health:
        return win_rate_a, health_history_a, health_history_b
    else:
        return win_rate_a

def plot_average_health(char_a_params, char_b_params, num_matches=100):
    """Plot average health of both opponents over all fights."""
    win_rate, health_history_a, health_history_b = run_simulation(
        char_a_params, char_b_params, num_matches, track_health=True
    )
    
    # Calculate average health at each tick
    ticks = sorted(health_history_a.keys())
    avg_health_a = [sum(health_history_a[tick]) / len(health_history_a[tick]) for tick in ticks]
    avg_health_b = [sum(health_history_b[tick]) / len(health_history_b[tick]) for tick in ticks]
    
    # Plot
    plt.figure(figsize=(10, 6))
    plt.plot(ticks, avg_health_a, label='Character A', linewidth=2)
    plt.plot(ticks, avg_health_b, label='Character B', linewidth=2)
    plt.xlabel('Ticks', fontsize=12)
    plt.ylabel('Average Health', fontsize=12)
    plt.title(f'Average Health Over Time (across {num_matches} fights)', fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
    
    return win_rate