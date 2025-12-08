import pygame
import sys
import time
import datetime
import csv 
import math
import os 
import matplotlib.pyplot as plt 
import matplotlib.image as mpimg
import numpy as np 
from typing import Dict, Any, Final

# =============================================================================
# 0. 定数定義クラス
# =============================================================================

class CourseConstants:
    """画像のピクセルを基準にすべてのスケールを定義する"""
    
    # --- 1. ハードウェア設定 ---
    DPI_SETTING: Final[int] = 800              
    POLLING_RATE: Final[int] = 1000
    
    # 1ミッキーが何センチか (0.003175 cm)
    MICKEY_TO_CM: Final[float] = 1/DPI_SETTING * 2.54      
    
    # --- 2. 画像と現実の対応 ---
    # 画像1000px = 現実1000cm なので 1.0
    CM_PER_PIXEL: Final[float] = 1.0 
    
    # ミッキー -> ピクセル変換係数
    MICKEY_TO_PIXEL: Final[float] = MICKEY_TO_CM / CM_PER_PIXEL

    # --- 3. スタート地点 (画像上のピクセル座標) ---
    START_PX_X: Final[int] = 500  # 中心
    START_PX_Y: Final[int] = 273  # 中心


# =============================================================================
# 1. 初期化 (Setup) - ★画像自動選択ロジック追加★
# =============================================================================

def _setup_context(args: list) -> Dict[str, Any]:
    if len(args) < 2:
        raise ValueError("エラー: マウス名を引数として指定してください。\n実行例: py script.py G304_Test")
    mouse_name = args[1]
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    LOG_ROOT_DIR = os.path.join(BASE_DIR, "Log")
    
    # --- 画像ファイルの自動検索ロジック ---
    # ルール: "CourseImage" で始まり、".jpg" または ".jpeg" で終わるファイル
    image_candidates = []
    try:
        for f in os.listdir(BASE_DIR):
            if f.startswith("CourseImage") and (f.lower().endswith(".jpg") or f.lower().endswith(".jpeg")):
                image_candidates.append(os.path.join(BASE_DIR, f))
    except FileNotFoundError:
        pass

    if image_candidates:
        # 名前順で降順ソート（日付が入っていれば最新が先頭に来る想定）
        image_candidates.sort(reverse=True)
        image_path = image_candidates[0]
    else:
        # 見つからない場合はデフォルト名（後のチェックでエラーになる）
        image_path = os.path.join(BASE_DIR, "CourseImage.jpg")

    
    MOUSE_DIR = os.path.join(LOG_ROOT_DIR, mouse_name)
    OUTPUT_DIR = os.path.join(MOUSE_DIR, f"{mouse_name}_{timestamp}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    raw_log_path = os.path.join(OUTPUT_DIR, "raw_data.log")
    analysis_log_path = os.path.join(OUTPUT_DIR, "analyze.log")
    plot_path = os.path.join(OUTPUT_DIR, "trajectory_plot.png")
    
    context = {
        'output_dir': OUTPUT_DIR, 'mouse_name': mouse_name, 'timestamp': timestamp, 
        'image_path': image_path, 'raw_log_path': raw_log_path, 'analysis_log_path': analysis_log_path,
        'plot_path': plot_path, 'final_total_mickey_distance': 0.0
    }
    return context

def _initialize_pygame(context: Dict[str, Any]) -> pygame.Surface:
    pygame.init()
    screen = pygame.display.set_mode((400, 300))
    pygame.display.set_caption(f"Mickey Logger (DPI: {CourseConstants.DPI_SETTING})")
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    print("=" * 70); print(f"✅ 計測開始 (DPI: {CourseConstants.DPI_SETTING})"); print(f"📂 保存先: {context['output_dir']}"); 
    
    # 画像の状態を表示
    img_name = os.path.basename(context['image_path'])
    if os.path.exists(context['image_path']): 
        print(f"🖼️ 背景画像: {img_name} を使用します")
    else: 
        print(f"⚠️ 背景画像: 見つかりません！ (検索条件: CourseImage*.jpg)")
    
    print("終了するにはウィンドウをアクティブにして [ESC] キー を押してください。")
    print("=" * 70)
    return screen


# =============================================================================
# 2. 生データ取得 (Acquire) - 高速化版
# =============================================================================

def acquire_raw_data(context: Dict[str, Any], screen: pygame.Surface):
    raw_log_path = context['raw_log_path']
    total_x = 0
    total_y = 0
    font = pygame.font.Font(None, 24)
    data_buffer = []
    BUFFER_SIZE = 5000 
    clock = pygame.time.Clock()
    running = True
    start_time = time.time()
    frame_count = 0 
    
    try:
        with open(raw_log_path, 'w', newline='') as log_file:
            log_file.write("Timestamp_s,Rel_X,Rel_Y,Total_X,Total_Y\n")
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: running = False
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: running = False

                dx, dy = pygame.mouse.get_rel()

                if dx != 0 or dy != 0:
                    total_x += dx
                    total_y += dy
                    elapsed = time.time() - start_time
                    data_buffer.append(f"{elapsed:.4f},{dx},{dy},{total_x},{total_y}\n")

                if len(data_buffer) >= BUFFER_SIZE:
                    log_file.writelines(data_buffer)
                    data_buffer.clear()

                frame_count += 1
                if frame_count % 15 == 0:
                    screen.fill((20, 20, 30))
                    text = font.render(f"Mickey: ({total_x}, {total_y})", True, (0, 255, 0))
                    screen.blit(text, (10, 10))
                    pygame.display.flip()
                    frame_count = 0
                
                clock.tick(CourseConstants.POLLING_RATE)
            
            if data_buffer:
                log_file.writelines(data_buffer)

    except Exception as e:
        print(f"\n❌ データ取得中にエラー: {e}")
    finally:
        context['final_total_x'] = total_x
        context['final_total_y'] = total_y


# =============================================================================
# 3. データ解析 (Analyze)
# =============================================================================

def analyze_raw_data(context: Dict[str, Any]):
    raw_path = context['raw_log_path']; analyze_path = context['analysis_log_path']; total_dist = 0.0;
    if not os.path.exists(raw_path): print("⚠️ 生データファイルが見つからないため、解析をスキップします。"); return
    try:
        with open(analyze_path, 'w', newline='') as outfile:
            writer = csv.writer(outfile); writer.writerow(['Timestamp_s', 'Rel_X', 'Rel_Y', 'Distance_Mickey', 'Angle_deg'])
            with open(raw_path, 'r', newline='') as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    dx = float(row['Rel_X']); dy = float(row['Rel_Y']); ts = float(row['Timestamp_s']);
                    dist = math.sqrt(dx**2 + dy**2); total_dist += dist; angle = math.degrees(math.atan2(dy, dx))
                    writer.writerow([f"{ts:.4f}", f"{dx:.0f}", f"{dy:.0f}", f"{dist:.3f}", f"{angle:.1f}"])
        context['final_total_mickey_distance'] = total_dist; print(f"📊 解析完了: 総移動距離 {total_dist:.2f} Mickey")
    except Exception as e: print(f"\n❌ 解析中にエラー: {e}")


# =============================================================================
# 4. 結果図示 (Plot) - 画像ファースト
# =============================================================================

def plot_analysis_results(context: Dict[str, Any]):
    analyze_path = context['analysis_log_path']
    plot_path = context['plot_path']
    image_path = context['image_path']
    
    if not os.path.exists(analyze_path): return

    # 画像上のスタート地点
    curr_x = CourseConstants.START_PX_X
    curr_y = CourseConstants.START_PX_Y
    
    x_plot = [curr_x]
    y_plot = [curr_y]
    
    try:
        with open(analyze_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dx_m = float(row['Rel_X'])
                dy_m = float(row['Rel_Y'])
                
                # Mickey -> Pixel
                dx_px = dx_m * CourseConstants.MICKEY_TO_PIXEL
                dy_px = dy_m * CourseConstants.MICKEY_TO_PIXEL
                
                # Global X (Left/Right) = +dy_px (負の値なら左へ)
                delta_global_x = dy_px 
                
                # Global Y (Up/Down) = -dx_px (正の値なら負(上)へ)
                delta_global_y = -dx_px 
                
                curr_x += delta_global_x
                curr_y += delta_global_y
                x_plot.append(curr_x); y_plot.append(curr_y)

        # --- 描画 ---
        if os.path.exists(image_path):
            img = mpimg.imread(image_path)
            h, w = img.shape[:2]
        else:
            img = None; w, h = 1000, 546

        dpi = 100
        fig, ax = plt.subplots(figsize=(w/dpi, h/dpi), dpi=dpi)

        if img is not None:
            ax.imshow(img)
        else:
            ax.set_xlim(0, w); ax.set_ylim(h, 0)

        ax.plot(x_plot, y_plot, label='Trajectory', color='red', linewidth=2)
        ax.scatter(x_plot[0], y_plot[0], color='lime', s=150, label='Start', edgecolors='black', zorder=5)
        ax.scatter(x_plot[-1], y_plot[-1], color='blue', marker='x', s=150, label='End', zorder=5)
        
        ax.set_title(f"Trajectory Overlay (Total: {context['final_total_mickey_distance']:.0f} Mickey)")
        ax.axis('off')
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        plt.savefig(plot_path, bbox_inches='tight', pad_inches=0.1)
        plt.close()
        print(f"🖼️ 軌跡図保存完了: {plot_path}")

    except Exception as e: print(f"\n❌ プロット中にエラー: {e}")

# =============================================================================
# 5. メイン実行
# =============================================================================
def main():
    try:
        context = _setup_context(sys.argv)
        screen = _initialize_pygame(context)
        acquire_raw_data(context, screen)
        pygame.quit() 
        analyze_raw_data(context)
        plot_analysis_results(context)
        print("-" * 70); print("🎉 全工程完了！")
    except ValueError as e: print(f"エラー: {e}")
    except Exception as e: print(f"予期せぬエラー: {e}")
    finally:
        if pygame.get_init(): pygame.quit()

if __name__ == "__main__":
    main()


# import pygame
# import sys
# import time
# import datetime
# import csv 
# import math
# import os 
# import matplotlib.pyplot as plt 
# import matplotlib.image as mpimg
# import numpy as np 
# from typing import Dict, Any, Final

# # =============================================================================
# # 0. 定数定義クラス
# # =============================================================================

# class CourseConstants:
#     """画像のピクセルを基準にすべてのスケールを定義する"""
    
#     # --- 1. ハードウェア設定 ---
#     DPI_SETTING: Final[int] = 800              
#     POLLING_RATE: Final[int] = 1000
    
#     # 1ミッキーが何センチか (0.003175 cm)
#     MICKEY_TO_CM: Final[float] = 1/DPI_SETTING * 2.54      
    
#     # --- 2. 画像と現実の対応 ---
#     # 画像1000px = 現実1000cm なので 1.0
#     CM_PER_PIXEL: Final[float] = 1.0 
    
#     # ミッキー -> ピクセル変換係数
#     MICKEY_TO_PIXEL: Final[float] = MICKEY_TO_CM / CM_PER_PIXEL

#     # --- 3. スタート地点 (画像上のピクセル座標) ---
#     START_PX_X: Final[int] = 500  # 画像の中心
#     START_PX_Y: Final[int] = 273  # 画像の中心


# # =============================================================================
# # 1. 初期化 (Setup)
# # =============================================================================

# def _setup_context(args: list) -> Dict[str, Any]:
#     if len(args) < 2:
#         raise ValueError("エラー: マウス名を引数として指定してください。\n実行例: py script.py G304_Test")
#     mouse_name = args[1]
#     timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
#     BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#     LOG_ROOT_DIR = os.path.join(BASE_DIR, "Log")
#     image_path = os.path.join(BASE_DIR, "CourseImage.jpg")
#     MOUSE_DIR = os.path.join(LOG_ROOT_DIR, mouse_name)
#     OUTPUT_DIR = os.path.join(MOUSE_DIR, f"{mouse_name}_{timestamp}")
#     os.makedirs(OUTPUT_DIR, exist_ok=True)
#     raw_log_path = os.path.join(OUTPUT_DIR, "raw_data.log")
#     analysis_log_path = os.path.join(OUTPUT_DIR, "analyze.log")
#     plot_path = os.path.join(OUTPUT_DIR, "trajectory_plot.png")
#     context = {
#         'output_dir': OUTPUT_DIR, 'mouse_name': mouse_name, 'timestamp': timestamp, 
#         'image_path': image_path, 'raw_log_path': raw_log_path, 'analysis_log_path': analysis_log_path,
#         'plot_path': plot_path, 'final_total_mickey_distance': 0.0
#     }
#     return context

# def _initialize_pygame(context: Dict[str, Any]) -> pygame.Surface:
#     pygame.init()
#     screen = pygame.display.set_mode((400, 300))
#     pygame.display.set_caption(f"Mickey Logger (DPI: {CourseConstants.DPI_SETTING})")
#     pygame.event.set_grab(True)
#     pygame.mouse.set_visible(False)
#     print("=" * 70); print(f"✅ 計測開始 (DPI: {CourseConstants.DPI_SETTING})"); print(f"📂 保存先: {context['output_dir']}"); 
#     if os.path.exists(context['image_path']): print("🖼️ 背景画像: 見つかりました")
#     else: print("⚠️ 背景画像: 見つかりません！ 'CourseImage.jpg'を配置してください。")
#     print("終了するにはウィンドウをアクティブにして [ESC] キー を押してください。")
#     print("=" * 70)
#     return screen


# # =============================================================================
# # 2. 生データ取得 (Acquire) - 高速化版
# # =============================================================================

# def acquire_raw_data(context: Dict[str, Any], screen: pygame.Surface):
#     """メインループ: メモリバッファリングと描画間引きによる高速化"""
#     raw_log_path = context['raw_log_path']
#     total_x = 0
#     total_y = 0
    
#     # 高速化: ループ外生成
#     font = pygame.font.Font(None, 24)
#     data_buffer = []
#     BUFFER_SIZE = 5000 
    
#     clock = pygame.time.Clock()
#     running = True
#     start_time = time.time()
#     frame_count = 0 
    
#     try:
#         with open(raw_log_path, 'w', newline='') as log_file:
#             log_file.write("Timestamp_s,Rel_X,Rel_Y,Total_X,Total_Y\n")
            
#             while running:
#                 # 1. イベント処理
#                 for event in pygame.event.get():
#                     if event.type == pygame.QUIT: running = False
#                     elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: running = False

#                 # 2. データ取得 (最速)
#                 dx, dy = pygame.mouse.get_rel()

#                 if dx != 0 or dy != 0:
#                     total_x += dx
#                     total_y += dy
#                     elapsed = time.time() - start_time
#                     # メモリへのバッファリングのみ
#                     data_buffer.append(f"{elapsed:.4f},{dx},{dy},{total_x},{total_y}\n")

#                 # バッファ書き出し
#                 if len(data_buffer) >= BUFFER_SIZE:
#                     log_file.writelines(data_buffer)
#                     data_buffer.clear()

#                 # 3. 描画 (10回に1回のみ実行)
#                 frame_count += 1
#                 if frame_count % 10 == 0:
#                     screen.fill((20, 20, 30))
#                     text = font.render(f"Mickey: ({total_x}, {total_y})", True, (0, 255, 0))
#                     screen.blit(text, (10, 10))
#                     pygame.display.flip()
#                     frame_count = 0
                
#                 clock.tick(CourseConstants.POLLING_RATE)
            
#             # 残りのデータを書き込み
#             if data_buffer:
#                 log_file.writelines(data_buffer)

#     except Exception as e:
#         print(f"\n❌ データ取得中にエラー: {e}")
#     finally:
#         context['final_total_x'] = total_x
#         context['final_total_y'] = total_y


# # =============================================================================
# # 3. データ解析 (Analyze)
# # =============================================================================

# def analyze_raw_data(context: Dict[str, Any]):
#     raw_path = context['raw_log_path']; analyze_path = context['analysis_log_path']; total_dist = 0.0;
#     if not os.path.exists(raw_path): print("⚠️ 生データファイルが見つからないため、解析をスキップします。"); return
#     try:
#         with open(analyze_path, 'w', newline='') as outfile:
#             writer = csv.writer(outfile); writer.writerow(['Timestamp_s', 'Rel_X', 'Rel_Y', 'Distance_Mickey', 'Angle_deg'])
#             with open(raw_path, 'r', newline='') as infile:
#                 reader = csv.DictReader(infile)
#                 for row in reader:
#                     dx = float(row['Rel_X']); dy = float(row['Rel_Y']); ts = float(row['Timestamp_s']);
#                     dist = math.sqrt(dx**2 + dy**2); total_dist += dist; angle = math.degrees(math.atan2(dy, dx))
#                     writer.writerow([f"{ts:.4f}", f"{dx:.0f}", f"{dy:.0f}", f"{dist:.3f}", f"{angle:.1f}"])
#         context['final_total_mickey_distance'] = total_dist; print(f"📊 解析完了: 総移動距離 {total_dist:.2f} Mickey")
#     except Exception as e: print(f"\n❌ 解析中にエラー: {e}")


# # =============================================================================
# # 4. 結果図示 (Plot) - 方向修正済み
# # =============================================================================

# def plot_analysis_results(context: Dict[str, Any]):
#     analyze_path = context['analysis_log_path']
#     plot_path = context['plot_path']
#     image_path = context['image_path']
    
#     if not os.path.exists(analyze_path): return

#     # 画像上のスタート地点
#     curr_x = CourseConstants.START_PX_X
#     curr_y = CourseConstants.START_PX_Y
    
#     x_plot = [curr_x]
#     y_plot = [curr_y]
    
#     try:
#         with open(analyze_path, 'r', newline='') as f:
#             reader = csv.DictReader(f)
#             for row in reader:
#                 dx_m = float(row['Rel_X'])
#                 dy_m = float(row['Rel_Y'])
                
#                 # Mickey -> Pixel
#                 dx_px = dx_m * CourseConstants.MICKEY_TO_PIXEL
#                 dy_px = dy_m * CourseConstants.MICKEY_TO_PIXEL
                
#                 # --- 方向変換ロジック (dx修正版) ---
#                 # 前進 (dy_px < 0) -> 地図左 (-X) : OK
#                 # 右折 (dx_px > 0) -> 地図上 (-Y) : ★ここを修正 (+dx_px -> -dx_px)
                
#                 # Global X (左/右) = +dy_px (負の値なら左へ)
#                 delta_global_x = dy_px 
                
#                 # Global Y (上/下) = -dx_px (正の値なら負(上)へ)
#                 delta_global_y = -dx_px 
                
#                 curr_x += delta_global_x
#                 curr_y += delta_global_y
#                 x_plot.append(curr_x); y_plot.append(curr_y)

#         # --- 描画 ---
#         if os.path.exists(image_path):
#             img = mpimg.imread(image_path)
#             h, w = img.shape[:2]
#         else:
#             img = None; w, h = 1000, 546

#         dpi = 100
#         fig, ax = plt.subplots(figsize=(w/dpi, h/dpi), dpi=dpi)

#         if img is not None:
#             ax.imshow(img)
#         else:
#             ax.set_xlim(0, w); ax.set_ylim(h, 0)

#         ax.plot(x_plot, y_plot, label='Trajectory', color='red', linewidth=2)
#         ax.scatter(x_plot[0], y_plot[0], color='lime', s=150, label='Start', edgecolors='black', zorder=5)
#         ax.scatter(x_plot[-1], y_plot[-1], color='blue', marker='x', s=150, label='End', zorder=5)
        
#         ax.set_title(f"Trajectory Overlay (Total: {context['final_total_mickey_distance']:.0f} Mickey)")
#         ax.axis('off')
#         plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
#         plt.savefig(plot_path, bbox_inches='tight', pad_inches=0.1)
#         plt.close()
#         print(f"🖼️ 軌跡図保存完了: {plot_path}")

#     except Exception as e: print(f"\n❌ プロット中にエラー: {e}")

# # =============================================================================
# # 5. メイン実行
# # =============================================================================
# def main():
#     try:
#         context = _setup_context(sys.argv)
#         screen = _initialize_pygame(context)
#         acquire_raw_data(context, screen)
#         pygame.quit() 
#         analyze_raw_data(context)
#         plot_analysis_results(context)
#         print("-" * 70); print("🎉 全工程完了！")
#     except ValueError as e: print(f"エラー: {e}")
#     except Exception as e: print(f"予期せぬエラー: {e}")
#     finally:
#         if pygame.get_init(): pygame.quit()

# if __name__ == "__main__":
#     main()