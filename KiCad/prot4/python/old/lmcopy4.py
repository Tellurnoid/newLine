
"""
KiCad の GUI を起動せず、外部から直接 .kicad_pcb を読み書きして
任意の部品群とその周囲の配線を複製するスクリプト（ヘッドレス版）

■ 目的
    KiCad の GUI を起動せずに .kicad_pcb を直接読み書きします。

    GUI のスクリプティングコンソールで実行すると、ラッツネスト再計算・
    DRC ライブチェック・3D ビューア更新・描画などが同時に走り、
    メモリ / CPU 負荷が高くクラッシュしやすくなります。

    このスクリプトは KiCad を起動せずに実行するため、その負荷が発生しません。


■ 実行方法
    1. KiCad を完全に終了しておく
       （必須ではないですが安全のため推奨）

    2. 元の .kicad_pcb を念のためバックアップ

    3. 下の BOARD_PATH / OUTPUT_PATH / SOURCE_REFS / CIRCULAR_LAYOUT
       などを必要に応じて変更

    4. KiCad に同梱の Python から実行

       Windows 例:
       "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" lmcopy3.py

       macOS 例:
       /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
           lmcopy3.py

       Linux 例:
       python3 lmcopy3.py

    5. 完了後、生成された OUTPUT_PATH を KiCad で開いて目視確認


■ 円形配置

    CIRCULAR_LAYOUT で以下を指定します。

        center_mm:
            円の中心座標 (X, Y) [mm]

        radius_mm:
            円の半径 [mm]

        start_angle_deg:
            最初のコピーを配置する角度 [deg]

        angle_step_deg:
            コピーごとの角度差 [deg]

        count:
            コピー数

        rotate_group:
            True  -> 部品群自体も円の中心を基準に回転
            False -> 部品群は元の向きを維持して円周上に配置


    例:

        CIRCULAR_LAYOUT = {
            "center_mm": (100.0, 100.0),
            "radius_mm": 50.0,
            "start_angle_deg": 0.0,
            "angle_step_deg": 30.0,
            "count": 12,
            "rotate_group": True,
        }

    この場合、

        中心       : (100, 100) mm
        半径       : 50 mm
        開始角度   : 0 度
        角度間隔   : 30 度
        コピー数   : 12 個

    となります。


■ 角度について

    KiCad の座標系に合わせて、ここでは

        0 度   : +X 方向
        90 度  : +Y 方向

    として円周上の位置を計算します。


■ ネットについて

    複製元と同じネットをそのまま共有したいネットは
    SHARED_NET_NAMES に指定します。

    それ以外のネットは

        元ネット名_increment

    という新しいネットを作成します。
"""

import gc
import math
import re

import pcbnew


# =====================================================================
# ユーザー調整パラメータ
# =====================================================================

BOARD_PATH = r"/home/carbonoid/newLine/KiCad/prot4/prot4.kicad_pcb"

# 元ファイルを上書きしたくない場合は別名にしてください。
OUTPUT_PATH = r"/home/carbonoid/newLine/KiCad/prot4/prot4.kicad_pcb"


# ---------------------------------------------------------------------
# 複製する部品
# ---------------------------------------------------------------------

SOURCE_REFS = [
    "D1",
    "Rs1",
    "Rs2",
    "Rl1",
    "Rl2",
    "U1",
    "Rc1",
    "Rc2",
    "C1",
]


# ---------------------------------------------------------------------
# 円形配置設定
# ---------------------------------------------------------------------
#
# center_mm:
#     円の中心座標 (X, Y) [mm]
#
# radius_mm:
#     円の半径 [mm]
#
# start_angle_deg:
#     最初のコピーを配置する角度
#
# angle_step_deg:
#     コピー間の角度差
#
# count:
#     コピー数
#
# rotate_group:
#     True  = 部品群そのものも回転
#     False = 部品群の向きは変えない
#
# ---------------------------------------------------------------------

CIRCULAR_LAYOUT = {
    "center_mm": (500.0, 500.0),
    "radius_mm": 30.0,
    "start_angle_deg": 0.0,
    "angle_step_deg": 90,
    "count": 2,
    "rotate_group": True,
}


# ---------------------------------------------------------------------
# 検索範囲
# ---------------------------------------------------------------------
#
# SOURCE_REFS のフットプリントを囲む bounding box を作り、
# その外側にこの値 [mm] のマージンを付けます。
#
# この範囲内に完全に含まれるトラック / ビアを
# 「複製対象の配線」として扱います。
#
# ---------------------------------------------------------------------

SEARCH_MARGIN_MM = 15.0


# ---------------------------------------------------------------------
# 複製後も同じネットのまま共有したいネット
# ---------------------------------------------------------------------

SHARED_NET_NAMES = [
    "GND",
    "VCC",
    "LED_5V",
]


# =====================================================================
# 以下、処理本体
# =====================================================================


def mm(v):
    """mm → KiCad 内部単位"""
    return pcbnew.FromMM(v)


def make_vector(dx, dy):
    """
    KiCad のバージョン差を考慮して VECTOR2I / wxPoint を生成する。
    """
    try:
        return pcbnew.VECTOR2I(mm(dx), mm(dy))
    except AttributeError:
        return pcbnew.wxPoint(mm(dx), mm(dy))


def make_angle(angle_deg):
    """
    KiCad 9 系で使用する EDA_ANGLE を生成する。
    """
    return pcbnew.EDA_ANGLE(angle_deg, pcbnew.DEGREES_T)


def new_reference(old_ref, increment):
    """
    'LED1' + increment=1 -> 'LED2'

    末尾の数字部分だけを increment 分だけ
    カウントアップします。

    例:
        R1  + 1 -> R2
        R7  + 3 -> R10
        C01 + 1 -> C02

    元の桁数（ゼロ埋め）も維持します。
    """

    m = re.match(r"^([A-Za-z_]+)(\d+)$", old_ref)

    if not m:
        raise ValueError(
            f"参照子 '{old_ref}' の形式を解釈できません"
        )

    base, num_str = m.group(1), m.group(2)

    new_num = int(num_str) + increment

    return f"{base}{str(new_num).zfill(len(num_str))}"


def rotate_point_xy(x, y, center_x, center_y, angle_deg):
    """
    点 (x, y) を center=(center_x, center_y) の周りに
    angle_deg 度回転した座標を返します。

    KiCad の基板座標系で使用するため、
    Y 軸の符号を反転させるような変換は行いません。
    """

    theta = math.radians(angle_deg)

    dx = x - center_x
    dy = y - center_y

    cos_a = math.cos(theta)
    sin_a = math.sin(theta)

    rx = center_x + dx * cos_a - dy * sin_a
    ry = center_y + dx * sin_a + dy * cos_a

    return rx, ry


def get_circular_position(center_x, center_y, radius, angle_deg):
    """
    円周上の位置を計算します。
    """

    theta = math.radians(angle_deg)

    x = center_x + radius * math.cos(theta)
    y = center_y + radius * math.sin(theta)

    return x, y


def rotate_footprint_to_position(
    new_fp,
    source_fp,
    center_x,
    center_y,
    target_angle_deg,
    rotate_group,
):
    """
    複製したフットプリントを円形配置する。

    rotate_group=True の場合:
        元フットプリントの位置を円の中心周りに回転し、
        フットプリント自身の向きも同じ角度だけ回転する。

    rotate_group=False の場合:
        フットプリントの向きは変更せず、
        位置だけを円周上の位置に移動する。

    この関数では、元のフットプリントの位置を基準として
    円の中心周りの回転を行います。
    """

    source_pos = source_fp.GetPosition()

    source_x_mm = pcbnew.ToMM(source_pos.x)
    source_y_mm = pcbnew.ToMM(source_pos.y)

    if rotate_group:
        new_x_mm, new_y_mm = rotate_point_xy(
            source_x_mm,
            source_y_mm,
            center_x,
            center_y,
            target_angle_deg,
        )

        new_fp.SetPosition(
            make_vector(
                new_x_mm - source_x_mm,
                new_y_mm - source_y_mm,
            )
        )

        # 元の向き + 円形配置角度
        original_orientation = source_fp.GetOrientationDegrees()

        new_fp.SetOrientationDegrees(
            original_orientation + target_angle_deg
        )

    else:
        # グループを回転させず、
        # フットプリント群の基準位置だけを円周上へ移動。
        #
        # ここは呼び出し側でグループ基準位置から
        # offset を計算しているため、通常は使用しません。
        new_fp.SetOrientationDegrees(
            source_fp.GetOrientationDegrees()
        )


def main():

    print(f"読み込み中: {BOARD_PATH}")

    board = pcbnew.LoadBoard(BOARD_PATH)

    if board is None:
        raise RuntimeError(
            f"基板ファイルを読み込めませんでした: {BOARD_PATH}"
        )


    # =================================================================
    # 設定値取得
    # =================================================================

    center_x, center_y = CIRCULAR_LAYOUT["center_mm"]

    radius_mm = CIRCULAR_LAYOUT["radius_mm"]

    start_angle_deg = CIRCULAR_LAYOUT["start_angle_deg"]

    angle_step_deg = CIRCULAR_LAYOUT["angle_step_deg"]

    count = CIRCULAR_LAYOUT["count"]

    rotate_group = CIRCULAR_LAYOUT["rotate_group"]


    if count <= 0:
        raise ValueError(
            "CIRCULAR_LAYOUT['count'] は 1 以上にしてください"
        )

    if radius_mm < 0:
        raise ValueError(
            "CIRCULAR_LAYOUT['radius_mm'] は 0 以上にしてください"
        )


    print("")
    print("=== 円形配置設定 ===")
    print(f"中心              : ({center_x}, {center_y}) mm")
    print(f"半径              : {radius_mm} mm")
    print(f"開始角度          : {start_angle_deg} deg")
    print(f"角度ステップ      : {angle_step_deg} deg")
    print(f"コピー数          : {count}")
    print(f"グループ回転      : {rotate_group}")
    print("")


    # =================================================================
    # フットプリント取得
    # =================================================================

    def get_footprint(ref):

        fp = board.FindFootprintByReference(ref)

        if fp is None:
            raise ValueError(
                f"フットプリント '{ref}' が見つかりません"
            )

        return fp


    source_fps = {
        ref: get_footprint(ref)
        for ref in SOURCE_REFS
    }


    # =================================================================
    # 元部品群が使用しているネットを収集
    # =================================================================

    source_nets = set()

    for fp in source_fps.values():

        for pad in fp.Pads():

            name = pad.GetNetname()

            if name:
                source_nets.add(name)


    # =================================================================
    # 元部品群の bounding box を取得
    # =================================================================

    bbox = None

    for fp in source_fps.values():

        b = fp.GetBoundingBox()

        bbox = (
            b
            if bbox is None
            else bbox.Merge(b)
        )


    margin = mm(SEARCH_MARGIN_MM)

    bbox.Inflate(
        margin,
        margin,
    )


    # =================================================================
    # 元部品群の周囲にあるトラック / ビアを取得
    # =================================================================

    source_tracks = [
        t
        for t in board.GetTracks()
        if t.GetNetname() in source_nets
        and bbox.Contains(t.GetBoundingBox())
    ]


    print(
        f"複製元フットプリント: "
        f"{list(source_fps.keys())}"
    )

    print(
        f"複製元トラック/ビア数: "
        f"{len(source_tracks)}"
    )


    # =================================================================
    # 円形コピー処理
    # =================================================================

    for copy_index in range(count):

        # -------------------------------------------------------------
        # このコピーの角度
        # -------------------------------------------------------------

        angle_deg = (
            start_angle_deg
            + angle_step_deg * copy_index
        )


        # -------------------------------------------------------------
        # 円周上のコピー基準位置
        # -------------------------------------------------------------

        target_x, target_y = get_circular_position(
            center_x,
            center_y,
            radius_mm,
            angle_deg,
        )


        print("")
        print(
            f"--- コピー {copy_index + 1}/{count} ---"
        )

        print(
            f"角度: {angle_deg:.3f} deg"
        )

        print(
            f"位置: "
            f"({target_x:.3f}, {target_y:.3f}) mm"
        )


        # -------------------------------------------------------------
        # このコピー用の increment
        #
        # 例:
        #   D1  -> D2 -> D3 ...
        #   R1  -> R2 -> R3 ...
        #
        # 元のコードと同じ方式です。
        # -------------------------------------------------------------

        increment = copy_index + 1


        # -------------------------------------------------------------
        # このコピーのネット変換テーブル
        # -------------------------------------------------------------

        new_fps = {}

        net_map = {}


        # =============================================================
        # フットプリント複製
        # =============================================================

        for ref, fp in source_fps.items():

            # ---------------------------------------------------------
            # フットプリントを複製
            # ---------------------------------------------------------

            new_fp = pcbnew.FOOTPRINT(fp)


            # ---------------------------------------------------------
            # 参照番号を更新
            # ---------------------------------------------------------

            new_fp.SetReference(
                new_reference(
                    ref,
                    increment,
                )
            )


            # ---------------------------------------------------------
            # 円形配置
            # ---------------------------------------------------------
            #
            # 元の部品群全体を
            #
            #     円の中心 = center_mm
            #
            # の周囲で angle_deg 回転させます。
            #
            # そのため、部品群内の相対位置関係も維持されます。
            # ---------------------------------------------------------

            source_pos = fp.GetPosition()

            source_x_mm = pcbnew.ToMM(
                source_pos.x
            )

            source_y_mm = pcbnew.ToMM(
                source_pos.y
            )


            if rotate_group:

                new_x_mm, new_y_mm = rotate_point_xy(
                    source_x_mm,
                    source_y_mm,
                    center_x,
                    center_y,
                    angle_deg,
                )

                # 複製したフットプリントは元位置にあるので、
                # 回転後の位置まで移動する。
                dx_mm = new_x_mm - source_x_mm
                dy_mm = new_y_mm - source_y_mm

                new_fp.Move(
                    make_vector(
                        dx_mm,
                        dy_mm,
                    )
                )


                # フットプリント自身の向きも回転。
                #
                # KiCad 9 の FOOTPRINT API には
                # SetOrientationDegrees() が用意されています。
                original_orientation = (
                    fp.GetOrientationDegrees()
                )

                new_fp.SetOrientationDegrees(
                    original_orientation
                    + angle_deg
                )

            else:

                # -----------------------------------------------------
                # グループを回転させない場合
                #
                # 元の部品群の基準位置を
                # 円周上 target_x,target_y に移動します。
                #
                # 基準位置は SOURCE_REFS の最初の部品とします。
                # -----------------------------------------------------

                base_fp = source_fps[SOURCE_REFS[0]]

                base_pos = base_fp.GetPosition()

                base_x_mm = pcbnew.ToMM(
                    base_pos.x
                )

                base_y_mm = pcbnew.ToMM(
                    base_pos.y
                )


                dx_mm = (
                    target_x
                    - base_x_mm
                    + source_x_mm
                    - base_x_mm
                )

                dy_mm = (
                    target_y
                    - base_y_mm
                    + source_y_mm
                    - base_y_mm
                )

                # 上記は基準部品位置からの相対位置を
                # 維持するための移動量。
                #
                # より直接的には:
                # target_base - source_base
                # を全フットプリントに適用する。

                dx_mm = target_x - base_x_mm
                dy_mm = target_y - base_y_mm

                new_fp.Move(
                    make_vector(
                        dx_mm,
                        dy_mm,
                    )
                )


            # ---------------------------------------------------------
            # 基板へ追加
            # ---------------------------------------------------------

            board.Add(new_fp)

            new_fps[ref] = new_fp


        # =============================================================
        # ネットの複製
        # =============================================================

        for ref, fp in source_fps.items():

            new_fp = new_fps[ref]

            for old_pad, new_pad in zip(
                fp.Pads(),
                new_fp.Pads(),
            ):

                old_netname = old_pad.GetNetname()


                # -----------------------------------------------------
                # ネット名がない場合、または共有ネットの場合は
                # そのまま使用する。
                # -----------------------------------------------------

                if (
                    not old_netname
                    or old_netname in SHARED_NET_NAMES
                ):
                    continue


                # -----------------------------------------------------
                # まだ新しいネットを作っていなければ作成
                # -----------------------------------------------------

                if old_netname not in net_map:

                    new_netname = (
                        f"{old_netname}_{increment}"
                    )

                    new_net = pcbnew.NETINFO_ITEM(
                        board,
                        new_netname,
                    )

                    board.Add(new_net)

                    net_map[old_netname] = new_net


                # -----------------------------------------------------
                # 新しいネットをパッドに設定
                # -----------------------------------------------------

                new_pad.SetNet(
                    net_map[old_netname]
                )


        # =============================================================
        # トラック / ビア複製
        # =============================================================

        for t in source_tracks:

            new_t = t.Duplicate()


            if rotate_group:

                # -----------------------------------------------------
                # 部品群と同じように、円の中心を基準に回転
                # -----------------------------------------------------

                try:

                    rotation_angle = make_angle(
                        angle_deg
                    )

                    center_point = make_vector(
                        center_x,
                        center_y,
                    )

                    new_t.Rotate(
                        center_point,
                        rotation_angle,
                    )

                except TypeError:

                    # -------------------------------------------------
                    # 古い KiCad API との互換用。
                    #
                    # KiCad 6/7 系では Rotate() の第2引数が
                    # double の場合があります。
                    # -------------------------------------------------

                    center_point = make_vector(
                        center_x,
                        center_y,
                    )

                    new_t.Rotate(
                        center_point,
                        angle_deg,
                    )

            else:

                # -----------------------------------------------------
                # グループを回転しない場合は、
                # 基準フットプリントと同じ平行移動だけ行う。
                # -----------------------------------------------------

                base_fp = source_fps[SOURCE_REFS[0]]

                base_pos = base_fp.GetPosition()

                base_x_mm = pcbnew.ToMM(
                    base_pos.x
                )

                base_y_mm = pcbnew.ToMM(
                    base_pos.y
                )

                dx_mm = target_x - base_x_mm
                dy_mm = target_y - base_y_mm

                new_t.Move(
                    make_vector(
                        dx_mm,
                        dy_mm,
                    )
                )


            # ---------------------------------------------------------
            # トラックのネットを変更
            # ---------------------------------------------------------

            old_netname = t.GetNetname()

            if old_netname in net_map:

                new_t.SetNet(
                    net_map[old_netname]
                )


            # ---------------------------------------------------------
            # 基板へ追加
            # ---------------------------------------------------------

            board.Add(new_t)


        # =============================================================
        # ログ
        # =============================================================

        print(
            f"セットを複製しました "
            f"(increment={increment}, "
            f"angle={angle_deg:.3f} deg, "
            f"position=({target_x:.3f}, "
            f"{target_y:.3f}) mm)"
        )


        # =============================================================
        # メモリ解放
        # =============================================================

        del new_fps
        del net_map

        gc.collect()


    # =================================================================
    # 接続情報を再構築
    # =================================================================

    print("")
    print("接続情報を再構築中...")

    board.BuildConnectivity()


    # =================================================================
    # 保存
    # =================================================================

    print(
        f"保存中: {OUTPUT_PATH}"
    )

    pcbnew.SaveBoard(
        OUTPUT_PATH,
        board,
    )


    print("")
    print("完了しました。")
    print(
        "KiCad で開いて配置・配線を目視確認してください。"
    )


# =====================================================================
# エントリーポイント
# =====================================================================

if __name__ == "__main__":
    main()
