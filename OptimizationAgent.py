from pydantic import BaseModel, Field
import json

# --- Pydantic Schema for individual archetype parameters ---
class ArchetypeParams(BaseModel):
    """Parameters for a single character archetype."""
    attack_power: int = Field(..., description="Attack Power (integer)")
    health: int = Field(..., description="Maximum Health (integer)")
    healing: int = Field(..., description="Healing points per heal (integer, 0 if no healing)")
    attack_cooldown: float = Field(..., description="Attack cooldown time in seconds (float)")
    healing_cooldown: float = Field(..., description="Healing cooldown time in seconds (float)")

# --- Pydantic Schema for parameter change decision ---
class ParameterChangeDecision(BaseModel):
    """Decision about which parameter to change."""
    character: str = Field(..., description="Which character to modify: 'Healer' or 'Attacker'")
    parameter: str = Field(..., description="Which parameter to change: 'attack_power', 'health', 'healing', 'attack_cooldown', or 'healing_cooldown'")
    direction: str = Field(..., description="Direction of change: 'increase' or 'decrease'")
    rationale: str = Field(..., description="Why this specific parameter change will help balance the matchup")

# --- Pydantic Schema (Defines the LLM's structured output) ---
class ProposedFix(BaseModel):
    """A JSON object describing the balancing fixes for both archetypes."""
    healer: ArchetypeParams = Field(..., description="Updated parameters for the Healer archetype")
    attacker: ArchetypeParams = Field(..., description="Updated parameters for the Attacker archetype")
    rationale: str = Field(..., description="The justification for the fixes, explicitly stating how they adhere to the archetype constraints.")
    amount: float = Field(..., description="The amount by which the parameter was changed (absolute value)")
    amount_percentage: float = Field(..., description="The percentage change of the parameter (relative to original value)")

# --- Step 1: Decide which parameter to change ---
def decide_parameter_change(client, imbalance_data_list, constraint, current_healer_params, current_attacker_params, history_buffer=None):
    """First step: Decide which single parameter of which character should be changed."""
    
    system_prompt = (
        "You are an expert game design analyst. Your task is to analyze imbalance data and decide "
        "which SINGLE parameter of which character should be changed to improve balance. "
        "You must choose ONE character and ONE parameter to modify. Output your decision in JSON format."
    )
    
    # Show both win rates explicitly for clarity
    matchup_info = ""
    for data in imbalance_data_list:
        win_rate_a = data['win_rate_a']
        win_rate_b = 100 - win_rate_a
        matchup_info += f"  - {data['matchup']}: {data['character_a']} Win Rate = {win_rate_a:.2f}%, {data['character_b']} Win Rate = {win_rate_b:.2f}%\n"
    
    history_section = ""
    if history_buffer:
        import json as json_module
        history_section = f"""
    
    PREVIOUS ITERATIONS HISTORY:
    {json_module.dumps(history_buffer, indent=2)}
    
    Use this history to avoid repeating ineffective changes and to learn from what worked or didn't work.
    """
    
    user_prompt = f"""
    COMBAT SIMULATOR MECHANICS:
    The combat system works as follows:
    - Time advances in discrete ticks of 0.1 seconds each
    - When a character's attack cooldown expires (after X seconds = X * 10 ticks), they perform an attack
    - Attack: damage = attack_power (with randomness: ±20 damage variance, 15% miss chance, 15% crit chance for 2x damage)
    - Attack damage is SUBTRACTED from the opponent's current health
    - When a character's healing cooldown expires (if healing > 0), they perform a heal
    - Heal: health += healing (with ±40% variance in healing amount)
    - Healing cannot exceed max_health (the character's starting health value)
    - The fight continues until one character's health drops to 0 or below
    - If both characters die (health <= 0), it's a tie (no winner)
    - Cooldowns are measured in seconds (e.g., 1.2 seconds = 12 ticks of 0.1s each)
    - Lower cooldown = more frequent actions = higher damage/healing output per second
    - Example: attack_cooldown=0.8s means attacking every 8 ticks, attack_cooldown=1.2s means attacking every 12 ticks

    IMBALANCE REPORT (Current Win Rates):
{matchup_info}
    CURRENT ARCHETYPE PARAMETERS:
    Healer: attack_power={current_healer_params['attack_power']}, health={current_healer_params['health']}, 
            healing={current_healer_params['healing']}, attack_cooldown={current_healer_params['attack_cooldown']}, 
            healing_cooldown={current_healer_params['healing_cooldown']}
    
    Attacker: attack_power={current_attacker_params['attack_power']}, health={current_attacker_params['health']}, 
              healing={current_attacker_params['healing']}, attack_cooldown={current_attacker_params['attack_cooldown']}, 
              healing_cooldown={current_attacker_params['healing_cooldown']}
{history_section}
    DESIGN CONSTRAINT:
    {constraint}

    TASK: Decide which SINGLE parameter of which character should be changed to improve balance.
    Choose ONE of: 'Healer' or 'Attacker'
    Choose ONE parameter: 'attack_power', 'health', 'healing', 'attack_cooldown', or 'healing_cooldown'
    Choose direction: 'increase' or 'decrease'
    
    Output JSON format:
    {{"character": "Healer|Attacker", "parameter": "parameter_name", "direction": "increase|decrease", "rationale": "explanation"}}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        response_content = response.choices[0].message.content
        response_json = json.loads(response_content)
        decision = ParameterChangeDecision(**response_json)
        return decision
    except Exception as e:
        print(f"Error in decide_parameter_change: {e}")
        return None

# --- Step 2: Apply the parameter change ---
def apply_parameter_change(client, decision, constraint, current_healer_params, current_attacker_params):
    """Second step: Apply the parameter change according to constraints."""
    
    system_prompt = (
        "You are an expert game designer. Your task is to apply a specific parameter change "
        "while STRICTLY adhering to all parameter constraints and design constraints. "
        "You must output the complete parameter set for both archetypes with the requested change applied."
    )
    
    # Get current value of the parameter to change
    character_params = {
        'Healer': current_healer_params,
        'Attacker': current_attacker_params
    }
    target_params = character_params[decision.character]
    current_value = target_params[decision.parameter]
    
    user_prompt = f"""
    COMBAT SIMULATOR MECHANICS:
    The combat system works as follows:
    - Time advances in discrete ticks of 0.1 seconds each
    - When a character's attack cooldown expires (after X seconds = X * 10 ticks), they perform an attack
    - Attack: damage = attack_power (with randomness: ±20 damage variance, 15% miss chance, 15% crit chance for 2x damage)
    - Attack damage is SUBTRACTED from the opponent's current health
    - When a character's healing cooldown expires (if healing > 0), they perform a heal
    - Heal: health += healing (with ±40% variance in healing amount)
    - Healing cannot exceed max_health (the character's starting health value)
    - The fight continues until one character's health drops to 0 or below
    - If both characters die (health <= 0), it's a tie (no winner)
    - Cooldowns are measured in seconds (e.g., 1.2 seconds = 12 ticks of 0.1s each)
    - Lower cooldown = more frequent actions = higher damage/healing output per second
    - Example: attack_cooldown=0.8s means attacking every 8 ticks, attack_cooldown=1.2s means attacking every 12 ticks

    PARAMETER CHANGE REQUEST:
    Character: {decision.character}
    Parameter: {decision.parameter}
    Current Value: {current_value}
    Direction: {decision.direction}
    Rationale: {decision.rationale}

    CURRENT ARCHETYPE PARAMETERS:
    Healer: attack_power={current_healer_params['attack_power']}, health={current_healer_params['health']}, 
            healing={current_healer_params['healing']}, attack_cooldown={current_healer_params['attack_cooldown']}, 
            healing_cooldown={current_healer_params['healing_cooldown']}
    
    Attacker: attack_power={current_attacker_params['attack_power']}, health={current_attacker_params['health']}, 
              healing={current_attacker_params['healing']}, attack_cooldown={current_attacker_params['attack_cooldown']}, 
              healing_cooldown={current_attacker_params['healing_cooldown']}

    DESIGN CONSTRAINT (MUST FOLLOW):
    {constraint}

    PARAMETER CONSTRAINTS (CRITICAL - MUST ENFORCE):
    1. NO ONE-SHOT KILLS: Attack power must be significantly less than opponent's health. 
       For example, if fighting an opponent with 100 health, attack_power should be at most 30-40.
       This ensures fights last multiple rounds and skill matters.
    
    2. HEALING LIMITS: Healing amount should be significantly below health (typically 20-50% of health).
       Healing should not be so powerful that it can fully restore health in one or two heals.
       This prevents healing from making characters nearly invincible.
    
    3. REASONABLE COOLDOWNS: Attack and healing cooldowns should be between 0.5 and 3.0 seconds.
       Too fast (<0.5s) makes combat chaotic, too slow (>3.0s) makes it feel sluggish.
    
    4. INCREMENTAL CHANGES: Make small adjustments (typically 5-15% changes to parameters).
       Do not make drastic changes. This is iterative optimization - gradual improvement is expected.

    TASK: Apply the requested change ({decision.direction} {decision.parameter} for {decision.character}) 
    with a small incremental adjustment (5-15% change), while ensuring ALL constraints are met.
    
    Output the complete parameter set for both archetypes in JSON format:
    {{"healer": {{"attack_power": int, "health": int, "healing": int, "attack_cooldown": float, "healing_cooldown": float}}, 
     "attacker": {{"attack_power": int, "health": int, "healing": int, "attack_cooldown": float, "healing_cooldown": float}}, 
     "rationale": "explanation of the change and how it respects constraints",
     "amount": float,
     "amount_percentage": float}}
    
    IMPORTANT: Calculate and include "amount" (absolute change) and "amount_percentage" (percentage change) 
    for the parameter that was changed. For example, if attack_power changed from 10 to 12, 
    amount=2.0 and amount_percentage=20.0 (20% increase).
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        response_content = response.choices[0].message.content
        response_json = json.loads(response_content)
        
        # Calculate amount and amount_percentage
        if decision.character == 'Healer':
            new_value = response_json['healer'][decision.parameter]
        else:
            new_value = response_json['attacker'][decision.parameter]
        
        amount = abs(new_value - current_value)
        if current_value != 0:
            amount_percentage = (amount / current_value) * 100
        else:
            amount_percentage = 0.0 if amount == 0 else 100.0
        
        # Add amount and amount_percentage to response
        response_json['amount'] = amount
        response_json['amount_percentage'] = amount_percentage
        
        proposed_fix = ProposedFix(**response_json)
        return proposed_fix
    except Exception as e:
        print(f"Error in apply_parameter_change: {e}")
        return None

# --- Main Optimization Agent Function ---
def run_optimization_agent(client, imbalance_data_list, constraint, history_buffer=None):
    # Extract current parameters from imbalance_data_list
    # Find unique archetype parameters from the matchups
    archetype_params = {}
    for data in imbalance_data_list:
        char_a = data['character_a']
        char_b = data['character_b']
        if char_a not in archetype_params:
            archetype_params[char_a] = data['character_a_params']
        if char_b not in archetype_params:
            archetype_params[char_b] = data['character_b_params']
    
    current_healer_params = archetype_params.get('Healer', {})
    current_attacker_params = archetype_params.get('Attacker', {})
    
    # Step 1: Decide which parameter to change
    decision = decide_parameter_change(
        client, imbalance_data_list, constraint,
        current_healer_params, current_attacker_params,
        history_buffer
    )
    
    if not decision:
        print("Failed to get parameter change decision.")
        return None
    
    # Step 2: Apply the parameter change
    proposed_fix = apply_parameter_change(
        client, decision, constraint,
        current_healer_params, current_attacker_params
    )
    
    if not proposed_fix:
        return None
    
    # Return both the decision and the fix
    return decision, proposed_fix