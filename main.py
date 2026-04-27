import os
import cv2
import time
import yaml
import sys
import ctypes

# 提升 Windows 系统的时钟精度
# 默认情况下，Windows 的 time.sleep() 和 waitKey() 最小精度为 15.6 毫秒。
# 这会导致哪怕 sleep(0.001)，也会被迫等待 15 毫秒，最高只能跑 60 FPS (甚至 30 FPS)。
# 调用 timeBeginPeriod(1) 将系统时钟精度提升到 1 毫秒，能让 FPS 暴涨！
try:
    ctypes.windll.winmm.timeBeginPeriod(1)
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

from src.utils.logger import logger
from src.capture.screen import FastScreenCapture
from src.vision.detector import TargetDetector
from src.control.mouse import MouseController

# 获取项目根目录的绝对路径，确保不论在哪个目录下执行代码都能找到配置
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")

def load_global_config(config_path=DEFAULT_CONFIG_PATH):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"无法加载 {config_path}: {e}")
        return {}

def main():
    logger.info("AimBot 启动中...")
    
    # 1. 加载配置
    config = load_global_config()
    capture_cfg = config.get('capture', {})
    debug_cfg = config.get('debug', {})
    
    width = capture_cfg.get('width', 600)
    height = capture_cfg.get('height', 600)
    fps_limit = capture_cfg.get('fps_limit', 0)
    show_window = debug_cfg.get('show_window', True)
    print_fps = debug_cfg.get('print_fps', True)
    
    # 2. 初始化各个模块 (依赖注入)
    try:
        screen = FastScreenCapture(width=width, height=height)
        detector = TargetDetector(config_path=DEFAULT_CONFIG_PATH)
        mouse = MouseController(config_path=DEFAULT_CONFIG_PATH)
    except Exception as e:
        logger.error(f"模块初始化失败: {e}")
        sys.exit(1)
        
    logger.info(f"所有模块初始化完成. 截取区域: {width}x{height}")
    logger.info("请切换到 Aim Lab。")
    logger.info("-> 按 'T' 键: 开启/暂停自动瞄准")
    logger.info("-> 按 'Q' 键或者在控制台按 Ctrl+C: 彻底退出程序")

    if show_window:
        # 提前创建窗口并强制置顶，防止被其他窗口挡住
        cv2.namedWindow('AimBot Vision Debug', cv2.WINDOW_NORMAL)
        cv2.setWindowProperty('AimBot Vision Debug', cv2.WND_PROP_TOPMOST, 1)

    # 3. 性能统计变量
    fps_time = time.time()
    frames = 0
    
    # 4. 状态控制变量
    is_aimbot_active = False
    prev_t_state = 0
    import win32api
    
    # 5. 主循环
    try:
        while True:
            loop_start = time.time()
            
            # --- 核心流程开始 ---
            
            # A. 捕获画面
            frame = screen.grab()
            if frame is None:
                # 画面未更新（例如游戏正在渲染这一帧的过程中），我们必须跳过！
                # 否则我们会对同一张旧画面重复计算出同样的 dx, dy，并连续发送多次鼠标移动，导致严重超调（抽搐）
                # 稍微 sleep 释放一下 CPU
                time.sleep(0.001)
                continue
            
            # B. 视觉检测 (动态 ROI 优化)
            h, w = frame.shape[:2]
            roi_size = 400
            
            if w > roi_size and h > roi_size:
                # 计算中心切片坐标
                y1 = (h - roi_size) // 2
                y2 = y1 + roi_size
                x1 = (w - roi_size) // 2
                x2 = x1 + roi_size
                
                # 第一阶段：极速处理中心核心区
                roi_frame = frame[y1:y2, x1:x2].copy()  # copy() 防止修改原图导致混乱
                (dx, dy), is_on_target, processed_roi = detector.detect(roi_frame)
                
                if dx == 0 and dy == 0 and not is_on_target:
                    # 如果核心区没找到目标，进入第二阶段：全盘扫描大回退 (Fallback)
                    (dx, dy), is_on_target, processed_frame = detector.detect(frame)
                else:
                    # 将处理后的小图贴回大图，并画一个黄框表示当前正在使用极速扫描区
                    frame[y1:y2, x1:x2] = processed_roi
                    processed_frame = frame
                    cv2.rectangle(processed_frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            else:
                # 截图本来就小于等于 400x400，直接全盘扫描
                (dx, dy), is_on_target, processed_frame = detector.detect(frame)
            
            # 监听 'T' 键 (0x54) 切换自动瞄准状态
            current_t_state = win32api.GetAsyncKeyState(0x54) & 0x8000
            if current_t_state and not prev_t_state:
                is_aimbot_active = not is_aimbot_active
                logger.info(f"【状态切换】自动瞄准已{'开启 (ACTIVE)' if is_aimbot_active else '暂停 (PAUSED)'}")
            prev_t_state = current_t_state

            # C. 鼠标控制 (闭环防空枪模式)
            if is_aimbot_active:
                # 无论是否已经在目标上，永远保持向目标的绝对中心移动
                if dx != 0 or dy != 0:
                    mouse.move(dx, dy)
                    
                if is_on_target:
                    # 准星在目标内部，果断开火
                    mouse.click()
                
            # 全局监听 'Q' 键退出 (即使 OpenCV 窗口没有焦点也能生效)
            if win32api.GetAsyncKeyState(0x51) & 0x8000:
                logger.info("检测到退出按键 'Q' (全局热键)")
                break

            # 调试与显示
            if show_window:
                cv2.imshow('AimBot Vision Debug', processed_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("检测到退出按键 'Q' (OpenCV窗口)")
                    break
            else:
                # 即使不显示窗口，也需要短暂 sleep 防止 CPU 100% 占用
                # (如果使用了 fps_limit 则在后面统一处理)
                if fps_limit <= 0:
                    time.sleep(0.001)
                    
            # 帧率计算
            frames += 1
            if time.time() - fps_time >= 1.0:
                if print_fps:
                    logger.info(f"当前运行帧率: {frames} FPS")
                frames = 0
                fps_time = time.time()
                
            # 帧率限制
            if fps_limit > 0:
                loop_duration = time.time() - loop_start
                target_duration = 1.0 / fps_limit
                if loop_duration < target_duration:
                    time.sleep(target_duration - loop_duration)

    except KeyboardInterrupt:
        logger.info("检测到 Ctrl+C, 正在退出...")
    except Exception as e:
        logger.exception(f"主循环发生未捕获异常: {e}")
    finally:
        # 显式清理资源，防止 DXGI 和 COM 接口在退出时发生 Access Violation
        if 'screen' in locals():
            screen.release()
            
        if show_window:
            cv2.destroyAllWindows()
        logger.info("AimBot 已安全退出.")

if __name__ == '__main__':
    main()
