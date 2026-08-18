import pcbnew
import math

board = pcbnew.GetBoard()

# ここを変更するだけでOK
prefix = "U"       # 部品のリファレンスの接頭辞 (D, R, LEDなど)
start_n = 1        # 開始番号
count = 16         # 配置したい部品の数

refs = [f"{prefix}{n}" for n in range(start_n, start_n + count)]

center_mm = (500, 500)   # 円の中心 (x, y) mm
radius_mm = 61.2329          # 半径 mm
start_angle_deg = -5.51     # 開始角度
rotate_with_circle = True

n_total = len(refs)
not_found = []

for i, ref in enumerate(refs):
    fp = board.FindFootprintByReference(ref)
    if fp is None:
        not_found.append(ref)
        continue

    # 反時計回りにするため角度の増分を負にする
    angle_deg = start_angle_deg - 360.0 * i / n_total
    angle_rad = math.radians(angle_deg)

    x_mm = center_mm[0] + radius_mm * math.cos(angle_rad)
    y_mm = center_mm[1] + radius_mm * math.sin(angle_rad)

    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))

    if rotate_with_circle:
        fp.SetOrientationDegrees(90 - angle_deg+5.51)

pcbnew.Refresh()

if not_found:
    print(f"見つからなかった部品: {not_found}")
else:
    print(f"{n_total}個の部品を円形に配置しました")
