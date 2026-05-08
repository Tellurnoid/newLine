import pcbnew
import math

board = pcbnew.GetBoard()

# === 削除対象の特徴 ===
target_layer = pcbnew.Edge_Cuts
target_radius_mm = 100
target_sides = 8
center_x_mm = 297
center_y_mm = 210
center = pcbnew.VECTOR2I(pcbnew.FromMM(center_x_mm), pcbnew.FromMM(center_y_mm))

# === 判定用（八角形の周囲にある線をおおよそ判定） ===
tolerance = pcbnew.FromMM(1)  # ±1mmの誤差で判定

to_remove = []

for d in board.GetDrawings():
    if isinstance(d, pcbnew.PCB_SHAPE) and d.GetLayer() == target_layer:
        start = d.GetStart()
        end = d.GetEnd()

        # 線の両端が中心から約100mmの距離にあるなら削除候補
        dist1 = math.hypot((start.x - center.x), (start.y - center.y))
        dist2 = math.hypot((end.x - center.x), (end.y - center.y))

        if abs(dist1 - pcbnew.FromMM(target_radius_mm)) < tolerance and \
           abs(dist2 - pcbnew.FromMM(target_radius_mm)) < tolerance:
            to_remove.append(d)

for d in to_remove:
    board.Remove(d)

pcbnew.Refresh()

print(f"削除した線分: {len(to_remove)} 本")
