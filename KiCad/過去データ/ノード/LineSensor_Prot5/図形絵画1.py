import pcbnew
import math

try:
    board = pcbnew.GetBoard()
except RuntimeError:
    # PCBエディタ外でも動作させる
    board = pcbnew.LoadBoard("/home/tellurnoid/25RoboCup/kiCad/LineSensor_Prot2/LineSensor_Prot2.kicad_pcb")
    print("外部ロードでboardを取得しました。")

center_x_mm = 297
center_y_mm = 210
radius_mm = 100
sides = 8
layer = pcbnew.Edge_Cuts

center = pcbnew.VECTOR2I(pcbnew.FromMM(center_x_mm), pcbnew.FromMM(center_y_mm))
points = []

for i in range(sides):
    angle = 2 * math.pi * i / sides
    x = center.x + pcbnew.FromMM(radius_mm * math.cos(angle))
    y = center.y + pcbnew.FromMM(radius_mm * math.sin(angle))
    points.append(pcbnew.VECTOR2I(int(x), int(y)))

for i in range(sides):
    seg = pcbnew.PCB_SHAPE(board)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetLayer(layer)
    seg.SetWidth(pcbnew.FromMM(0.15))
    seg.SetStart(points[i])
    seg.SetEnd(points[(i+1)%sides])
    board.Add(seg)

pcbnew.Refresh()
print("正八角形を描画しました。")
