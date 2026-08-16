# -*- coding: utf-8 -*-
"""
KiCad pcbnew スクリプティングコンソール用
LED1, R1, C1 とその周囲の配線(トラック/ビア)を、
LED2/R2/C2, LED3/R3/C3 ... へ反復的に複製するスクリプト

使い方:
  1. KiCad の PCB エディタを開く
  2. [ツール] -> [スクリプティングコンソール] を開く
  3. このファイルの中身を貼り付けて実行、または
     exec(open(r"このファイルのパス", encoding="utf-8").read())
  4. 実行後、[表示]->[更新] や保存前の目視確認を忘れずに

KiCadのバージョンによって pcbnew の API(座標型が wxPoint か VECTOR2I か等)が
異なります。手元でエラーが出た場合は該当箇所をコメントに従って調整してください。
(このスクリプトは KiCad 7/8 系を想定しています)
"""

import re
import pcbnew

board = pcbnew.GetBoard()

# =====================================================================
# ユーザー調整パラメータ
# =====================================================================

# 複製元となる基準グループの参照子
SOURCE_REFS = ["D1", "Rs1", "Rs2","Rl1","Rl2","U1","Rc1","Rc2", "C1"]

# 複製先の定義: 1エントリが1セット分(参照子サフィックスとオフセット)
# offset は (X[mm], Y[mm]) で指定。基準グループからの相対移動量。
COPIES = [
    {"suffix": "2", "offset_mm": (20.0, 0.0)},
    # 必要なだけ追加できます
    # {"suffix": "4", "offset_mm": (60.0, 0.0)},
]

# 配線を拾う際、部品のバウンディングボックスをどれだけ広げて探索するか(mm)
# 部品からはみ出した配線(引き回し)も含めて複製したい場合は広めに
SEARCH_MARGIN_MM = 5.0

# ネットを新規に作らず、元のネットのまま繋げておきたいネット名
# (例: 電源/GNDを共通にしたい場合はここに書く。空リストなら全ネットを複製ごとに独立させる)
SHARED_NET_NAMES = []  # 例: ["GND", "+5V"]

# =====================================================================
# 以下、処理本体(通常は変更不要)
# =====================================================================


def mm(v):
    return pcbnew.FromMM(v)


def get_footprint(ref):
    fp = board.FindFootprintByReference(ref)
    if fp is None:
        raise ValueError(f"フットプリント '{ref}' が見つかりません")
    return fp


def new_reference(old_ref, suffix):
    """ 'LED1' + suffix '2' -> 'LED2' のように、末尾の数字部分だけ置き換える """
    m = re.match(r"^([A-Za-z_]+)(\d+)$", old_ref)
    if not m:
        raise ValueError(f"参照子 '{old_ref}' の形式を解釈できません")
    base = m.group(1)
    return f"{base}{suffix}"


def make_vector(dx, dy):
    # KiCad 7/8: VECTOR2I。旧バージョンで無ければ wxPoint に変更してください。
    try:
        return pcbnew.VECTOR2I(mm(dx), mm(dy))
    except AttributeError:
        return pcbnew.wxPoint(mm(dx), mm(dy))


def main():
    source_fps = {ref: get_footprint(ref) for ref in SOURCE_REFS}

    # ソース部品が属するネット名一覧
    source_nets = set()
    for fp in source_fps.values():
        for pad in fp.Pads():
            name = pad.GetNetname()
            if name:
                source_nets.add(name)

    # 探索用バウンディングボックスを合成
    bbox = None
    for fp in source_fps.values():
        b = fp.GetBoundingBox()
        bbox = b if bbox is None else bbox.Merge(b)
    margin = mm(SEARCH_MARGIN_MM)
    bbox.Inflate(margin, margin)

    # 探索領域内かつソースネットに属するトラック/ビア/配線弧を収集
    source_tracks = []
    for t in board.GetTracks():
        if t.GetNetname() in source_nets and bbox.Contains(t.GetBoundingBox()):
            source_tracks.append(t)

    print(f"複製元フットプリント: {list(source_fps.keys())}")
    print(f"複製元トラック/ビア数: {len(source_tracks)}")

    for copy in COPIES:
        suffix = copy["suffix"]
        offset = make_vector(*copy["offset_mm"])

        new_fps = {}
        net_map = {}  # 元ネット名 -> 新規 NETINFO_ITEM

        # --- フットプリント複製 ---
        for ref, fp in source_fps.items():
            new_fp = pcbnew.FOOTPRINT(fp)  # コピーコンストラクタ
            new_fp.SetReference(new_reference(ref, suffix))
            new_fp.Move(offset)
            board.Add(new_fp)
            new_fps[ref] = new_fp

        # --- パッドのネット差し替え ---
        for ref, fp in source_fps.items():
            new_fp = new_fps[ref]
            for old_pad, new_pad in zip(fp.Pads(), new_fp.Pads()):
                old_netname = old_pad.GetNetname()
                if not old_netname:
                    continue

                if old_netname in SHARED_NET_NAMES:
                    # 元のネットのまま(共通ネットとして接続)
                    continue

                if old_netname not in net_map:
                    new_netname = f"{old_netname}_{suffix}"
                    new_net = pcbnew.NETINFO_ITEM(board, new_netname)
                    board.Add(new_net)
                    net_map[old_netname] = new_net

                new_pad.SetNet(net_map[old_netname])

        # --- 配線(トラック/ビア/配線弧)複製 ---
        for t in source_tracks:
            new_t = t.Duplicate()
            new_t.Move(offset)
            old_netname = t.GetNetname()
            if old_netname in net_map:
                new_t.SetNet(net_map[old_netname])
            # SHARED_NET_NAMES に含まれる場合は何もしない = 元のネットのまま
            board.Add(new_t)

        print(f"セット '{suffix}' を複製しました (オフセット {copy['offset_mm']} mm)")

    # 接続情報(ラッツネスト等)を更新
    board.BuildConnectivity()
    pcbnew.Refresh()
    print("完了しました。保存前に配置・配線を目視確認してください。")


main()
