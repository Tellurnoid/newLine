import pcbnew

board = pcbnew.GetBoard()

count = 0
for d in list(board.GetDrawings()):
    # Edge.Cutsレイヤ上の線分を削除
    if isinstance(d, pcbnew.PCB_SHAPE) and d.GetLayer() == pcbnew.Edge_Cuts:
        board.Remove(d)
        count += 1

pcbnew.Refresh()
print(f"🧹 Edge.Cuts上の図形 {count} 個を削除しました。")
