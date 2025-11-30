# Agentic Game Balancing

An automated game balancing system that uses LLM-powered agents to iteratively optimize character parameters in a 1v1 combat game simulation.

## Requirements

### Python Libraries

Install the following Python packages:

```bash
pip install openai
pip install python-dotenv
pip install pydantic
pip install matplotlib
pip install numpy
```

## Setup

### 1. OpenAI API Key

Create a `.env` file in the project root directory with your OpenAI API key:

```
OPENAI_API_KEY=your_api_key_here
```

**Important:** Replace `your_api_key_here` with your actual OpenAI API key. The `.env` file is used to securely load the API key without hardcoding it in the source code.

## Running the System

To start the optimization process, run:

```bash
python run.py
```

This will:
1. Run an initial simulation to assess the current game balance
2. Iteratively optimize character parameters using the LLM-powered optimization agent
3. Continue until the matchup is balanced (win rate within 40-60%) or a maximum iteration limit is reached
4. Display the final balanced parameters

## Project Structure

- `run.py` - Main script that orchestrates the simulation and optimization process
- `GameSimulator.py` - Contains the combat simulation logic and Character class
- `OptimizationAgent.py` - LLM-powered agent that decides and applies parameter changes
- `plot_optimization.py` - Script to visualize optimization progress

