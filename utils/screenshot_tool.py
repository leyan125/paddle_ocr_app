# utils/screenshot_tool.py
import os
import sys
import tkinter as tk
from PIL import Image
from mss import mss
import logging  # <-- 新增导入
import traceback  # <-- 新增导入，用于异常日志

# 获取当前模块的日志器实例
logger = logging.getLogger(__name__)


class ScreenshotTaker:
    """支持多显示器的截图选择器，带透明实时区域显示。"""

    def __init__(self, on_finish=None):
        """
        初始化截图工具
        参数:
            on_finish: 截图完成后的回调函数，形如 on_finish(image: PIL.Image or None)
        """
        self.on_finish = on_finish
        self.root = None  # Tkinter 根窗口
        self.canvas = None  # 用于绘制半透明遮罩和选区矩形的 Canvas
        self.rect_id = None  # Canvas 上选区矩形的 ID，用于更新/删除
        self.rect_start = None  # 鼠标按下的起始点 (屏幕坐标)
        self.rect_end = None  # 鼠标释放的结束点 (屏幕坐标)

    def take_screenshot(self):
        """启动截图窗口。"""
        logger.info("启动 ScreenshotTaker...")

        # ------------------ Windows DPI 设置 ------------------
        if sys.platform.startswith('win'):
            try:
                import ctypes
                # DPI_AWARENESS_PER_MONITOR_AWARE = 1
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
                logger.debug("Windows DPI 意识已设置为 Per Monitor Aware。")
            except Exception as e:
                # 替换 print
                logger.warning(f"DPI 设置失败: {e}")

        # 创建覆盖所有显示器的截图窗口
        self._create_window()
        # 启动 Tkinter 事件循环
        self.root.mainloop()

    def _create_window(self):
        """创建覆盖所有显示器的透明窗口，用于选取截图区域。"""
        self.root = tk.Tk()

        # ------------------ 窗口样式设置 ------------------
        self.root.overrideredirect(True)  # 去掉边框和标题栏
        self.root.attributes("-topmost", True)  # 窗口置顶
        self.root.attributes("-alpha", 0.2)  # 半透明遮罩
        self.root.configure(bg="#FFFFFF")  # 浅色背景

        # ------------------ 获取虚拟屏幕信息 ------------------
        left = top = 0
        width = self.root.winfo_screenwidth()  # 默认值
        height = self.root.winfo_screenheight()  # 默认值

        try:
            with mss() as sct:
                # mss.monitors[0] 通常是虚拟屏幕的总范围
                monitor_info = sct.monitors[0]
                left = monitor_info["left"]
                top = monitor_info["top"]
                width = monitor_info["width"]
                height = monitor_info["height"]
                logger.info(f"虚拟屏幕尺寸获取成功: {width}x{height}@{left},{top}")
        except Exception as e:
            # 替换 print
            logger.warning(f"无法使用 mss 获取虚拟屏幕尺寸: {e}。使用默认值。")

        # 设置窗口覆盖整个虚拟屏幕
        self.root.geometry(f"{width}x{height}+{left}+{top}")
        self.root.focus_force()
        self.root.bind("<Escape>", self.cancel_capture)
        logger.debug("截图窗口创建完成，等待用户选择区域...")

        # ------------------ Canvas 用于绘制选区 ------------------
        self.canvas = tk.Canvas(
            self.root,
            cursor="cross",
            bg="#FFFFFF",
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # ------------------ 绑定鼠标事件 ------------------
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def on_button_press(self, event):
        """鼠标按下时开始绘制选区矩形。"""
        self.rect_start = (self.root.winfo_pointerx(), self.root.winfo_pointery())
        self.rect_end = None
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        logger.debug(f"鼠标按下，起始点: {self.rect_start}")

    def on_mouse_drag(self, event):
        """鼠标拖动时实时更新矩形边框。"""
        if not self.rect_start:
            return

        self.rect_end = (self.root.winfo_pointerx(), self.root.winfo_pointery())
        x1, y1 = self.rect_start
        x2, y2 = self.rect_end
        x1, x2 = sorted([x1, x2])
        y1, y2 = sorted([y1, y2])

        if self.rect_id:
            self.canvas.delete(self.rect_id)

        # 转换为 Canvas 局部坐标
        cx1 = x1 - self.root.winfo_x()
        cy1 = y1 - self.root.winfo_y()
        cx2 = x2 - self.root.winfo_x()
        cy2 = y2 - self.root.winfo_y()

        # 绘制矩形
        self.rect_id = self.canvas.create_rectangle(
            cx1, cy1, cx2, cy2,
            outline="#FF0000",
            width=2,
            fill=""
        )

    def on_button_release(self, event):
        """鼠标释放时捕获截图。"""
        if not self.rect_start:
            self._finish(None)
            return

        self.rect_end = (self.root.winfo_pointerx(), self.root.winfo_pointery())

        # 销毁截图窗口
        if self.root:
            self.root.destroy()

        logger.info(f"鼠标释放，捕获区域: {self.rect_start} -> {self.rect_end}")

        # 计算选区坐标 (四舍五入到最近整数)
        x1, y1 = self.rect_start
        x2, y2 = self.rect_end
        x1, x2 = sorted([int(round(x1)), int(round(x2))])
        y1, y2 = sorted([int(round(y1)), int(round(y2))])

        width = x2 - x1
        height = y2 - y1

        # 如果选区太小，直接取消
        if width < 5 or height < 5:
            # 替换 print
            logger.warning("选区太小，截图取消。")
            self._finish(None)
            return

        # 捕获屏幕图像
        try:
            with mss() as sct:
                # 使用 mss.monitors[0] 获取虚拟屏范围
                vm = sct.monitors[0]
                vx, vy = vm['left'], vm['top']
                vwidth, vheight = vm['width'], vm['height']

                # 将选区 clamp 到虚拟屏范围内
                x1_clamped = max(vx, min(x1, vx + vwidth - 1))
                y1_clamped = max(vy, min(y1, vy + vheight - 1))
                x2_clamped = max(vx, min(x2, vx + vwidth))
                y2_clamped = max(vy, min(y2, vy + vheight))

                final_width = int(max(1, x2_clamped - x1_clamped))
                final_height = int(max(1, y2_clamped - y1_clamped))

                region = {
                    "left": int(x1_clamped),
                    "top": int(y1_clamped),
                    "width": final_width,
                    "height": final_height
                }

                logger.info(f"最终捕获区域（屏幕坐标）: {region}")

                sct_img = sct.grab(region)
                # mss 返回 BGRA 数据，转换为 PIL RGB
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                self._finish(img)
        except Exception as e:
            # 替换 print 和 file=sys.stderr
            logger.exception(f"截图失败: {e}")
            self._finish(None)

    def cancel_capture(self, event=None):
        """按下 ESC 键取消截图。"""
        logger.info("用户通过 ESC 取消截图。")
        if self.root:
            self.root.destroy()
        self._finish(None)

    def _finish(self, img):
        """截图完成后的回调。"""
        if self.on_finish:
            self.on_finish(img)


# =============================
# 测试示例
# =============================
if __name__ == "__main__":
    # 配置独立的日志系统，仅用于测试
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 确保 data_test 目录存在
    test_dir = "../data_test"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)


    def on_capture_done(img):
        if img:
            logger.info(f"截图完成，尺寸：{img.size}")
            # 保存图片
            output_path = os.path.join(test_dir, "screenshot_output.png")
            img.save(output_path)
            logger.info(f"图片已保存为 {output_path}")
        else:
            logger.info("未捕获到截图。")


    taker = ScreenshotTaker(on_capture_done)
    taker.take_screenshot()
