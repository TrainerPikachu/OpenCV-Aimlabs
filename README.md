# OpenCV Aimlabs Bot

这是一个基于 Python 和 OpenCV 的 Aim Lab 自动化视觉辅助脚本，主要用于展示计算机视觉基础、高性能屏幕捕获以及 Windows API 的底层交互。

示例视频：https://www.bilibili.com/video/

> ⚠️ **免责声明**: 本项目仅供编程学习与技术展示，请勿在包含反作弊机制（如 Vanguard, EAC, BattlEye 等）的多人游戏中使用。

## 核心技术实现

1. **DXGI 屏幕捕获**: 使用 `dxcam` (Desktop Duplication API) 直接从显存读取画面，实现低延迟的高帧率捕获，避免了传统 `win32gui` 的 CPU 瓶颈。
2. **时钟精度优化**: 调用 `ctypes.windll.winmm.timeBeginPeriod(1)` 绕过 Windows 默认的 15.6ms 线程调度限制，将主循环调度精度提升至 1ms 级别。
3. **动态 ROI 扫描**: 采用双阶段扫描策略。优先处理准星中心 400x400 的核心区域以保证帧率；若核心区无目标，则自动扩展至 1200x1200 区域进行扫描。
4. **反死区鼠标控制**: 自定义 `MouseController`，加入最小像素移动下限（反死区逻辑），避免 `win32api` 处理浮点数坐标截断时产生的微调卡死现象。
5. **多边形内点测试**: 射击触发器基于 `cv2.pointPolygonTest` 算法，确保准星严格位于目标轮廓内部（而非 Bounding Box）时才执行点击。

## 快速上手

### 环境要求
- OS: Windows 10 / 11
- Python: 3.8 - 3.11
- 游戏设置: Aim Lab 需设置为 **无边框窗口化** 或 **窗口化**

### 安装与运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行脚本
python main.py
```

### 全局热键
- `T` 键: 开启 / 暂停自动瞄准
- `Q` 键: 退出程序

## 测试

运行单元测试：
```bash
pytest tests/
```
