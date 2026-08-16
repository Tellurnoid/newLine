# -*- coding: utf-8 -*-
"""
KiCad の GUI を起動せず、外部から直接 .kicad_pcb を読み書きして
LED1, R1, C1 とその周囲の配線を複製するスクリプト(ヘッドレス版)

■ 目的
  GUIのスクリプティングコンソールで実行すると、ラッツネスト再計算・
  DRCライブチェック・3Dビューア更新・描画などが同時に走り、
  メモリ/CPU負荷が高くクラッシュしやすくなります。
  このスクリプトは KiCad を起動せずに実行するため、その負荷が発生しません。

■ 実行方法
  1. KiCad を完全に終了しておく(必須ではないですが安全のため推奨)
  2. 元の .kicad_pcb を念のためバックアップ
  3. 下の BOARD_PATH / OUTPUT_PATH を書き換える
  4. KiCad に同梱の Python から実行する
     (システムの通常の python では pcbnew モジュールが見つかりません)

     Windows 例:
       "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" duplicate_led_group_headless.py

     macOS 例:
       /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
         duplicate_led_group_headless.py

     Linux 例(KiCadをaptやパッケージマネージャで入れている場合、
     システムpythonにpcbnewが入っていることが多いです):
       python3 duplicate_led_group_headless.py

  5. 完了後、生成された OUTPUT_PATH を KiCad で開いて目視確認
"""

import gc
import re
import pcbnew

# =====================================================================
# ユーザー調整パラメータ
# =====================================================================

BOARD_PATH = r"/home/carbonoid/newLine/KiCad/prot4/prot4.kicad_pcb"
OUTPUT_PATH = r"/home/carbonoid/newLine/KiCad/prot4/prot4.kicad_pcb"  # 元ファイルを上書きしたくない場合は別名に

SOURCE_REFS = ["D1", "Rs1", "Rs2","Rl1","Rl2","U1","Rc1","Rc2", "C1"]

# suffix(固定の新しい番号)ではなく、元の番号からの増分(increment)を指定する。
# 例: LED1, R7, C3 が SOURCE_REFS のとき increment=1 なら LED2, R8, C4 になる
# (部品ごとの元の番号がそれぞれ独立して +increment される)
COPIES = [
    {"increment": 1, "offset_mm": (20.0, 0.0)},
]

SEARCH_MARGIN_MM = 15.0

# 複製後も同じネットのまま共有したいネット名(電源/GNDなど)
#SHARED_NET_NAMES = []  # 例: ["GND", "+5V"]
SHARED_NET_NAMES = ["GND","VCC","LED_5V"]  # 例: ["GND", "+5V"]

# =====================================================================
# 以下、処理本体
# =====================================================================


def mm(v):
    return pcbnew.FromMM(v)


def make_vector(dx, dy):
    try:
        return pcbnew.VECTOR2I(mm(dx), mm(dy))
    except AttributeError:
        return pcbnew.wxPoint(mm(dx), mm(dy))


def new_reference(old_ref, increment):
    """ 'LED1' + increment=1 -> 'LED2' のように、末尾の数字部分だけを
    元の値から increment 分だけカウントアップする(部品ごとに独立) """
    m = re.match(r"^([A-Za-z_]+)(\d+)$", old_ref)
    if not m:
        raise ValueError(f"参照子 '{old_ref}' の形式を解釈できません")
    base, num_str = m.group(1), m.group(2)
    new_num = int(num_str) + increment
    # 元の桁数(例: "01"のようなゼロ埋め)を維持する
    return f"{base}{str(new_num).zfill(len(num_str))}"


def main():
    print(f"読み込み中: {BOARD_PATH}")
    board = pcbnew.LoadBoard(BOARD_PATH)

    def get_footprint(ref):
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            raise ValueError(f"フットプリント '{ref}' が見つかりません")
        return fp

    source_fps = {ref: get_footprint(ref) for ref in SOURCE_REFS}

    source_nets = set()
    for fp in source_fps.values():
        for pad in fp.Pads():
            name = pad.GetNetname()
            if name:
                source_nets.add(name)

    bbox = None
    for fp in source_fps.values():
        b = fp.GetBoundingBox()
        bbox = b if bbox is None else bbox.Merge(b)
    margin = mm(SEARCH_MARGIN_MM)
    bbox.Inflate(margin, margin)

    source_tracks = [
        t for t in board.GetTracks()
        if t.GetNetname() in source_nets and bbox.Contains(t.GetBoundingBox())
    ]

    print(f"複製元フットプリント: {list(source_fps.keys())}")
    print(f"複製元トラック/ビア数: {len(source_tracks)}")

    for copy in COPIES:
        increment = copy["increment"]
        offset = make_vector(*copy["offset_mm"])

        new_fps = {}
        net_map = {}

        for ref, fp in source_fps.items():
            new_fp = pcbnew.FOOTPRINT(fp)
            new_fp.SetReference(new_reference(ref, increment))
            new_fp.Move(offset)
            board.Add(new_fp)
            new_fps[ref] = new_fp

        for ref, fp in source_fps.items():
            new_fp = new_fps[ref]
            for old_pad, new_pad in zip(fp.Pads(), new_fp.Pads()):
                old_netname = old_pad.GetNetname()
                if not old_netname or old_netname in SHARED_NET_NAMES:
                    continue
                if old_netname not in net_map:
                    new_netname = f"{old_netname}_{increment}"
                    new_net = pcbnew.NETINFO_ITEM(board, new_netname)
                    board.Add(new_net)
                    net_map[old_netname] = new_net
                new_pad.SetNet(net_map[old_netname])

        for t in source_tracks:
            new_t = t.Duplicate()
            new_t.Move(offset)
            old_netname = t.GetNetname()
            if old_netname in net_map:
                new_t.SetNet(net_map[old_netname])
            board.Add(new_t)

        print(f"セット (increment={increment}) を複製しました (オフセット {copy['offset_mm']} mm)")

        # ピーク時のメモリを抑えるため、セットごとに未使用オブジェクトを解放
        del new_fps, net_map
        gc.collect()

    board.BuildConnectivity()

    print(f"保存中: {OUTPUT_PATH}")
    pcbnew.SaveBoard(OUTPUT_PATH, board)
    print("完了しました。KiCadで開いて配置・配線を目視確認してください。")


if __name__ == "__main__":
    main()
