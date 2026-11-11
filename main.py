"""
UAV Target Tracking 2D Simulation - Main Entry Point.

Usage:
    python main.py                    # GUI mode (default)
    python main.py --mode gui         # GUI mode
    python main.py --mode headless    # Headless mode (run default scenario)
    python main.py --config config.yaml
"""

import sys
import os
import argparse
import yaml
import json
import numpy as np

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def load_config(path: str = None) -> dict:
    """Load configuration from YAML file."""
    if path is None:
        path = os.path.join(PROJECT_ROOT, 'config.yaml')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def run_gui(config: dict):
    """Launch Pygame GUI dashboard."""
    from interface.dashboard import Dashboard
    dashboard = Dashboard(config)
    dashboard.run()


def run_headless(config: dict, scenario_id: int = 1, filter_mode: str = 'both',
                  seed: int = 42, output_dir: str = None):
    """Run simulation without GUI."""
    from simulation.simulation_engine import SimulationEngine
    from simulation.target_scenario import get_scenario_config
    from evaluation.estimation_evaluation import EstimationEvaluator
    from evaluation.tracking_evaluation import TrackingEvaluator

    config['simulation'] = config.get('simulation', {})
    config['simulation']['random_seed'] = seed
    config['filter'] = config.get('filter', {})
    config['filter']['selected'] = filter_mode

    engine = SimulationEngine(config)
    scfg = get_scenario_config(scenario_id)
    engine.setup(scfg)
    engine.filter_mode = filter_mode

    print(f"Running Scenario {scenario_id}: {scfg['name']} | Filter: {filter_mode} | Seed: {seed}")

    # Run
    est_eval = EstimationEvaluator()
    track_eval = TrackingEvaluator(config.get('pid', {}).get('desired_distance', 50.0))

    history = engine.run_headless()

    for step in history:
        est_eval.add_step(step)
        track_eval.add_step(step)

    # Compute metrics
    metrics = engine.compute_metrics()
    metrics.update(est_eval.compute_metrics())
    metrics.update(track_eval.compute_metrics())

    # Save
    if output_dir is None:
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(PROJECT_ROOT, "results", "data",
                                   f"scenario_{scenario_id:02d}", f"run_{ts}")

    os.makedirs(output_dir, exist_ok=True)
    engine.save_results(output_dir)
    engine.save_metrics(output_dir, metrics)

    # Print summary
    print(f"\n{'='*50}")
    print(f"Scenario: {scfg['name']}")
    print(f"Filter: {filter_mode} | Seed: {seed}")
    print(f"Duration: {engine.time:.1f}s | Steps: {engine.step_count}")
    print(f"{'='*50}")
    for k, v in metrics.items():
        if isinstance(v, (int, float)):
            print(f"  {k}: {v:.4f}")
        elif v is not None and not isinstance(v, dict):
            print(f"  {k}: {v}")
    print(f"\nResults saved to: {output_dir}")

    return metrics


def main():
    parser = argparse.ArgumentParser(description="UAV Target Tracking 2D Simulation")
    parser.add_argument('--mode', choices=['gui', 'headless'], default='gui',
                        help='Run mode: gui (Pygame) or headless (no GUI)')
    parser.add_argument('--config', default=None, help='Path to config YAML file')
    parser.add_argument('--scenario', type=int, default=1, help='Scenario ID (1-12) for headless')
    parser.add_argument('--filter', choices=['ekf', 'ukf', 'both'], default='both',
                        help='Filter selection')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--output', default=None, help='Output directory for results')
    args = parser.parse_args()

    config = load_config(args.config)

    if args.mode == 'gui':
        run_gui(config)
    elif args.mode == 'headless':
        run_headless(config, args.scenario, args.filter, args.seed, args.output)


if __name__ == "__main__":
    main()
