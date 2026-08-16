# -*- coding: utf-8 -*-

"""
KiCad PCB 円形複製スクリプト
--------------------------------

KiCad の GUI を起動せず、外部から .kicad_pcb を読み書きして、

    ・指定したフットプリント群
    ・その周囲の配線 / ビア

を円形に複製します。

重要:
    この版では TRACK.Rotate() を使用しません。

    各オブジェクトの座標を直接、

        1. 元の基準点からの相対座標を取得
        2. 指定角度だけ回転
        3. 円周上の配置位置に加算

    という方法で変換します。

これにより、KiCad の C++ 側での Rotate() API に依存する
処理をできるだけ避けています。


■ 円形配置

例えば、

    center_mm = (100, 100)
    radius_mm = 50
    start_angle_deg = 0
    angle_step_deg = 30
    count = 12

とすると、

    (150,100)
    (143.3,125)
    ...
    
のように12個を円周上へ配置します。


■ 部品群の基準点

SOURCE_REFS の最初の部品を基準点とします。

例えば、

    SOURCE_REFS = [
        "D1",
        "Rs1",
        "Rs2",
        "U1",
    ]

なら D1 の中心位置が部品群の基準点になります。

D1 が円周上の指定位置に配置され、
Rs1 / Rs2 / U1 は D1 からの相対位置を保ったまま
同じ角度だけ回転します。


■ 参照番号

元の番号に increment を加えます。

例えば、

    D1  -> D2
    Rs1 -> Rs2
    U1  -> U2

となります。


■ ネット

SHARED_NET_NAMES に指定したネットは、
複製後も元と同じネットを使用します。

それ以外は、

    元ネット名_増分

として新しいネットを生成します。


■ 注意

このスクリプトは元ファイルを直接上書きしない設定を
推奨します。

例:

    BOARD_PATH  = ".../prot4.kicad_pcb"
    OUTPUT_PATH = ".../prot4_circular.kicad_pcb"
"""


import gc
import math
import re

import pcbnew


# =====================================================================
# ユーザー設定
# =====================================================================


# ---------------------------------------------------------------------
# 入力ファイル
# ---------------------------------------------------------------------

BOARD_PATH = (
    r"/home/carbonoid/newLine/KiCad/prot4/prot4.kicad_pcb"
)


# ---------------------------------------------------------------------
# 出力ファイル
#
# 元ファイルとは必ず別名にすることを推奨します。
# ---------------------------------------------------------------------

OUTPUT_PATH = (     
    r"/home/carbonoid/newLine/KiCad/prot4/prot4B.kicad_pcb"
)


# ---------------------------------------------------------------------
# 複製対象のフットプリント
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


# =====================================================================
# 円形配置設定
# =====================================================================

CIRCULAR_LAYOUT = {

    # ---------------------------------------------------------------
    # 円の中心座標 [mm]
    # ---------------------------------------------------------------

    "center_mm": (
        500.0,
        500.0,
    ),


    # ---------------------------------------------------------------
    # 円の半径 [mm]
    # ---------------------------------------------------------------

    "radius_mm": 50.0,


    # ---------------------------------------------------------------
    # 最初のコピーの角度 [deg]
    #
    # 0度   = +X方向
    # 90度  = +Y方向
    # ---------------------------------------------------------------

    "start_angle_deg": 90.0,


    # ---------------------------------------------------------------
    # コピー間の角度 [deg]
    #
    # 例:
    #
    # 30度 -> 12個で一周
    # 45度 -> 8個で一周
    # 90度 -> 4個で一周
    # ---------------------------------------------------------------

    "angle_step_deg": 90,


    # ---------------------------------------------------------------
    # コピー数
    # ---------------------------------------------------------------

    "count": 3,
}


# =====================================================================
# 配線検索用マージン
# =====================================================================

"""
SOURCE_REFS のフットプリントを囲む bounding box に対して、
この値 [mm] の余白を追加します。

その範囲に完全に含まれるトラック / ビアを
複製対象とします。
"""

SEARCH_MARGIN_MM = 15.0


# =====================================================================
# 共有ネット
# =====================================================================

"""
ここに記載したネットは、コピー間で共有します。

それ以外のネットはコピーごとに、

    元ネット名_1
    元ネット名_2
    元ネット名_3

のように分離します。
"""

SHARED_NET_NAMES = [
    "GND",
    "VCC",
    "LED_5V",
]


# =====================================================================
# 基本ユーティリティ
# =====================================================================


def mm(value):
    """
    mm -> KiCad 内部単位
    """
    return pcbnew.FromMM(value)


def to_mm(value):
    """
    KiCad 内部単位 -> mm
    """
    return pcbnew.ToMM(value)


def make_vector(dx_mm, dy_mm):
    """
    mm 単位の座標から KiCad の VECTOR2I を生成します。
    古いAPI向けに wxPoint もフォールバックします。
    """

    try:
        return pcbnew.VECTOR2I(
            mm(dx_mm),
            mm(dy_mm),
        )

    except AttributeError:

        return pcbnew.wxPoint(
            mm(dx_mm),
            mm(dy_mm),
        )


# =====================================================================
# 参照番号生成
# =====================================================================


def new_reference(old_ref, increment):
    """
    参照番号末尾の数字だけを increment します。

    例:

        D1  + 1 -> D2
        R7  + 3 -> R10
        C01 + 1 -> C02
    """

    match = re.match(
        r"^([A-Za-z_]+)(\d+)$",
        old_ref,
    )

    if not match:
        raise ValueError(
            f"参照子 '{old_ref}' の形式を解釈できません"
        )

    base = match.group(1)
    num_str = match.group(2)

    new_num = int(num_str) + increment

    return (
        f"{base}"
        f"{str(new_num).zfill(len(num_str))}"
    )


# =====================================================================
# 2次元座標回転
# =====================================================================


def rotate_relative_xy(
    x_mm,
    y_mm,
    angle_deg,
):
    """
    原点を中心として相対座標を回転します。

    入力:
        x_mm
        y_mm
        angle_deg

    出力:
        rotated_x
        rotated_y
    """

    theta = math.radians(angle_deg)

    cos_a = math.cos(theta)
    sin_a = math.sin(theta)

    rotated_x = (
        x_mm * cos_a
        - y_mm * sin_a
    )

    rotated_y = (
        x_mm * sin_a
        + y_mm * cos_a
    )

    return (
        rotated_x,
        rotated_y,
    )


# =====================================================================
# 円周上の座標
# =====================================================================


def circular_position(
    center_x_mm,
    center_y_mm,
    radius_mm,
    angle_deg,
):
    """
    円周上の座標を返します。
    """

    theta = math.radians(angle_deg)

    x_mm = (
        center_x_mm
        + radius_mm * math.cos(theta)
    )

    y_mm = (
        center_y_mm
        + radius_mm * math.sin(theta)
    )

    return (
        x_mm,
        y_mm,
    )


# =====================================================================
# フットプリント座標取得
# =====================================================================


def footprint_position_mm(fp):
    """
    フットプリント位置を mm で取得します。
    """

    pos = fp.GetPosition()

    return (
        to_mm(pos.x),
        to_mm(pos.y),
    )


# =====================================================================
# フットプリント配置
# =====================================================================


def place_footprint(
    new_fp,
    source_fp,
    source_base_x,
    source_base_y,
    target_base_x,
    target_base_y,
    angle_deg,
):
    """
    複製したフットプリントを円形配置します。

    処理:

        元位置
          ↓
        基準点からの相対座標
          ↓
        angle_deg 回転
          ↓
        円周上の基準点を加算
          ↓
        新位置

    さらにフットプリントの向きも
    angle_deg だけ回転します。
    """

    source_x, source_y = (
        footprint_position_mm(source_fp)
    )


    # ---------------------------------------------------------------
    # 基準点からの相対座標
    # ---------------------------------------------------------------

    relative_x = (
        source_x
        - source_base_x
    )

    relative_y = (
        source_y
        - source_base_y
    )


    # ---------------------------------------------------------------
    # 相対座標を回転
    # ---------------------------------------------------------------

    rotated_x, rotated_y = (
        rotate_relative_xy(
            relative_x,
            relative_y,
            angle_deg,
        )
    )


    # ---------------------------------------------------------------
    # 円周上の基準位置へ加算
    # ---------------------------------------------------------------

    new_x = (
        target_base_x
        + rotated_x
    )

    new_y = (
        target_base_y
        + rotated_y
    )


    # ---------------------------------------------------------------
    # 移動量
    #
    # Duplicate() 直後は元フットプリントと
    # 同じ位置にあります。
    # ---------------------------------------------------------------

    dx = new_x - source_x
    dy = new_y - source_y


    # ---------------------------------------------------------------
    # Move()
    # ---------------------------------------------------------------

    new_fp.Move(
        make_vector(
            dx,
            dy,
        )
    )


    # ---------------------------------------------------------------
    # フットプリントの向き
    # ---------------------------------------------------------------

    original_orientation = (
        source_fp.GetOrientationDegrees()
    )

    new_orientation = (
        original_orientation
        + angle_deg
    )

    new_fp.SetOrientationDegrees(
        new_orientation
    )


# =====================================================================
# トラックの座標変換
# =====================================================================


def transform_track(
    new_track,
    source_track,
    source_base_x,
    source_base_y,
    target_base_x,
    target_base_y,
    angle_deg,
):
    """
    TRACK / VIA を円形配置します。

    重要:
        Rotate() は使用しません。

    元オブジェクトの座標を取得し、

        基準点からの相対座標
        -> 回転
        -> 新しい基準点へ移動

    として直接座標を設定します。


    通常の TRACK の場合:

        Start
        End

    の両方を変換します。


    VIA の場合:

        Position

    を変換します。
    """


    # -----------------------------------------------------------------
    # VIA / TRACK の判定
    # -----------------------------------------------------------------

    is_via = isinstance(
        source_track,
        pcbnew.PCB_VIA,
    )


    # -----------------------------------------------------------------
    # VIA
    # -----------------------------------------------------------------

    if is_via:

        pos = source_track.GetPosition()

        source_x = to_mm(pos.x)
        source_y = to_mm(pos.y)


        relative_x = (
            source_x
            - source_base_x
        )

        relative_y = (
            source_y
            - source_base_y
        )


        rotated_x, rotated_y = (
            rotate_relative_xy(
                relative_x,
                relative_y,
                angle_deg,
            )
        )


        new_x = (
            target_base_x
            + rotated_x
        )

        new_y = (
            target_base_y
            + rotated_y
        )


        # Duplicate() 後の位置との差分

        dx = new_x - source_x
        dy = new_y - source_y


        new_track.Move(
            make_vector(
                dx,
                dy,
            )
        )

        return


    # -----------------------------------------------------------------
    # 通常の TRACK
    # -----------------------------------------------------------------

    start = source_track.GetStart()
    end = source_track.GetEnd()


    start_x = to_mm(start.x)
    start_y = to_mm(start.y)

    end_x = to_mm(end.x)
    end_y = to_mm(end.y)


    # -----------------------------------------------------------------
    # Start の相対座標
    # -----------------------------------------------------------------

    start_relative_x = (
        start_x
        - source_base_x
    )

    start_relative_y = (
        start_y
        - source_base_y
    )


    # -----------------------------------------------------------------
    # End の相対座標
    # -----------------------------------------------------------------

    end_relative_x = (
        end_x
        - source_base_x
    )

    end_relative_y = (
        end_y
        - source_base_y
    )


    # -----------------------------------------------------------------
    # Start を回転
    # -----------------------------------------------------------------

    new_start_relative_x, new_start_relative_y = (
        rotate_relative_xy(
            start_relative_x,
            start_relative_y,
            angle_deg,
        )
    )


    # -----------------------------------------------------------------
    # End を回転
    # -----------------------------------------------------------------

    new_end_relative_x, new_end_relative_y = (
        rotate_relative_xy(
            end_relative_x,
            end_relative_y,
            angle_deg,
        )
    )


    # -----------------------------------------------------------------
    # 新しい絶対座標
    # -----------------------------------------------------------------

    new_start_x = (
        target_base_x
        + new_start_relative_x
    )

    new_start_y = (
        target_base_y
        + new_start_relative_y
    )

    new_end_x = (
        target_base_x
        + new_end_relative_x
    )

    new_end_y = (
        target_base_y
        + new_end_relative_y
    )


    # -----------------------------------------------------------------
    # Duplicate() 直後の座標との差分
    # -----------------------------------------------------------------

    dx_start = (
        new_start_x
        - start_x
    )

    dy_start = (
        new_start_y
        - start_y
    )

    dx_end = (
        new_end_x
        - end_x
    )

    dy_end = (
        new_end_y
        - end_y
    )


    # -----------------------------------------------------------------
    # TRACK の座標設定
    #
    # SetStart / SetEnd が利用可能な場合は直接設定します。
    # -----------------------------------------------------------------

    try:

        new_track.SetStart(
            make_vector(
                new_start_x,
                new_start_y,
            )
        )

        new_track.SetEnd(
            make_vector(
                new_end_x,
                new_end_y,
            )
        )

    except AttributeError:

        # -------------------------------------------------------------
        # 古いAPI向けフォールバック
        # -------------------------------------------------------------

        # 始点と終点の移動量が異なる場合、
        # Move() だけでは対応できないため、
        # エラーとして停止します。
        #
        # 中途半端に処理を続けて基板を破壊するより安全です。

        if (
            abs(dx_start - dx_end) > 1e-9
            or abs(dy_start - dy_end) > 1e-9
        ):
            raise RuntimeError(
                "TRACK の SetStart()/SetEnd() API が "
                "利用できないため、回転配置できません。"
            )

        new_track.Move(
            make_vector(
                dx_start,
                dy_start,
            )
        )


# =====================================================================
# メイン
# =====================================================================


def main():

    print("")
    print("========================================")
    print(" KiCad 円形複製スクリプト")
    print("========================================")
    print("")


    # =================================================================
    # 設定値
    # =================================================================

    center_x, center_y = (
        CIRCULAR_LAYOUT["center_mm"]
    )

    radius_mm = (
        CIRCULAR_LAYOUT["radius_mm"]
    )

    start_angle_deg = (
        CIRCULAR_LAYOUT["start_angle_deg"]
    )

    angle_step_deg = (
        CIRCULAR_LAYOUT["angle_step_deg"]
    )

    count = (
        CIRCULAR_LAYOUT["count"]
    )


    # =================================================================
    # 設定チェック
    # =================================================================

    if count <= 0:

        raise ValueError(
            "count は 1 以上にしてください。"
        )


    if radius_mm < 0:

        raise ValueError(
            "radius_mm は 0 以上にしてください。"
        )


    if len(SOURCE_REFS) == 0:

        raise ValueError(
            "SOURCE_REFS が空です。"
        )


    # =================================================================
    # ファイルチェック
    # =================================================================

    if BOARD_PATH == OUTPUT_PATH:

        raise ValueError(
            "BOARD_PATH と OUTPUT_PATH が同じです。\n"
            "テスト中は元ファイルを上書きしないことを推奨します。"
        )


    # =================================================================
    # 基板読み込み
    # =================================================================

    print(
        f"読み込み中:\n{BOARD_PATH}"
    )

    board = pcbnew.LoadBoard(
        BOARD_PATH
    )


    if board is None:

        raise RuntimeError(
            "基板を読み込めませんでした。"
        )


    print(
        "基板を読み込みました。"
    )


    # =================================================================
    # フットプリント検索
    # =================================================================

    def get_footprint(ref):

        fp = board.FindFootprintByReference(
            ref
        )

        if fp is None:

            raise ValueError(
                f"フットプリント '{ref}' が見つかりません。"
            )

        return fp


    source_fps = {
        ref: get_footprint(ref)
        for ref in SOURCE_REFS
    }


    # =================================================================
    # 部品群の基準フットプリント
    # =================================================================

    base_ref = SOURCE_REFS[0]

    base_fp = source_fps[base_ref]

    source_base_x, source_base_y = (
        footprint_position_mm(base_fp)
    )


    print("")
    print("複製元:")
    print(
        f"  基準部品 : {base_ref}"
    )

    print(
        f"  基準位置 : "
        f"({source_base_x:.4f}, "
        f"{source_base_y:.4f}) mm"
    )


    # =================================================================
    # 使用ネットを収集
    # =================================================================

    source_nets = set()


    for fp in source_fps.values():

        for pad in fp.Pads():

            netname = pad.GetNetname()

            if netname:

                source_nets.add(
                    netname
                )


    print(
        f"使用ネット数: "
        f"{len(source_nets)}"
    )


    # =================================================================
    # 配線検索用 bounding box
    # =================================================================

    bbox = None


    for fp in source_fps.values():

        current_bbox = (
            fp.GetBoundingBox()
        )

        if bbox is None:

            bbox = current_bbox

        else:

            bbox = bbox.Merge(
                current_bbox
            )


    margin = mm(
        SEARCH_MARGIN_MM
    )

    bbox.Inflate(
        margin,
        margin,
    )


    # =================================================================
    # 配線取得
    # =================================================================

    source_tracks = []


    for track in board.GetTracks():

        netname = (
            track.GetNetname()
        )


        if netname not in source_nets:

            continue


        if not bbox.Contains(
            track.GetBoundingBox()
        ):

            continue


        source_tracks.append(
            track
        )


    print(
        f"複製元トラック/ビア数: "
        f"{len(source_tracks)}"
    )


    # =================================================================
    # 円形コピー
    # =================================================================

    for copy_index in range(count):

        # -------------------------------------------------------------
        # increment
        # -------------------------------------------------------------

        increment = (
            copy_index + 1
        )


        # -------------------------------------------------------------
        # 角度
        # -------------------------------------------------------------

        angle_deg = (
            start_angle_deg
            + angle_step_deg
            * copy_index
        )


        # -------------------------------------------------------------
        # 円周上の基準位置
        # -------------------------------------------------------------

        target_base_x, target_base_y = (
            circular_position(
                center_x,
                center_y,
                radius_mm,
                angle_deg,
            )
        )


        print("")
        print(
            "----------------------------------------"
        )

        print(
            f"コピー {copy_index + 1}/{count}"
        )

        print(
            f"  increment : {increment}"
        )

        print(
            f"  angle     : "
            f"{angle_deg:.4f} deg"
        )

        print(
            f"  position  : "
            f"({target_base_x:.4f}, "
            f"{target_base_y:.4f}) mm"
        )


        # -------------------------------------------------------------
        # 新しいフットプリント
        # -------------------------------------------------------------

        new_fps = {}


        # =============================================================
        # フットプリント複製
        # =============================================================

        for ref, source_fp in source_fps.items():

            print(
                f"  FP: {ref}"
            )


            # ---------------------------------------------------------
            # コピー
            # ---------------------------------------------------------

            new_fp = pcbnew.FOOTPRINT(
                source_fp
            )


            # ---------------------------------------------------------
            # 参照番号
            # ---------------------------------------------------------

            new_ref = new_reference(
                ref,
                increment,
            )

            new_fp.SetReference(
                new_ref
            )


            # ---------------------------------------------------------
            # 円形配置
            # ---------------------------------------------------------

            place_footprint(
                new_fp,
                source_fp,
                source_base_x,
                source_base_y,
                target_base_x,
                target_base_y,
                angle_deg,
            )


            # ---------------------------------------------------------
            # 基板へ追加
            # ---------------------------------------------------------

            board.Add(
                new_fp
            )


            new_fps[ref] = new_fp


        # =============================================================
        # ネット複製
        # =============================================================

        net_map = {}


        for ref, source_fp in source_fps.items():

            new_fp = new_fps[ref]


            for old_pad, new_pad in zip(
                source_fp.Pads(),
                new_fp.Pads(),
            ):

                old_netname = (
                    old_pad.GetNetname()
                )


                # -----------------------------------------------------
                # ネットなし
                # -----------------------------------------------------

                if not old_netname:

                    continue


                # -----------------------------------------------------
                # 共有ネット
                # -----------------------------------------------------

                if (
                    old_netname
                    in SHARED_NET_NAMES
                ):

                    continue


                # -----------------------------------------------------
                # 新しいネット生成
                # -----------------------------------------------------

                if (
                    old_netname
                    not in net_map
                ):

                    new_netname = (
                        f"{old_netname}_{increment}"
                    )


                    new_net = (
                        pcbnew.NETINFO_ITEM(
                            board,
                            new_netname,
                        )
                    )


                    board.Add(
                        new_net
                    )


                    net_map[
                        old_netname
                    ] = new_net


                # -----------------------------------------------------
                # パッドに新ネット設定
                # -----------------------------------------------------

                new_pad.SetNet(
                    net_map[
                        old_netname
                    ]
                )


        # =============================================================
        # トラック / ビア複製
        # =============================================================

        for track_index, source_track in enumerate(
            source_tracks
        ):

            new_track = (
                source_track.Duplicate()
            )


            # ---------------------------------------------------------
            # 座標変換
            #
            # Rotate() は使用しません。
            # ---------------------------------------------------------

            transform_track(
                new_track,
                source_track,
                source_base_x,
                source_base_y,
                target_base_x,
                target_base_y,
                angle_deg,
            )


            # ---------------------------------------------------------
            # ネット変換
            # ---------------------------------------------------------

            old_netname = (
                source_track.GetNetname()
            )


            if (
                old_netname
                in net_map
            ):

                new_track.SetNet(
                    net_map[
                        old_netname
                    ]
                )


            # ---------------------------------------------------------
            # 基板へ追加
            # ---------------------------------------------------------

            board.Add(
                new_track
            )


        # =============================================================
        # コピー完了
        # =============================================================

        print(
            f"コピー {copy_index + 1} 完了"
        )


        # =============================================================
        # メモリ解放
        # =============================================================

        del new_fps
        del net_map

        gc.collect()


    # =================================================================
    # BuildConnectivity は実行しない
    # =================================================================
    #
    # 以前のコードではここで
    #
    #     board.BuildConnectivity()
    #
    # を実行していました。
    #
    # KiCad GUI内で実行した場合のクラッシュ切り分けを
    # 優先するため、この版では意図的に実行しません。
    #
    # 保存されたPCBはKiCadで開いた際に必要に応じて
    # 接続情報が再構築されます。
    # =================================================================

    print("")
    print(
        "BuildConnectivity() はスキップします。"
    )


    # =================================================================
    # 保存
    # =================================================================

    print("")
    print(
        f"保存中:\n{OUTPUT_PATH}"
    )


    pcbnew.SaveBoard(
        OUTPUT_PATH,
        board,
    )


    print("")
    print(
        "========================================"
    )

    print(
        "完了しました。"
    )

    print(
        f"出力ファイル:\n{OUTPUT_PATH}"
    )

    print(
        "========================================"
    )


# =====================================================================
# エントリーポイント
# =====================================================================

if __name__ == "__main__":

    main()