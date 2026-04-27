import cv2
import numpy as np
import yaml
from src.utils.logger import logger

class TargetDetector:
    def __init__(self, config_path="config.yaml"):
        """
        初始化视觉识别模块，加载配置文件中的 HSV 阈值和面积阈值。
        """
        self._load_config(config_path)

    def _load_config(self, config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                vision_cfg = config.get('vision', {})
                
                # 获取 HSV 颜色阈值
                self.lower_color = np.array(vision_cfg.get('hsv_lower', [80, 100, 100]), dtype=np.uint8)
                self.upper_color = np.array(vision_cfg.get('hsv_upper', [100, 255, 255]), dtype=np.uint8)
                
                # 获取面积阈值
                self.min_area = vision_cfg.get('min_contour_area', 50)
                self.max_area = vision_cfg.get('max_contour_area', 5000)
                
                logger.info("视觉模块配置加载成功")
                logger.debug(f"HSV Lower: {self.lower_color}, HSV Upper: {self.upper_color}")
        except Exception as e:
            logger.error(f"加载配置文件失败，使用默认值: {e}")
            self.lower_color = np.array([80, 100, 100], dtype=np.uint8)
            self.upper_color = np.array([100, 255, 255], dtype=np.uint8)
            self.min_area = 50
            self.max_area = 5000

    def detect(self, frame):
        """
        在给定的图像帧中检测目标，并返回最近目标的中心点相对于画面中心的偏移量。
        :param frame: 截图得到的 BGR 图像 (numpy array)
        :return: (dx, dy) 偏移量，或者如果没有找到目标则返回 (0, 0)
                 is_on_target (布尔值) 表示当前画面中心（准星）是否落在目标内部
                 frame (处理后的图像，用于绘制调试信息)
        """
        if frame is None or frame.size == 0:
            return (0, 0), False, frame

        height, width = frame.shape[:2]
        center_x, center_y = width // 2, height // 2

        # 1. 转换颜色空间：BGR 到 HSV (HSV 空间受光照影响更小，更适合颜色过滤)
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 2. 根据颜色阈值创建二值化掩膜 (Mask)
        # 目标颜色的像素会被设为 255(白色)，其他颜色变为 0(黑色)
        mask = cv2.inRange(hsv_frame, self.lower_color, self.upper_color)

        # 3. 寻找轮廓
        # cv2.RETR_EXTERNAL: 只提取最外面的轮廓
        # cv2.CHAIN_APPROX_SIMPLE: 压缩水平、垂直和对角线段，只保留它们的端点
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        target_center = None
        min_distance = float('inf')

        for contour in contours:
            area = cv2.contourArea(contour)
            # 4. 面积过滤：排除噪点和异常大的物体
            if self.min_area < area < self.max_area:
                # 5. 计算轮廓的矩 (Moments) 来获取中心点
                M = cv2.moments(contour)
                if M['m00'] != 0:
                    cx = int(M['m10'] / M['m00'])
                    cy = int(M['m01'] / M['m00'])

                    # 寻找距离屏幕中心最近的目标
                    distance = (cx - center_x) ** 2 + (cy - center_y) ** 2
                    if distance < min_distance:
                        min_distance = distance
                        target_center = (cx, cy)
                        best_contour = contour

        # 6. 计算相对偏移量并绘制调试信息
        dx, dy = 0, 0
        is_on_target = False
        
        if target_center is not None:
            cx, cy = target_center
            
            # 画出最佳轮廓的边界框 (绿色)
            x, y, w, h = cv2.boundingRect(best_contour)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # 画出目标中心点 (红色)
            cv2.circle(frame, (cx, cy), 3, (0, 0, 255), -1)
            
            # 画出从画面中心到目标的连线 (蓝色)
            cv2.line(frame, (center_x, center_y), (cx, cy), (255, 0, 0), 1)

            # 计算相对偏移
            dx = cx - center_x
            dy = cy - center_y
            
            # 7. 判断准星（画面中心）是否在目标轮廓内 (触发器逻辑)
            # 使用 measureDist=True，返回准星到轮廓边缘的最短距离 (正数表示在内部，负数表示在外部)
            # 为了防止在“外围方框的角落”开枪导致空枪，必须要求准星严格进入圆形轮廓内部！(dist >= 0.0)
            dist = cv2.pointPolygonTest(best_contour, (center_x, center_y), True)
            if dist >= 0.0:
                is_on_target = True

        # 画出画面中心点作为准星 (白色)
        cv2.circle(frame, (center_x, center_y), 2, (255, 255, 255), -1)
        
        # 准星如果在目标上，将准星画成绿色以示区分
        if is_on_target:
            cv2.circle(frame, (center_x, center_y), 3, (0, 255, 0), -1)

        return (dx, dy), is_on_target, frame
