"""
Batch Experiment Runner.

Supports:
- GUI mode: Tkinter-based batch runner interface
- Headless mode: CLI-based batch execution

Runs multiple scenarios, seeds, and filter configurations.
Saves results, metrics, and summary CSV.
"""

import sys
import os
import argparse
import json
import csv
import time
import datetime
import yaml
import copy
import numpy as np
from typing import List, Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from simulation.simulation_engine import SimulationEngine
from simulation.target_scenario import get_scenario_config, get_all_scenario_names
from evaluation.estimation_evaluation import EstimationEvaluator
from evaluation.tracking_evaluation import TrackingEvaluator


def load_config(path: str = None) -> dict:
    if path is None:
        path = os.path.join(PROJECT_ROOT, 'config.yaml')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def run_single_experiment(config: dict, scenario_id: int, filter_mode: str,
                           seed: int, output_dir: str) -> Dict[str, Any]:
    """Run a single experiment and save results."""
    config = copy.deepcopy(config)
    config['simulation'] = config.get('simulation', {})
    config['simulation']['random_seed'] = seed
    config['filter'] = config.get('filter', {})
    config['filter']['selected'] = filter_mode

    engine = SimulationEngine(config)
    scfg = get_scenario_config(scenario_id)
    engine.setup(scfg)
    engine.filter_mode = filter_mode

    est_eval = EstimationEvaluator()
    track_eval = TrackingEvaluator(config.get('pid', {}).get('desired_distance', 50.0))

    history = engine.run_headless()

    for step in history:
        est_eval.add_step(step)
        track_eval.add_step(step)

    metrics = engine.compute_metrics()
    metrics.update(est_eval.compute_metrics())
    metrics.update(track_eval.compute_metrics())
    metrics['scenario_id'] = scenario_id
    metrics['scenario_name'] = scfg['name']
    metrics['filter_mode'] = filter_mode
    metrics['seed'] = seed
    metrics['duration'] = engine.time
    metrics['steps'] = engine.step_count

    os.makedirs(output_dir, exist_ok=True)
    engine.save_results(output_dir)
    engine.save_metrics(output_dir, metrics)

    return metrics


def run_batch_headless(config: dict, scenarios: List[int], filters: List[str],
                        seeds: List[int], base_output: str = None):
    """Run batch experiments in headless mode."""
    if base_output is None:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_output = os.path.join(PROJECT_ROOT, "results", "data", f"batch_{ts}")

    os.makedirs(base_output, exist_ok=True)
    all_scenarios = get_all_scenario_names()

    total = len(scenarios) * len(filters) * len(seeds)
    print(f"\n{'='*60}")
    print(f"BATCH EXPERIMENT RUNNER")
    print(f"Scenarios: {scenarios}")
    print(f"Filters: {filters}")
    print(f"Seeds: {seeds}")
    print(f"Total runs: {total}")
    print(f"Output: {base_output}")
    print(f"{'='*60}\n")

    all_metrics = []
    run_count = 0
    failed = 0

    # Status tracking
    status_file = os.path.join(base_output, "batch_status.json")

    for sc_id in scenarios:
        sc_name = all_scenarios.get(sc_id, f"scenario_{sc_id}")
        for filt in filters:
            for seed in seeds:
                run_count += 1
                run_id = f"s{sc_id}_{filt}_seed{seed}"
                run_dir = os.path.join(base_output, f"scenario_{sc_id:02d}_{sc_name.replace(' ', '_').lower()}", run_id)

                # Skip if already completed
                metrics_file = os.path.join(run_dir, "metrics.json")
                if os.path.exists(metrics_file):
                    print(f"[{run_count}/{total}] SKIP (exists): {run_id}")
                    with open(metrics_file, 'r') as f:
                        m = json.load(f)
                    all_metrics.append(m)
                    continue

                print(f"[{run_count}/{total}] Running: Scenario {sc_id} | {filt} | seed={seed} ... ", end="", flush=True)
                t0 = time.time()

                try:
                    metrics = run_single_experiment(config, sc_id, filt, seed, run_dir)
                    all_metrics.append(metrics)
                    elapsed = time.time() - t0
                    ekf_rmse = metrics.get('ekf_position_rmse', 'N/A')
                    ukf_rmse = metrics.get('ukf_position_rmse', 'N/A')
                    track_rmse = metrics.get('tracking_rmse', 'N/A')
                    print(f"OK ({elapsed:.1f}s) | EKF={ekf_rmse:.2f} UKF={ukf_rmse:.2f} Track={track_rmse:.2f}" if isinstance(ekf_rmse, float) else f"OK ({elapsed:.1f}s)")
                except Exception as e:
                    failed += 1
                    print(f"FAILED: {e}")
                    all_metrics.append({
                        'scenario_id': sc_id, 'filter_mode': filt, 'seed': seed,
                        'status': 'failed', 'error': str(e)
                    })

                # Update status
                status = {
                    'total': total, 'completed': run_count - failed,
                    'failed': failed, 'remaining': total - run_count,
                }
                with open(status_file, 'w') as f:
                    json.dump(status, f, indent=2)

    # Summary CSV
    summary_path = os.path.join(base_output, "summary.csv")
    if all_metrics:
        keys = set()
        for m in all_metrics:
            keys.update(k for k, v in m.items() if isinstance(v, (int, float, str, type(None))))
        keys = sorted(keys)

        with open(summary_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            for m in all_metrics:
                row = {k: v for k, v in m.items() if isinstance(v, (int, float, str, type(None)))}
                writer.writerow(row)

    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {run_count - failed}/{total} succeeded, {failed} failed")
    print(f"Summary: {summary_path}")
    print(f"Results: {base_output}")
    print(f"{'='*60}")

    return all_metrics


def run_batch_gui(config: dict):
    """Run batch runner with Tkinter GUI."""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog
    except ImportError:
        print("Tkinter not available. Use --headless mode.")
        return

    root = tk.Tk()
    root.title("UAV Tracking - Batch Experiment Runner")
    root.geometry("700x650")
    root.configure(bg='#1a1c24')

    style = ttk.Style()
    style.theme_use('clam')

    main_frame = ttk.Frame(root, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Scenarios
    ttk.Label(main_frame, text="Scenarios:").grid(row=0, column=0, sticky=tk.W, pady=5)
    scenario_vars = {}
    sc_frame = ttk.Frame(main_frame)
    sc_frame.grid(row=0, column=1, sticky=tk.W)
    for sc_id, sc_name in get_all_scenario_names().items():
        var = tk.BooleanVar(value=True)
        scenario_vars[sc_id] = var
        ttk.Checkbutton(sc_frame, text=f"{sc_id}. {sc_name}", variable=var).pack(anchor=tk.W)

    # Filters
    ttk.Label(main_frame, text="Filters:").grid(row=1, column=0, sticky=tk.W, pady=5)
    filter_frame = ttk.Frame(main_frame)
    filter_frame.grid(row=1, column=1, sticky=tk.W)
    filter_vars = {}
    for f in ['ekf', 'ukf', 'both']:
        var = tk.BooleanVar(value=(f == 'both'))
        filter_vars[f] = var
        ttk.Checkbutton(filter_frame, text=f.upper(), variable=var).pack(side=tk.LEFT, padx=5)

    # Seeds
    ttk.Label(main_frame, text="Seeds:").grid(row=2, column=0, sticky=tk.W, pady=5)
    seed_entry = ttk.Entry(main_frame, width=40)
    seed_entry.insert(0, "42, 123, 456, 789, 1000")
    seed_entry.grid(row=2, column=1, sticky=tk.W)

    # Num runs
    ttk.Label(main_frame, text="Runs per config:").grid(row=3, column=0, sticky=tk.W, pady=5)
    runs_spin = ttk.Spinbox(main_frame, from_=1, to=100, width=10)
    runs_spin.set(1)
    runs_spin.grid(row=3, column=1, sticky=tk.W)

    # Progress
    progress_var = tk.DoubleVar()
    progress = ttk.Progressbar(main_frame, variable=progress_var, maximum=100)
    progress.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=10)

    status_label = ttk.Label(main_frame, text="Ready")
    status_label.grid(row=6, column=0, columnspan=2, sticky=tk.W)

    # Log
    log_text = tk.Text(main_frame, height=15, width=80, bg='#0d0e14', fg='#c8d0dc',
                        font=('Consolas', 10))
    log_text.grid(row=7, column=0, columnspan=2, sticky=tk.NSEW, pady=5)
    main_frame.rowconfigure(7, weight=1)

    def log(msg):
        log_text.insert(tk.END, msg + "\n")
        log_text.see(tk.END)
        root.update_idletasks()

    def run_all():
        scenarios = [sc_id for sc_id, var in scenario_vars.items() if var.get()]
        filters = [f for f, var in filter_vars.items() if var.get()]
        try:
            seeds = [int(s.strip()) for s in seed_entry.get().split(',') if s.strip()]
        except ValueError:
            messagebox.showerror("Error", "Invalid seed values")
            return

        if not scenarios or not filters or not seeds:
            messagebox.showwarning("Warning", "Select at least one scenario, filter, and seed")
            return

        total = len(scenarios) * len(filters) * len(seeds)
        log(f"Starting {total} experiments...")
        status_label.config(text=f"Running 0/{total}")

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_output = os.path.join(PROJECT_ROOT, "results", "data", f"batch_{ts}")

        count = 0
        for sc_id in scenarios:
            for filt in filters:
                for seed in seeds:
                    count += 1
                    run_id = f"s{sc_id}_{filt}_seed{seed}"
                    run_dir = os.path.join(base_output, f"scenario_{sc_id:02d}", run_id)
                    status_label.config(text=f"Running {count}/{total}: {run_id}")
                    progress_var.set(count / total * 100)
                    root.update_idletasks()

                    try:
                        metrics = run_single_experiment(config, sc_id, filt, seed, run_dir)
                        ekf_r = metrics.get('ekf_position_rmse', 'N/A')
                        ukf_r = metrics.get('ukf_position_rmse', 'N/A')
                        log(f"[{count}/{total}] {run_id}: OK | EKF_RMSE={ekf_r:.2f} UKF_RMSE={ukf_r:.2f}" if isinstance(ekf_r, float) else f"[{count}/{total}] {run_id}: OK")
                    except Exception as e:
                        log(f"[{count}/{total}] {run_id}: FAILED - {e}")

        progress_var.set(100)
        status_label.config(text=f"Complete: {count} experiments")
        log(f"\nResults saved to: {base_output}")
        messagebox.showinfo("Complete", f"Batch complete!\nResults: {base_output}")

    # Buttons
    btn_frame = ttk.Frame(main_frame)
    btn_frame.grid(row=4, column=0, columnspan=2, pady=5)
    ttk.Button(btn_frame, text="RUN ALL", command=run_all).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Close", command=root.destroy).pack(side=tk.LEFT, padx=5)

    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Batch Experiment Runner")
    parser.add_argument('--mode', choices=['gui', 'headless'], default='gui')
    parser.add_argument('--config', default=None)
    parser.add_argument('--scenarios', default='1,2,3,4,5,6,7,8,9,10,11,12',
                        help='Comma-separated scenario IDs')
    parser.add_argument('--filters', default='both', help='Comma-separated: ekf,ukf,both')
    parser.add_argument('--seeds', default='42,123,456', help='Comma-separated seeds')
    parser.add_argument('--output', default=None)
    parser.add_argument('--headless', action='store_true', help='Force headless mode')
    args = parser.parse_args()

    config = load_config(args.config)

    if args.headless or args.mode == 'headless':
        scenarios = [int(s) for s in args.scenarios.split(',')]
        filters = [f.strip() for f in args.filters.split(',')]
        seeds = [int(s) for s in args.seeds.split(',')]
        run_batch_headless(config, scenarios, filters, seeds, args.output)
    else:
        run_batch_gui(config)


if __name__ == "__main__":
    main()
