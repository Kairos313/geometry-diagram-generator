#!/usr/bin/env python3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path

def render_geometry():
    # --- Hardcoded coordinates from blueprint ---
    # Scaled coordinates (Scale factor 0.3125)
    points = {
        "A": np.array([0.000, 0.000]),
        "B": np.array([5.000, 0.000]),
        "D": np.array([0.938, 1.250]),
        "C": np.array([4.063, 1.250]),
        "D_prime": np.array([0.938, 0.000])  # D'
    }

    output_path = "/Users/kairos/Desktop/geometry-video-generator/Geometry_v2/Geometry Test Questions/Full_Pipeline/test_output/05_trapezoid/diagram.png"
    
    # --- Create figure ---
    fig, ax = plt.subplots(1, 1, figsize=(1920/150, 1080/150), dpi=150)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.set_aspect('equal')
    ax.axis('off')

    # Colors
    ACCENT = "#E63946"
    NORMAL_LINE = "#444444"
    POINT_COLOR = "#1A1A1A"
    REGION_COLOR = "#444444"

    # 0. Draw Regions
    trapezoid_pts = [points["A"], points["B"], points["C"], points["D"]]
    poly = patches.Polygon(trapezoid_pts, closed=True, facecolor=REGION_COLOR, alpha=0.08, zorder=0)
    ax.add_patch(poly)

    # 1. Draw Glow for Asked Elements (DD')
    p_d = points["D"]
    p_dp = points["D_prime"]
    ax.plot([p_d[0], p_dp[0]], [p_d[1], p_dp[1]], color=ACCENT, linewidth=8, alpha=0.2, zorder=1)

    # 2. Draw Lines
    # Normal lines (Sides)
    edges = [
        ("A", "B", "16 cm"),
        ("B", "C", "5 cm"),
        ("C", "D", "10 cm"),
        ("D", "A", "5 cm")
    ]
    for start_key, end_key, label in edges:
        p1, p2 = points[start_key], points[end_key]
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=NORMAL_LINE, linewidth=2, zorder=2)
        
        # Add measurement labels for given lengths
        mid = (p1 + p2) / 2
        vec = p2 - p1
        perp = np.array([-vec[1], vec[0]])
        perp = perp / np.linalg.norm(perp)
        
        # Adjust offset direction based on position relative to center
        offset_dist = 0.25
        if label == "16 cm": # AB (bottom)
            label_pos = mid + np.array([0, -offset_dist])
        elif label == "10 cm": # CD (top)
            label_pos = mid + np.array([0, offset_dist])
        elif label == "5 cm" and start_key == "B": # BC (right)
            label_pos = mid + np.array([offset_dist, 0.1])
        else: # DA (left)
            label_pos = mid + np.array([-offset_dist, 0.1])
            
        ax.text(label_pos[0], label_pos[1], label, color=POINT_COLOR, 
                fontsize=10, ha='center', va='center', zorder=5)

    # Asked line (DD')
    ax.plot([p_d[0], p_dp[0]], [p_d[1], p_dp[1]], color=ACCENT, linewidth=4, zorder=2)
    # Asked label "?"
    mid_h = (p_d + p_dp) / 2
    ax.text(mid_h[0] + 0.15, mid_h[1], "?", color=ACCENT, fontsize=14, fontweight='bold', ha='left', va='center', zorder=5)

    # 3. Angle Arcs / Markers
    # Right angle marker at D' (angle DD'A)
    s = 0.15 # size of square
    square_pts = [
        points["D_prime"],
        points["D_prime"] + np.array([-s, 0]),
        points["D_prime"] + np.array([-s, s]),
        points["D_prime"] + np.array([0, s])
    ]
    sq = patches.Polygon(square_pts, closed=True, fill=False, edgecolor=NORMAL_LINE, linewidth=1.5, zorder=3)
    ax.add_patch(sq)

    # 4. Draw Points
    for name, pt in points.items():
        ax.scatter(pt[0], pt[1], color=POINT_COLOR, s=40, zorder=4)
        
        # Smart label positioning
        label_name = name.replace("_prime", "'")
        offset = np.array([0.0, 0.0])
        if name == "A": offset = np.array([-0.15, -0.15])
        elif name == "B": offset = np.array([0.15, -0.15])
        elif name == "C": offset = np.array([0.15, 0.15])
        elif name == "D": offset = np.array([-0.15, 0.15])
        elif name == "D_prime": offset = np.array([0.1, -0.2])
        
        ax.text(pt[0] + offset[0], pt[1] + offset[1], label_name, 
                color=POINT_COLOR, fontsize=12, ha='center', va='center', zorder=5)

    # Auto-scale with padding
    all_coords = np.array(list(points.values()))
    x_min, y_min = np.min(all_coords, axis=0)
    x_max, y_max = np.max(all_coords, axis=0)
    x_range = x_max - x_min
    y_range = y_max - y_min
    padding = 0.25
    ax.set_xlim(x_min - padding * x_range, x_max + padding * x_range)
    ax.set_ylim(y_min - padding * y_range, y_max + padding * y_range)

    # Save output
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#FFFFFF', edgecolor='none')
        plt.close()
        print(f"Saved: {output_path}")
    except Exception as e:
        print(f"Error saving file: {e}")
        exit(1)

if __name__ == "__main__":
    render_geometry()