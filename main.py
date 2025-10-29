# main.py
# ----------------------------------------------------------------------
# 程序主入口：初始化 OCR 核心模型，配置并启动 Tkinter 图形用户界面 (GUI)。
# ----------------------------------------------------------------------

import tkinter as tk
import logging  # 导入 logging 库
import os  # 用于处理文件路径
from logging.handlers import RotatingFileHandler  # 导入用于文件滚动记录的 Handler
# 导入后端逻辑：模型初始化和文字识别函数
from ocr_engine import init_paddle_ocr, recognize_and_get_text
# 导入前端界面：GUI 应用类
from gui_app import OcrApp
# 导入配置加载器
from config_loader import get_logging_config
from PIL import Image, ImageTk

# --- 日志配置函数 ---
def setup_logging():
    """配置统一的日志系统。（此函数内容保持不变）"""
    try:
        log_config = get_logging_config()
        log_level_str = log_config.get('level', 'INFO').upper()
        log_file_path = log_config.get('file_path', 'app.log')

        # 转换日志级别字符串为 logging 模块的常量
        log_level = getattr(logging, log_level_str, logging.INFO)

        # 确定日志文件路径（如果需要，创建目录）
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 1. 根日志器配置
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # 2. 定义格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 3. 添加控制台 Handler
        if not any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        # 4. 添加文件 Handler (使用 RotatingFileHandler 实现日志文件自动滚动)
        if not any(isinstance(handler, logging.FileHandler) for handler in root_logger.handlers):
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=1024 * 1024 * 5,  # 最大 5MB
                backupCount=5,  # 保留 5 个备份文件
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        logging.info(f"日志系统初始化完成。级别: {log_level_str}, 文件: {log_file_path}")

    except Exception as e:
        # 如果日志系统配置失败，至少保证能打印出错误
        # 此处的 print 是必要的，因为日志系统可能未成功建立
        print(f"[FATAL ERROR] 无法初始化日志系统: {e}")


# ----------------------------------------------------
# >>> 图标文件路径定义 <<<
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH_ICO = os.path.join(BASE_DIR, 'assets', 'app_icon.ico')
ICON_PATH_PNG = os.path.join(BASE_DIR, 'assets', 'app_icon.png')
# ----------------------------------------------------


if __name__ == "__main__":

    # ------------------------------------------------------------------
    # 1. 初始化日志系统 (新增/修正)
    # ------------------------------------------------------------------
    setup_logging()
    logger = logging.getLogger(__name__)  # 获取当前模块的logger实例

    # ------------------------------------------------------------------
    # 2. 初始化 PaddleOCR 模型及线程池 (原 1.)
    # ------------------------------------------------------------------
    logger.info("正在初始化 OCR 引擎...")  # 替换原有提示
    ocr_instance, executor_instance = init_paddle_ocr(lang='ch')

    # 检查模型是否加载成功
    if ocr_instance is None:
        # 替换 print
        logger.error("OCR 模型初始化失败。请检查 config.yaml 配置和 models/ 目录下的模型文件是否存在。")
        # 即使模型加载失败，程序也允许继续，但 GUI 必须处理功能受限的情况。
        pass

    # ------------------------------------------------------------------
    # 3. 启动 Tkinter GUI 应用 (原 2.)
    # ------------------------------------------------------------------
    # 创建 Tkinter 应用程序的根窗口
    root = tk.Tk()

    # =========================================================
    # >>> 关键修改：设置窗口图标逻辑 <<<
    try:
        icon_set = False

        # 1. 尝试使用 iconbitmap (.ico) - Windows 首选
        if os.path.exists(ICON_PATH_ICO):
            root.iconbitmap(ICON_PATH_ICO)
            logger.info(f"窗口图标设置为: {ICON_PATH_ICO}")
            icon_set = True

        # 2. 尝试使用 iconphoto (.png) - 跨平台兼容
        if not icon_set and os.path.exists(ICON_PATH_PNG) and Image and ImageTk:
            try:
                # 加载 PNG 图片并转换为 PhotoImage 对象
                icon_img = Image.open(ICON_PATH_PNG)
                # 必须将 PhotoImage 对象保存在 root 实例上，防止被垃圾回收
                root.icon_photo = ImageTk.PhotoImage(icon_img)
                root.iconphoto(True, root.icon_photo)
                logger.info(f"窗口图标设置为: {ICON_PATH_PNG}")
                icon_set = True
            except Exception as e:
                logger.warning(f"使用 iconphoto 加载 PNG 图标失败: {e}")

        if not icon_set:
            logger.warning("未找到可用的图标文件 (.ico 或 .png) 或 PIL 库缺失，使用默认系统图标。")

    except tk.TclError as e:
        logger.warning(f"设置窗口图标时发生 TclError (可能是格式不支持): {e}")
    # =========================================================

    logger.info("配置并启动 GUI 界面。")  # 新增信息

    # 配置窗口几何属性
    root.geometry("750x650")  # 设置初始窗口尺寸为 750x650 像素
    root.resizable(False, False)  # 禁用窗口大小调整功能

    # 实例化 GUI 主界面类，传入所有核心依赖
    app = OcrApp(
        master=root,
        ocr_instance=ocr_instance,
        executor_instance=executor_instance,
        recognize_func=recognize_and_get_text
    )

    # ------------------------------------------------------------------
    # 4. 主事件循环与资源安全管理 (原 3.)
    # ------------------------------------------------------------------
    try:
        # 设置窗口关闭（X 按钮）时的协议处理
        if executor_instance:
            # 使用 root.protocol 确保在 GUI 关闭时，安全地关闭并发执行器/线程池。
            # wait=False 避免在等待线程结束时造成程序阻塞。
            def on_closing():
                executor_instance.shutdown(wait=False)
                # 替换原有逻辑：在关闭时记录日志
                logger.info("GUI 窗口关闭，并发执行器已安全关闭。")
                root.destroy()


            root.protocol("WM_DELETE_WINDOW", on_closing)

        logger.info("启动 Tkinter 主事件循环。")  # 新增信息
        # 启动 Tkinter 主事件循环，等待用户交互
        root.mainloop()

    finally:
        # 确保在程序发生异常退出时，线程池也能被安全关闭
        if executor_instance:
            # 替换 print
            logger.info("程序退出，安全关闭并发执行器...")
            executor_instance.shutdown(wait=False)