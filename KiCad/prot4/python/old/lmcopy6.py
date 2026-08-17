# -*- coding: utf-8 -*-
"""
KiCad の GUI を起動せず、外部から直接 .kicad_pcb を読み書きして、
「すでに回路図と対応づけられた(=実在するUUIDを持つ)複数グループの部品」を
複製せずに、そのまま円周上の指定位置へ移動・回転するスクリプト(ヘッドレス版)

■ 前提
  ・回路図側にすでに D1グループ, D2グループ, D3グループ...のように、
    実体のある複数インスタンスが存在している
  ・「シンボルの更新(PCBへ反映)」等で、それぞれの部品がPCB上にすでに
    フットプリントとして存在し、UUIDも回路図と対応している
  ・各グループの周囲の配線(トラック/ビア)もすでに存在している

  このスクリプトは新しいフットプリントや新しいネットを一切作成しません。
  既存のオブジェクトを直接 Move / Rotate するだけです。
  そのため、回路図とのUUID対応・ネット対応はそのまま保たれます。

■ 実行方法
  KiCad に同梱の Python から実行してください
  (システムの通常の python では pcbnew モジュールが見つからないか、
   バージョン不一致でクラッシュする場合があります)。

     Windows 例:
       "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" lmcopy_move_existing.py

     macOS 例:
       /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
         lmcopy_move_existing.py

     Linux 例:
       python3 lmcopy_move_existing.py
       (クラッシュする場合は、KiCadに同梱のpythonがあればそちらを使ってください)

  実行前に必ず .kicad_pcb をバックアップしてください。
"""

import math
import pcbnew
import faulthandler

faulthandler.enable()  # セグフォルト時にPython側のスタックトレースを出力する

# =====================================================================
# ユーザー調整パラメータ
# =====================================================================

BOARD_PATH = r"/home/carbonoid/newLine/KiCad/prot4/prot4.kicad_pcb"
OUTPUT_PATH = r"/home/carbonoid/newLine/KiCad/prot4/prot4.kicad_pcb"  # 元ファイルを上書きしたくない場合は別名に

SEARCH_MARGIN_MM = 15.0

# 複数グループで共有されている可能性のあるネット名(電源/GNDなど)。
# これらのネットに属するトラックは「そのグループ専用の配線」ではなく
# 他の場所ともつながっている可能性があるため、移動対象から除外します。
SHARED_NET_NAMES = ["GND", "VCC", "LED_5V"]

CIRCLE_CENTER_MM = (150.0, 100.0)  # 円の中心座標 (mm) : (X, Y)

# 各グループ = 既存の部品セット(すでに回路図と対応済み・配線済み)
# refs: そのグループに属する実在の参照子
#
# ちょうど1つのグループに "is_base": True を付けてください。
# 基準グループは移動しません。その代わり、基準グループの現在の実際の位置から
# CIRCLE_CENTER_MM までの距離(半径)と角度を自動計算し、他のグループは
# そこからの相対値(angle_offset_deg: 角度差、radius_offset_mm: 半径差)で
# 配置します。
#
# 例えば基準グループが中心から半径40mm・角度10度の位置にあった場合、
# angle_offset_deg=60 のグループは「半径40mm・角度70度」の位置に、
# グループ全体(部品+その配線)が平行移動+その場で60度分だけ自転して
# 配置されます(回転量は角度の"差分"だけ適用されます)。
GROUPS = [
    {"refs": ["D1", "Rs1", "Rs2", "Rl1", "Rl2", "U1", "Rc1", "Rc2", "C1"],
     "is_base": True},
    {"refs": ["D2", "Rs3", "Rs4", "Rl3", "Rl4", "U2", "Rc3", "Rc4", "C2"],
     "angle_offset_deg": 60.0, "radius_offset_mm": 0.0},
    {"refs": ["D3", "Rs5", "Rs6", "Rl5", "Rl6", "U3", "Rc5", "Rc6", "C3"],
     "angle_offset_deg": 120.0, "radius_offset_mm": 0.0},
    # 必要な分だけ追加してください
]

# =====================================================================
# 以下、処理本体
# =====================================================================


def mm(v):
    return pcbnew.FromMM(v)


def make_point_nm(x, y):
    """ x, y は KiCad内部単位(nm)。mm単位への変換は行わない。 """
    try:
        return pcbnew.VECTOR2I(int(round(x)), int(round(y)))
    except AttributeError:
        return pcbnew.wxPoint(int(round(x)), int(round(y)))


def footprint_bbox_from_pads(fp):
    """ fp.GetBoundingBox() はヘッドレス実行時にコートヤードキャッシュ未初期化で
    セグフォルトすることがあるため使わない。パッドのバウンディングボックスを
    合成して代わりに使う(この用途では十分な精度)。 """
    bbox = None
    for pad in fp.Pads():
        b = pad.GetBoundingBox()
        bbox = b if bbox is None else bbox.Merge(b)
    if bbox is None:
        # パッドが無い場合のフォールバック(位置のみの点として扱う)
        pos = fp.GetPosition()
        bbox = pcbnew.BOX2I(pos, make_point_nm(0, 0))
    return bbox


def to_rotation_angle(deg):
    """ pcbnewのバージョン差異を吸収して回転角オブジェクトを返す。
    KiCad 7以降: EDA_ANGLE、それ以前: 1/10度単位の整数 """
    try:
        return pcbnew.EDA_ANGLE(deg, pcbnew.DEGREES_T)
    except AttributeError:
        return int(round(deg * 10))


def main():
    print(f"読み込み中: {BOARD_PATH}")
    board = pcbnew.LoadBoard(BOARD_PATH)

    def get_footprint(ref):
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            raise ValueError(
                f"フットプリント '{ref}' が見つかりません。"
                f"回路図からPCBへ未反映の可能性があります"
                f"(「基板をシンボルの変更で更新」を先に実行してください)。"
            )
        return fp

    margin = mm(SEARCH_MARGIN_MM)
    center_x = mm(CIRCLE_CENTER_MM[0])
    center_y = mm(CIRCLE_CENTER_MM[1])

    # ---- 基準グループの現在位置から半径・角度を自動取得 ----
    base_groups = [g for g in GROUPS if g.get("is_base")]
    if len(base_groups) != 1:
        raise ValueError("GROUPS の中にちょうど1つ 'is_base': True を指定してください")
    base_group = base_groups[0]

    base_fps = {ref: get_footprint(ref) for ref in base_group["refs"]}
    base_anchor_x = sum(fp.GetPosition().x for fp in base_fps.values()) / len(base_fps)
    base_anchor_y = sum(fp.GetPosition().y for fp in base_fps.values()) / len(base_fps)

    base_dx = base_anchor_x - center_x
    base_dy = base_anchor_y - center_y
    base_radius = math.hypot(base_dx, base_dy)
    base_angle_rad = math.atan2(base_dy, base_dx)

    print(
        f"基準グループ({base_group['refs'][0]}系)の現在位置: "
        f"半径 {pcbnew.ToMM(base_radius):.3f} mm, "
        f"角度 {math.degrees(base_angle_rad):.3f} 度 (中心からの相対値)"
    )

    for group in GROUPS:
        if group.get("is_base"):
            continue  # 基準グループは移動しない

        refs = group["refs"]
        angle_offset_deg = group.get("angle_offset_deg", 0.0)
        radius_offset_mm = group.get("radius_offset_mm", 0.0)

        radius = base_radius + mm(radius_offset_mm)
        angle_rad = base_angle_rad + math.radians(angle_offset_deg)

        print(f"  [debug] {refs[0]}系: get_footprint 開始")
        fps = {ref: get_footprint(ref) for ref in refs}
        print(f"  [debug] {refs[0]}系: get_footprint 完了")

        # このグループの部品が使っているネット(共有ネットは除外)
        group_nets = set()
        for fp in fps.values():
            for pad in fp.Pads():
                name = pad.GetNetname()
                if name and name not in SHARED_NET_NAMES:
                    group_nets.add(name)
        print(f"  [debug] {refs[0]}系: ネット収集完了 ({len(group_nets)}件)")

        # このグループのバウンディングボックス(既存配線の検索用)
        bbox = None
        for fp in fps.values():
            b = footprint_bbox_from_pads(fp)
            bbox = b if bbox is None else bbox.Merge(b)
        bbox.Inflate(margin, margin)
        print(f"  [debug] {refs[0]}系: バウンディングボックス計算完了")

        group_tracks = [
            t for t in board.GetTracks()
            if t.GetNetname() in group_nets and bbox.Contains(t.GetBoundingBox())
        ]
        print(f"  [debug] {refs[0]}系: トラック収集完了 ({len(group_tracks)}件)")

        # このグループの基準点(アンカー) = 各フットプリント位置の重心
        anchor_x = sum(fp.GetPosition().x for fp in fps.values()) / len(fps)
        anchor_y = sum(fp.GetPosition().y for fp in fps.values()) / len(fps)

        # 目標座標
        target_x = center_x + radius * math.cos(angle_rad)
        target_y = center_y + radius * math.sin(angle_rad)

        offset = make_point_nm(target_x - anchor_x, target_y - anchor_y)
        rot_centre = make_point_nm(target_x, target_y)
        rot_angle = to_rotation_angle(angle_offset_deg)  # 基準グループからの回転差分
        print(f"  [debug] {refs[0]}系: offset/rot_angle計算完了 -> {rot_angle}")

        # 既存オブジェクトを直接移動・回転する(複製しない・新規ネットも作らない)
        for ref, fp in fps.items():
            print(f"  [debug] {ref}: Move開始")
            fp.Move(offset)
            print(f"  [debug] {ref}: Move完了 / Rotate開始")
            fp.Rotate(rot_centre, rot_angle)
            print(f"  [debug] {ref}: Rotate完了")

        for i, t in enumerate(group_tracks):
            print(f"  [debug] track[{i}] ({t.GetNetname()}): Move開始")
            t.Move(offset)
            print(f"  [debug] track[{i}]: Move完了 / Rotate開始")
            t.Rotate(rot_centre, rot_angle)
            print(f"  [debug] track[{i}]: Rotate完了")

        print(
            f"グループ {refs[0]} 系({len(fps)}部品, "
            f"配線/ビア{len(group_tracks)}個)を移動しました "
            f"(半径 {pcbnew.ToMM(radius):.3f} mm, "
            f"角度 {math.degrees(angle_rad):.3f} 度 "
            f"[基準から角度差 {angle_offset_deg} 度, 半径差 {radius_offset_mm} mm])"
        )

    board.BuildConnectivity()

    print(f"保存中: {OUTPUT_PATH}")
    pcbnew.SaveBoard(OUTPUT_PATH, board)
    print("完了しました。KiCadで開いて配置・配線・回路図との対応を目視確認してください。")


if __name__ == "__main__":
    main()