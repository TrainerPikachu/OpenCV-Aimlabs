import win32api
import win32con
import time
import yaml
from src.utils.logger import logger

class MouseController:
    def __init__(self, config_path="config.yaml"):
        """
        初始化鼠标控制模块。
        读取配置文件中的平滑度、灵敏度和点击延迟参数。
        """
        self._load_config(config_path)

    def _load_config(self, config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                control_cfg = config.get('control', {})
                
                # 平滑度：防止鼠标瞬间跳跃，更像人类操作 (0.0=瞬间移动, 1.0=完全不移动)
                # 实际上由于 win32api.mouse_event 只接受整数，所以平滑处理会打些折扣
                self.smoothing = control_cfg.get('mouse_smoothing', 0.5)
                
                # 灵敏度系数：由于游戏内的FOV和灵敏度设置，屏幕像素偏移并不等于鼠标物理偏移
                self.x_multiplier = control_cfg.get('x_multiplier', 0.8)
                self.y_multiplier = control_cfg.get('y_multiplier', 0.8)
                
                self.click_delay = control_cfg.get('click_delay', 0.01)
                
                logger.info("鼠标控制模块配置加载成功")
        except Exception as e:
            logger.error(f"加载鼠标控制配置失败，使用默认值: {e}")
            self.smoothing = 0.5
            self.x_multiplier = 0.8
            self.y_multiplier = 0.8
            self.click_delay = 0.01

    def move(self, dx, dy):
        """
        普通的相对鼠标移动事件
        """
        if dx == 0 and dy == 0:
            return

        # 应用灵敏度和阻尼(平滑度)系数
        # x_multiplier 用于抵消游戏内灵敏度带来的像素/角度误差
        # smoothing 用于模拟人为拉枪的减速过程 (0.0 = 瞬间满速, 0.9 = 龟速)
        move_x = int(dx * self.x_multiplier * (1.0 - self.smoothing))
        move_y = int(dy * self.y_multiplier * (1.0 - self.smoothing))

        # 核心修复：消除浮点数截断产生的“死区 (Deadzone)”
        # 如果你的游戏灵敏度很高（multiplier很小），当准星靠近目标时，比如 dx=10，10 * 0.05 = 0.5，int(0.5) 就会变成 0！
        # 这会导致鼠标在距离目标很远的地方“彻底停住”，死活不肯走最后几步。
        # 解决方案：只要视觉上算出来还有偏差 (dx!=0)，物理鼠标就必须至少挪动 1 个单位去追赶！
        if dx > 0 and move_x == 0:
            move_x = 1
        elif dx < 0 and move_x == 0:
            move_x = -1
            
        if dy > 0 and move_y == 0:
            move_y = 1
        elif dy < 0 and move_y == 0:
            move_y = -1

        if move_x != 0 or move_y != 0:
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, move_x, move_y, 0, 0)

    def click(self):
        """
        极速点击，带有微弱延迟以防游戏引擎漏判
        """
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(self.click_delay)  # 恢复 0.01 秒的延迟，防止漏点
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
