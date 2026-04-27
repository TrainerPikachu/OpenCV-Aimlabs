import cv2
import numpy as np
import dxcam
import win32api
import win32con
import time
from src.utils.logger import logger

class FastScreenCapture:
    def __init__(self, width=1200, height=1200):
        """
        初始化 DXGI 截图类，使用 dxcam 进行 GPU 级抓取。
        """
        # 获取系统屏幕物理分辨率
        self.screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        self.screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        
        # 计算中心截取区域的坐标
        self.w = width
        self.h = height
        left = (self.screen_w - self.w) // 2
        top = (self.screen_h - self.h) // 2
        right = left + self.w
        bottom = top + self.h
        
        self.region = (left, top, right, bottom)
        
        # 创建 DXGI 相机实例，直接输出 BGR 格式给 OpenCV 使用
        try:
            self.camera = dxcam.create(output_color="BGR")
            logger.info(f"DXGI 截图模块初始化成功，捕获区域: {self.region}")
        except Exception as e:
            logger.error(f"DXGI 初始化失败，可能不支持独占全屏或系统版本过低: {e}")
            raise e

        # 缓存上一帧画面，因为 DXGI 在画面静止时会返回 None
        # 初始化一个黑色占位图防止启动时报错
        self.last_frame = np.zeros((self.h, self.w, 3), dtype=np.uint8)

    def grab(self):
        """
        执行截图并返回适用于 OpenCV 的 numpy 数组
        """
        # 从显存高速抓取
        frame = self.camera.grab(region=self.region)
        
        # DXGI 机制：如果屏幕相比上一帧没有任何像素改变，则返回 None。
        # 这里我们直接返回 None 给主程序，让主程序跳过这一帧的判断，
        # 防止重复处理同一张静止画面导致“鼠标重复移动（抽搐/抖动）”！
        if frame is not None:
            self.last_frame = frame
            
        return frame

    def release(self):
        """
        显式释放 DXGI 资源，防止 Python 退出时发生 comtypes 访问冲突 (Access Violation)
        """
        if hasattr(self, 'camera') and self.camera is not None:
            try:
                self.camera.release()
            except Exception:
                pass
            self.camera = None

    def __del__(self):
        # 尽量在主程序结束时调用 release()，避免依赖析构函数
        pass

# ==========================================
# 测试与运行
# ==========================================
if __name__ == '__main__':
    # 实例化截图器
    capture = FastScreenCapture(width=1200, height=1200)
    
    # 用于计算 FPS 的变量
    fps_time = time.time()
    frames = 0

    print("开始 DXGI 捕获。按 'Q' 键退出。")

    while True:
        # 1. 抓取画面
        frame = capture.grab()

        # 2. 计算并显示 FPS
        frames += 1
        if time.time() - fps_time >= 1.0:
            print(f"当前 DXGI 捕获帧率: {frames} FPS")
            frames = 0
            fps_time = time.time()

        # 3. 实时显示
        cv2.imshow('DXGI Capture Test', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()