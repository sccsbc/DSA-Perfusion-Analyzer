"""交互式选点脚本：用 matplotlib 验证 DSA 灌注算法。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# 兼容从不同目录运行的导入
try:
    from dicom_parser import parse_dicom, export_preview_frames
    from tic_extractor import extract_aif_and_rois
    from perfusion_params import compute_tic_parameters
    from deconvolution import compute_deconvolution_parameters
except ImportError:
    from src.dicom_parser import parse_dicom, export_preview_frames
    from src.tic_extractor import extract_aif_and_rois
    from src.perfusion_params import compute_tic_parameters
    from src.deconvolution import compute_deconvolution_parameters


def pick_points(frame_image: np.ndarray, max_rois: int = 3):
    """
    弹出 matplotlib 窗口，让用户点击选点。
    第一个点为 AIF，后续为 ROI。
    返回 aif 坐标和 roi 列表。
    """
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(frame_image, cmap="gray")

    points = []
    colors = ["red", "green", "blue", "orange"]
    labels = ["AIF", "ROI-1", "ROI-2", "ROI-3"]

    def update_title():
        selected = "\n".join(
            f"  {labels[i]}: ({points[i][0]:.0f}, {points[i][1]:.0f})"
            for i in range(len(points))
        )
        hint = (
            f"已选 {len(points)}/4 个点"
            if len(points) < 1 + max_rois
            else "选点完成！按 Enter 键或关闭窗口继续"
        )
        ax.set_title(
            f"请点击选点：第1个=AIF(红)，第2-4个=ROI(绿/蓝/黄)\n"
            f"{hint}\n{selected}",
            fontsize=11,
        )
        fig.canvas.draw()

    update_title()

    def on_click(event):
        if event.inaxes != ax:
            return
        if len(points) >= 1 + max_rois:
            return
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
        points.append((x, y))
        idx = len(points) - 1
        color = colors[idx % len(colors)]
        label = labels[idx % len(labels)]
        ax.plot(x, y, "o", color=color, markersize=12, label=label)
        ax.text(x + 10, y - 10, label, color=color, fontsize=10)
        update_title()

    def on_key(event):
        if event.key in ("return", "enter", "q"):
            plt.close(fig)

    fig.canvas.mpl_connect("button_press_event", on_click)
    fig.canvas.mpl_connect("key_press_event", on_key)
    plt.show()

    if len(points) < 2:
        raise ValueError("请至少选择 1 个 AIF 和 1 个 ROI")

    aif = {"x": float(points[0][0]), "y": float(points[0][1]), "radius": 10.0}
    rois = []
    for i, (x, y) in enumerate(points[1:], start=1):
        rois.append({
            "id": f"roi-{i}",
            "x": float(x),
            "y": float(y),
            "radius": 15.0,
        })

    return aif, rois


def analyze(dicom_path: str | Path, output_dir: str | Path | None = None):
    """完整分析流程：解析 -> 选点 -> 提取 TIC -> 计算参数 -> 绘图 -> 保存结果。"""
    dicom_path = Path(dicom_path)
    print(f"正在解析 DICOM: {dicom_path}")

    data = parse_dicom(dicom_path)
    pixel_array = data["pixel_array"]
    times = data["times"]
    n_frames, rows, cols = pixel_array.shape

    print(f"帧数: {n_frames}, 尺寸: {rows}x{cols}, 帧率: {data.get('frame_rate')} fps")

    # 显示中间帧用于选点
    mid_frame_idx = n_frames // 2
    mid_frame = pixel_array[mid_frame_idx]
    # 归一化到 0-255 用于显示
    f_min, f_max = mid_frame.min(), mid_frame.max()
    display_frame = ((mid_frame - f_min) / max(f_max - f_min, 1e-6) * 255).astype(np.uint8)

    print("请在弹出的窗口中选点...")
    aif, rois = pick_points(display_frame, max_rois=3)
    print(f"AIF: {aif}")
    for r in rois:
        print(f"  {r['id']}: ({r['x']:.1f}, {r['y']:.1f}), r={r['radius']}")

    # 提取 TIC
    tics = extract_aif_and_rois(pixel_array, aif, rois)

    # 计算参数
    results = {}
    for key, tic in tics.items():
        tic_params = compute_tic_parameters(tic, times, baseline_frames=3)
        if key != "aif":
            deconv_params = compute_deconvolution_parameters(
                tics["aif"], tic, times, sigma=1.0
            )
            tic_params.update({
                "dsa_cbf": deconv_params["dsa_cbf"],
                "dsa_cbv": deconv_params["dsa_cbv"],
                "dsa_mtt": deconv_params["dsa_mtt"],
                "dsa_tmax": deconv_params["dsa_tmax"],
            })
        results[key] = tic_params

    # 打印结果
    print("\n=== 分析结果 ===")
    for key, params in results.items():
        print(f"\n[{key.upper()}]")
        for p_name, p_val in params.items():
            if isinstance(p_val, float):
                print(f"  {p_name}: {p_val:.4f}")
            elif isinstance(p_val, np.ndarray):
                print(f"  {p_name}: array shape {p_val.shape}")

    # 绘图
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. TIC 曲线
    ax_tic = axes[0, 0]
    colors = {"aif": "red", "roi-1": "green", "roi-2": "blue", "roi-3": "orange"}
    for key, tic in tics.items():
        ax_tic.plot(times, tic, label=key.upper(), color=colors.get(key, "black"))
    ax_tic.set_xlabel("Time (s)")
    ax_tic.set_ylabel("Intensity")
    ax_tic.set_title("Time-Intensity Curves")
    ax_tic.legend()
    ax_tic.grid(True, linestyle="--", alpha=0.5)

    # 2. Residue functions
    ax_res = axes[0, 1]
    for key in tics:
        if key == "aif":
            continue
        deconv = compute_deconvolution_parameters(tics["aif"], tics[key], times, sigma=1.0)
        ax_res.plot(times, deconv["flow_scaled_residue"], label=key.upper(), color=colors.get(key, "black"))
    ax_res.set_xlabel("Time (s)")
    ax_res.set_ylabel("Flow-scaled Residue k(t)")
    ax_res.set_title("Residue Functions")
    ax_res.legend()
    ax_res.grid(True, linestyle="--", alpha=0.5)

    # 3. 参数表格图
    ax_table = axes[1, 0]
    ax_table.axis("off")
    table_data = []
    for key, params in results.items():
        if key == "aif":
            continue
        row = [
            key.upper(),
            f"{params['ttp']:.2f}",
            f"{params['auc']:.2f}",
            f"{params['wash_in_slope']:.2f}",
            f"{params['dsa_cbf']:.4f}",
            f"{params['dsa_mtt']:.2f}",
            f"{params['dsa_tmax']:.2f}",
        ]
        table_data.append(row)

    if table_data:
        table = ax_table.table(
            cellText=table_data,
            colLabels=["ROI", "TTP", "AUC", "Wash-in", "DSA-CBF", "DSA-MTT", "DSA-Tmax"],
            loc="center",
            cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)
    ax_table.set_title("Perfusion Parameters", y=0.95)

    # 4. 带标记的 DSA 帧
    ax_img = axes[1, 1]
    ax_img.imshow(display_frame, cmap="gray")
    for key, circle in [("aif", aif)] + [(r["id"], r) for r in rois]:
        color = colors.get(key, "white")
        circ = plt.Circle((circle["x"], circle["y"]), circle["radius"], color=color, fill=False, linewidth=2)
        ax_img.add_patch(circ)
        ax_img.text(circle["x"], circle["y"] - circle["radius"] - 5, key.upper(), color=color, fontsize=9, ha="center")
    ax_img.set_title("Selected Regions")
    ax_img.axis("off")

    plt.tight_layout()

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存结果 JSON
        result_path = output_dir / "result.json"
        with open(result_path, "w", encoding="utf-8") as f:
            # numpy 不可直接 JSON 序列化，先转 list
            serializable = {}
            for k, v in results.items():
                serializable[k] = {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv for kk, vv in v.items()}
            json.dump(serializable, f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存: {result_path}")

        # 保存图片
        fig_path = output_dir / "analysis.png"
        plt.savefig(fig_path, dpi=150)
        print(f"图表已保存: {fig_path}")

    plt.show()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python src/interactive_picker.py <dicom_path> [output_dir]")
        sys.exit(1)

    dicom_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    analyze(dicom_path, output_dir)
