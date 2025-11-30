from GameSimulator import run_simulation
from OptimizationAgent import run_optimization_agent
from openai import OpenAI
import os
from dotenv import load_dotenv


if __name__ == "__main__":
    load_dotenv(".env")
    api_key = os.getenv("OPENAI_API_KEY")
    optimization_client = OpenAI(api_key=api_key)
    
    # Initialize parameters for two character archetypes with deliberate imbalance:
    # 1. Healer (Overpowered): High health, good attack, extremely strong healing, reasonable cooldowns
    INITIAL_HEALER_PARAMS = {
        "attack_power": 9,
        "health": 70,
        "healing": 30,                # Excessively high healing
        "attack_cooldown": 1.2,
        "healing_cooldown": 0.5       # Heals very often
    }
    # 2. Attacker: Very high attack, average health for archetype, no healing, fast attack
    INITIAL_ATTACKER_PARAMS = {
        "attack_power": 28,
        "health": 90,
        "healing": 0,
        "attack_cooldown": 0.8,
        "healing_cooldown": 1.0       # not used
    }
    # 1. Simulate initial match
    print(f"--- Initial Healer vs Attacker Simulation ---")
    win_rate = run_simulation(INITIAL_HEALER_PARAMS, INITIAL_ATTACKER_PARAMS)
    if win_rate > 50:
        winner = "Healer"
        winner_rate = win_rate
    else:
        winner = "Attacker"
        winner_rate = 100 - win_rate
    print(f"Healer vs Attacker: Winner: {winner} (Win Rate = {winner_rate:.2f}%)")
    print("-" * 30)

    # 2. Define the Semantic Constraint
    # Defines the essential spirit of each archetype
    semantic_constraint = (
        "Respect the archetype identities when making adjustments: "
        "Healer is defined by robust healing ability, low attack, and moderate health. "
        "Attacker is characterized by high attack power, moderate health, fast attacks, and no healing. "
        "When balancing, DO NOT violate these core archetype principles."
    )

    # Iteratively adjust parameters until all matchups are roughly balanced or max 5 rounds
    max_rounds = 50
    tolerance = 10  # Acceptable deviation from 50%
    round_number = 0

    # Deepcopy to preserve initial params for each archetype
    import copy
    current_healer_params = copy.deepcopy(INITIAL_HEALER_PARAMS)
    current_attacker_params = copy.deepcopy(INITIAL_ATTACKER_PARAMS)
    
    # History buffer to track iterations and changes
    history_buffer = []

    while round_number < max_rounds:
        print(f"\n=== Balancing Round {round_number + 1} ===")
        # Compute imbalance data for the matchup
        win_rate = run_simulation(current_healer_params, current_attacker_params)
        imbalance_data_list = [
            {
                'matchup': 'Healer vs Attacker',
                'win_rate_a': win_rate,
                'character_a': 'Healer',
                'character_b': 'Attacker',
                'character_a_params': current_healer_params.copy(),
                'character_b_params': current_attacker_params.copy(),
            },
        ]

        # Print current win rate and winner name
        if win_rate > 50:
            winner = 'Healer'
            winner_rate = win_rate
        elif win_rate < 50:
            winner = 'Attacker'
            winner_rate = 100 - win_rate
        else:
            winner = 'Tie'
            winner_rate = 50.0
        print(f"Healer vs Attacker: Winner: {winner} (Win Rate = {winner_rate:.2f}%)")

        # Check stopping criteria: win rate within [40%, 60%]
        balanced = 40 <= win_rate <= 60
        if balanced:
            print("Matchup balanced within ±10% of 50%.")
            break

        # Store win rate before changes
        win_rate_before = win_rate

        # 3. Run the design agent once, passing all imbalance data and the constraint
        result = run_optimization_agent(
            optimization_client,
            imbalance_data_list, 
            semantic_constraint,
            history_buffer
        )

        if result:
            decision, fixes = result
            
            # Apply the fixes to update current parameters
            current_healer_params = {
                'attack_power': fixes.healer.attack_power,
                'health': fixes.healer.health,
                'healing': fixes.healer.healing,
                'attack_cooldown': fixes.healer.attack_cooldown,
                'healing_cooldown': fixes.healer.healing_cooldown
            }
            current_attacker_params = {
                'attack_power': fixes.attacker.attack_power,
                'health': fixes.attacker.health,
                'healing': fixes.attacker.healing,
                'attack_cooldown': fixes.attacker.attack_cooldown,
                'healing_cooldown': fixes.attacker.healing_cooldown
            }
            
            # Print decision and proposed changes
            print(f"--- Design Agent Decision and Proposed Changes ---")
            print(f"Decision: {decision.direction} {decision.parameter} for {decision.character}")
            print(f"Decision Rationale: {decision.rationale}")
            print(f"\nProposed Parameters:")
            print("  Healer:", current_healer_params)
            print("  Attacker:", current_attacker_params)
            print(f"\nChange Details:")
            print(f"  Amount: {fixes.amount:.2f} ({fixes.amount_percentage:.2f}%)")
            print(f"\nFull Rationale: {fixes.rationale}")
            print("-" * 30)
            
            # Get win rate after changes
            win_rate_after = run_simulation(current_healer_params, current_attacker_params)
            
            # Append to history buffer
            history_entry = {
                "iteration": round_number + 1,
                "win_rate_before": win_rate_before,
                "win_rate_after": win_rate_after,
                "changes": {
                    "character": decision.character,
                    "parameter": decision.parameter,
                    "direction": decision.direction,
                    "amount": fixes.amount,
                    "amount_percentage": fixes.amount_percentage
                }
            }
            history_buffer.append(history_entry)
        else:
            print("Failed to get fixes from optimization agent.")
            break

        round_number += 1

    print("\n=== Final Archetype Parameters ===")
    print("Healer:", current_healer_params)
    print("Attacker:", current_attacker_params)

    # Final win rate
    print("\n--- Final Balance Check ---")
    final_win_rate = run_simulation(current_healer_params, current_attacker_params)
    print(f"Healer vs Attacker: {final_win_rate:.2f}% win rate for Healer")
    print("-" * 30)