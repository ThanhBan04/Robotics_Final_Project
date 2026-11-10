"""
Plotting and Visualization Tool for Simulation Results.

Generates professional publication-quality figures from simulation data:
1. 2D Trajectory (Ground Truth, UAV, EKF, UKF, Measurements)
2. Estimation Errors over Time (EKF vs UKF Position & Velocity Error)
3. Tracking Distance & Error over Time (Desired vs Actual, Settling Time)
4. Dropout Recovery Analysis (Prediction-only behavior during sensor loss)
"""

import os
import sys
import glob
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Set style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8


def plot_simulation_run(run_dir: str, save_dir: str = None):
    """
    Generate all evaluation plots from a single simulation run directory.
    
    Args:
        run_dir: Path to directory containing data.csv and metrics.json
        save_dir: Path to save generated plots (defaults to run_dir/plots)
    """
    csv_path = os.path.join(run_dir, "data.csv")
    metrics_path = os.path.join(run_dir, "metrics.json")
    
    if not os.path.exists(csv_path):
        print(f"[ERROR] data.csv not found in {run_dir}")
        return
        
    df = pd.read_csv(csv_path)
    metrics = {}
    if os.path.exists(metrics_path):
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)

    if save_dir is None:
        save_dir = os.path.join(run_dir, "plots")
    os.makedirs(save_dir, exist_ok=True)
    
    # -------------------------------------------------------------
    # 1. 2D Trajectory Plot
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 7), dpi=150)
    ax.plot(df['target_x'], df['target_y'], 'k-', label='Target Ground Truth', linewidth=2.0, alpha=0.9)
    ax.plot(df['uav_x'], df['uav_y'], 'b--', label='UAV Trajectory', linewidth=1.8, alpha=0.8)
    
    if 'ekf_x' in df and df['ekf_x'].notna().any():
        ax.plot(df['ekf_x'], df['ekf_y'], color='orange', linestyle=':', label='EKF Estimate', linewidth=1.5, alpha=0.85)
    if 'ukf_x' in df and df['ukf_x'].notna().any():
        ax.plot(df['ukf_x'], df['ukf_y'], color='purple', linestyle='-.', label='UKF Estimate', linewidth=1.5, alpha=0.85)
        
    # Mark start & end
    ax.scatter(df['target_x'].iloc[0], df['target_y'].iloc[0], color='green', marker='o', s=80, label='Start', zorder=5)
    ax.scatter(df['target_x'].iloc[-1], df['target_y'].iloc[-1], color='red', marker='x', s=80, label='End', zorder=5)
    
    ax.set_title("2D Target Tracking Trajectory", fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel("X Position (m)", fontsize=11)
    ax.set_ylabel("Y Position (m)", fontsize=11)
    ax.legend(loc='best', frameon=True, framealpha=0.9)
    ax.axis('equal')
    ax.grid(True, linestyle='--', alpha=0.6)
    
    traj_path = os.path.join(save_dir, "trajectory_2d.png")
    fig.tight_layout()
    fig.savefig(traj_path)
    plt.close(fig)
    print(f"[OK] Saved: {traj_path}")

    # -------------------------------------------------------------
    # 2. Estimation Errors (EKF vs UKF)
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), dpi=150, sharex=True)
    
    if 'estimation_error_ekf' in df and df['estimation_error_ekf'].notna().any():
        ekf_rmse = metrics.get('ekf_position_rmse', df['estimation_error_ekf'].mean())
        ax1.plot(df['time'], df['estimation_error_ekf'], color='orange', label=f"EKF (RMSE={ekf_rmse:.2f} m)", linewidth=1.5)
    if 'estimation_error_ukf' in df and df['estimation_error_ukf'].notna().any():
        ukf_rmse = metrics.get('ukf_position_rmse', df['estimation_error_ukf'].mean())
        ax1.plot(df['time'], df['estimation_error_ukf'], color='purple', label=f"UKF (RMSE={ukf_rmse:.2f} m)", linewidth=1.5)
        
    ax1.set_title("Target Estimation Position Error over Time", fontsize=13, fontweight='bold')
    ax1.set_ylabel("Position Error (m)", fontsize=11)
    ax1.legend(loc='upper right', frameon=True)
    ax1.grid(True, linestyle='--', alpha=0.6)
    
    # Velocity errors
    if 'ekf_vx' in df and df['ekf_vx'].notna().any():
        ekf_v_err = np.sqrt((df['ekf_vx'] - df['target_vx'])**2 + (df['ekf_vy'] - df['target_vy'])**2)
        ax2.plot(df['time'], ekf_v_err, color='orange', label="EKF Velocity Error", linewidth=1.5)
    if 'ukf_vx' in df and df['ukf_vx'].notna().any():
        ukf_v_err = np.sqrt((df['ukf_vx'] - df['target_vx'])**2 + (df['ukf_vy'] - df['target_vy'])**2)
        ax2.plot(df['time'], ukf_v_err, color='purple', label="UKF Velocity Error", linewidth=1.5)
        
    ax2.set_title("Velocity Estimation Error over Time", fontsize=13, fontweight='bold')
    ax2.set_xlabel("Time (s)", fontsize=11)
    ax2.set_ylabel("Velocity Error (m/s)", fontsize=11)
    ax2.legend(loc='upper right', frameon=True)
    ax2.grid(True, linestyle='--', alpha=0.6)
    
    err_path = os.path.join(save_dir, "estimation_errors.png")
    fig.tight_layout()
    fig.savefig(err_path)
    plt.close(fig)
    print(f"[OK] Saved: {err_path}")

    # -------------------------------------------------------------
    # 3. Tracking Distance & Error
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    desired_dist = metrics.get('desired_distance', 50.0)
    
    ax.plot(df['time'], df['tracking_distance'], color='blue', label='Actual Distance', linewidth=1.8)
    ax.axhline(desired_dist, color='red', linestyle='--', label=f'Desired Distance ({desired_dist:.0f} m)', linewidth=1.5)
    ax.fill_between(df['time'], desired_dist * 0.85, desired_dist * 1.15, color='green', alpha=0.15, label='Success Zone (±15%)')
    
    settling_time = metrics.get('settling_time', None)
    if settling_time and settling_time > 0:
        ax.axvline(settling_time, color='darkgreen', linestyle=':', label=f'Settling Time ({settling_time:.2f} s)')
        
    ax.set_title("UAV-to-Target Following Distance", fontsize=13, fontweight='bold', pad=10)
    ax.set_xlabel("Time (s)", fontsize=11)
    ax.set_ylabel("Distance (m)", fontsize=11)
    ax.legend(loc='best', frameon=True)
    ax.grid(True, linestyle='--', alpha=0.6)
    
    track_path = os.path.join(save_dir, "tracking_distance.png")
    fig.tight_layout()
    fig.savefig(track_path)
    plt.close(fig)
    print(f"[OK] Saved: {track_path}")

    # -------------------------------------------------------------
    # 4. Camera Status & Dropout Shading (if any dropout occurred)
    # -------------------------------------------------------------
    if (df['measurement_detected'] == 0).any():
        fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
        ax.plot(df['time'], df['estimation_error_ekf'], color='orange', label='EKF Error (m)', linewidth=1.5)
        if 'estimation_error_ukf' in df and df['estimation_error_ukf'].notna().any():
            ax.plot(df['time'], df['estimation_error_ukf'], color='purple', label='UKF Error (m)', linewidth=1.5)
            
        # Highlight dropout intervals
        dropout_mask = df['measurement_detected'] == 0
        diff = np.diff(np.pad(dropout_mask.astype(int), (1, 1), 'constant'))
        starts = df['time'].iloc[np.where(diff == 1)[0]].values
        ends = df['time'].iloc[np.where(diff == -1)[0] - 1].values
        
        for s, e in zip(starts, ends):
            ax.axvspan(s, e, color='red', alpha=0.25, label='Sensor Dropout (Prediction Only)' if s == starts[0] else "")
            
        ax.set_title("Filter Robustness during Camera Dropout", fontsize=13, fontweight='bold')
        ax.set_xlabel("Time (s)", fontsize=11)
        ax.set_ylabel("Position Error (m)", fontsize=11)
        ax.legend(loc='upper right', frameon=True)
        ax.grid(True, linestyle='--', alpha=0.6)
        
        drop_path = os.path.join(save_dir, "dropout_recovery.png")
        fig.tight_layout()
        fig.savefig(drop_path)
        plt.close(fig)
        print(f"[OK] Saved: {drop_path}")

    # -------------------------------------------------------------
    # 5. Error Distribution (Histogram, KDE, Boxplot)
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=150)
    
    # Histogram of estimation errors
    has_ekf = 'estimation_error_ekf' in df and df['estimation_error_ekf'].notna().any()
    has_ukf = 'estimation_error_ukf' in df and df['estimation_error_ukf'].notna().any()
    
    if has_ekf:
        ekf_err = df['estimation_error_ekf'].dropna()
        ax1.hist(ekf_err, bins=30, density=True, alpha=0.55, color='orange', label=f"EKF (Mean={ekf_err.mean():.2f}m, Std={ekf_err.std():.2f}m)")
    if has_ukf:
        ukf_err = df['estimation_error_ukf'].dropna()
        ax1.hist(ukf_err, bins=30, density=True, alpha=0.55, color='purple', label=f"UKF (Mean={ukf_err.mean():.2f}m, Std={ukf_err.std():.2f}m)")
        
    ax1.set_title("Estimation Error Distribution", fontsize=13, fontweight='bold')
    ax1.set_xlabel("Position Error (m)", fontsize=11)
    ax1.set_ylabel("Probability Density", fontsize=11)
    ax1.legend(loc='upper right', frameon=True)
    ax1.grid(True, linestyle='--', alpha=0.6)
    
    # Boxplot comparison
    box_data = []
    box_labels = []
    if has_ekf:
        box_data.append(ekf_err)
        box_labels.append("EKF")
    if has_ukf:
        box_data.append(ukf_err)
        box_labels.append("UKF")
        
    # Also add tracking error
    track_err = np.abs(df['tracking_distance'] - desired_dist).dropna()
    box_data.append(track_err)
    box_labels.append("Tracking Error")
    
    try:
        bplot = ax2.boxplot(box_data, patch_artist=True, tick_labels=box_labels)
    except TypeError:
        bplot = ax2.boxplot(box_data, patch_artist=True, labels=box_labels)
    colors = ['#ffcc80', '#e1bee7', '#90caf9']
    for patch, color in zip(bplot['boxes'], colors[:len(box_data)]):
        patch.set_facecolor(color)
        
    ax2.set_title("Error Statistical Spread (Boxplot)", fontsize=13, fontweight='bold')
    ax2.set_ylabel("Error Magnitude (m)", fontsize=11)
    ax2.grid(True, linestyle='--', alpha=0.6)
    
    dist_path = os.path.join(save_dir, "error_distribution.png")
    fig.tight_layout()
    fig.savefig(dist_path)
    plt.close(fig)
    print(f"[OK] Saved: {dist_path}")

    # -------------------------------------------------------------
    # 6. Detailed 2D Trajectory with Timestamps & Tracking Lines
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 8), dpi=150)
    ax.plot(df['target_x'], df['target_y'], 'k-', label='Target Path (Ground Truth)', linewidth=2.2, zorder=3)
    ax.plot(df['uav_x'], df['uav_y'], 'b--', label='UAV Path', linewidth=1.8, zorder=3)
    
    # Mark positions at periodic timestamps (every 5 seconds)
    total_time = df['time'].max()
    sample_times = np.arange(0, total_time + 0.1, 5.0)
    for t_mark in sample_times:
        idx = (df['time'] - t_mark).abs().idxmin()
        tx, ty = df.loc[idx, 'target_x'], df.loc[idx, 'target_y']
        ux, uy = df.loc[idx, 'uav_x'], df.loc[idx, 'uav_y']
        # Distance line connecting UAV and target at t_mark
        ax.plot([tx, ux], [ty, uy], color='gray', linestyle=':', alpha=0.7, linewidth=1.0)
        ax.scatter(tx, ty, color='black', s=35, zorder=4)
        ax.scatter(ux, uy, color='blue', s=35, zorder=4)
        ax.annotate(f"t={t_mark:.0f}s", (tx, ty), textcoords="offset points", xytext=(6, 6), fontsize=8, color='#333333')
        
    # Mark start & end
    ax.scatter(df['target_x'].iloc[0], df['target_y'].iloc[0], color='green', marker='o', s=100, label='Start (t=0s)', zorder=6)
    ax.scatter(df['target_x'].iloc[-1], df['target_y'].iloc[-1], color='red', marker='x', s=100, label='End', zorder=6)
    
    ax.set_title("Detailed 2D Path with Timestamps & Distance Vectors", fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel("X Position (m)", fontsize=11)
    ax.set_ylabel("Y Position (m)", fontsize=11)
    ax.legend(loc='best', frameon=True, framealpha=0.9)
    ax.axis('equal')
    ax.grid(True, linestyle='--', alpha=0.6)
    
    detail_traj_path = os.path.join(save_dir, "trajectory_2d_detailed.png")
    fig.tight_layout()
    fig.savefig(detail_traj_path)
    plt.close(fig)
    print(f"[OK] Saved: {detail_traj_path}")


def plot_batch_summary(summary_csv_path: str, save_dir: str = None):
    """
    Generate comparison charts across all scenarios in summary.csv:
    1. EKF vs UKF Position RMSE bar chart
    2. Tracking Performance (Tracking RMSE & Success Rate) bar chart
    """
    if not os.path.exists(summary_csv_path):
        return
        
    df = pd.read_csv(summary_csv_path)
    if 'scenario_id' not in df or 'ekf_position_rmse' not in df:
        return
        
    if save_dir is None:
        save_dir = os.path.dirname(summary_csv_path)
    os.makedirs(save_dir, exist_ok=True)
        
    scenarios = df['scenario_id'].unique()
    scenarios.sort()
    
    ekf_vals = []
    ukf_vals = []
    track_rmse_vals = []
    success_vals = []
    labels = []
    
    for s_id in scenarios:
        sub = df[df['scenario_id'] == s_id]
        ekf_vals.append(sub['ekf_position_rmse'].mean())
        ukf_vals.append(sub['ukf_position_rmse'].mean() if 'ukf_position_rmse' in sub else 0)
        track_rmse_vals.append(sub['tracking_rmse'].mean() if 'tracking_rmse' in sub else 0)
        success_vals.append((sub['tracking_success_rate'].mean() * 100) if 'tracking_success_rate' in sub else 0)
        name = sub['scenario_name'].iloc[0] if 'scenario_name' in sub else f"S{s_id}"
        labels.append(f"S{s_id}: {name}")
        
    x = np.arange(len(scenarios))
    w = 0.35
    
    # -------------------------------------------------------------
    # Chart 1: EKF vs UKF Position RMSE
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(13, 6), dpi=150)
    rects1 = ax.bar(x - w/2, ekf_vals, w, label='EKF Position RMSE', color='#ff9800', alpha=0.9)
    rects2 = ax.bar(x + w/2, ukf_vals, w, label='UKF Position RMSE', color='#9c27b0', alpha=0.85)
    
    ax.set_ylabel('Position RMSE (m)', fontsize=12, fontweight='bold')
    ax.set_title('Estimation Performance Comparison: EKF vs UKF across All 12 Scenarios', fontsize=14, fontweight='bold', pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha='right', fontsize=9)
    ax.legend(frameon=True, fontsize=11)
    ax.grid(True, linestyle='--', alpha=0.5, axis='y')
    
    for r in rects1:
        h = r.get_height()
        ax.annotate(f"{h:.1f}", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 2),
                    textcoords="offset points", ha='center', va='bottom', fontsize=7.5)
    for r in rects2:
        h = r.get_height()
        ax.annotate(f"{h:.1f}", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 2),
                    textcoords="offset points", ha='center', va='bottom', fontsize=7.5)
                    
    fig.tight_layout()
    out_path1 = os.path.join(save_dir, "batch_comparison_ekf_vs_ukf.png")
    fig.savefig(out_path1)
    plt.close(fig)
    print(f"[OK] Saved: {out_path1}")

    # -------------------------------------------------------------
    # Chart 2: Tracking Performance & Success Rate
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), dpi=150, sharex=True)
    
    bars1 = ax1.bar(x, track_rmse_vals, color='#1e88e5', width=0.55, alpha=0.85)
    ax1.set_ylabel('Tracking RMSE (m)', fontsize=11, fontweight='bold')
    ax1.set_title('UAV Tracking Performance across All 12 Scenarios', fontsize=13, fontweight='bold')
    ax1.grid(True, linestyle='--', alpha=0.5, axis='y')
    for b in bars1:
        h = b.get_height()
        ax1.annotate(f"{h:.1f}", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 2),
                     textcoords="offset points", ha='center', va='bottom', fontsize=8)
                     
    bars2 = ax2.bar(x, success_vals, color='#43a047', width=0.55, alpha=0.85)
    ax2.set_ylabel('Success Rate (%)', fontsize=11, fontweight='bold')
    ax2.set_title('Tracking Success Rate in Acceptable Tolerance Band (±15%)', fontsize=13, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=25, ha='right', fontsize=9)
    ax2.grid(True, linestyle='--', alpha=0.5, axis='y')
    ax2.set_ylim(0, 105)
    for b in bars2:
        h = b.get_height()
        ax2.annotate(f"{h:.1f}%", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 2),
                     textcoords="offset points", ha='center', va='bottom', fontsize=8)
                     
    fig.tight_layout()
    out_path2 = os.path.join(save_dir, "batch_tracking_performance.png")
    fig.savefig(out_path2)
    plt.close(fig)
    print(f"[OK] Saved: {out_path2}")


def generate_all_scenario_plots(base_batch_dir: str, export_figures_dir: str = "results/figures"):
    """
    Generate plots for every scenario in a batch directory and copy to export_figures_dir.
    """
    os.makedirs(export_figures_dir, exist_ok=True)
    
    # 1. Plot batch summaries
    summary_csv = os.path.join(base_batch_dir, "summary.csv")
    if os.path.exists(summary_csv):
        summary_export_dir = os.path.join(export_figures_dir, "summary")
        plot_batch_summary(summary_csv, summary_export_dir)
        
    # 2. Plot each scenario
    subdirs = sorted(glob.glob(os.path.join(base_batch_dir, "scenario_*")))
    for sdir in subdirs:
        sname = os.path.basename(sdir)
        run_dirs = sorted(glob.glob(os.path.join(sdir, "s*")))
        if run_dirs:
            target_run = run_dirs[0]
            scenario_export_dir = os.path.join(export_figures_dir, sname)
            print(f"\n--> Generating plots for {sname}...")
            plot_simulation_run(target_run, save_dir=scenario_export_dir)


if __name__ == '__main__':
    # Find latest batch dir
    batch_dirs = sorted(glob.glob("results/data/batch_*"))
    latest_batch = batch_dirs[-1] if batch_dirs else None
    
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        if latest_batch:
            print(f"Generating full suite of figures for all 12 scenarios from: {latest_batch}")
            generate_all_scenario_plots(latest_batch, "results/figures")
            print("\n[SUCCESS] All plots exported to: results/figures/")
            sys.exit(0)
            
    elif len(sys.argv) > 1:
        target_dir = sys.argv[1]
        if target_dir.endswith(".csv"):
            plot_batch_summary(target_dir)
            sys.exit(0)
        elif os.path.isdir(target_dir) and os.path.exists(os.path.join(target_dir, "summary.csv")):
            generate_all_scenario_plots(target_dir, "results/figures")
            sys.exit(0)
        else:
            plot_simulation_run(target_dir)
            sys.exit(0)
            
    # Default behavior: generate for all 12 scenarios in latest batch + latest single run
    if latest_batch:
        print(f"Generating full figure library for all 12 scenarios from: {latest_batch}")
        generate_all_scenario_plots(latest_batch, "results/figures")
        print("\n[SUCCESS] Complete library of figures saved to: results/figures/")
