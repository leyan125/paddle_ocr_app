# ocr_engine.py

import os
import inspect
from paddle import device, set_device
from paddleocr import PaddleOCR
from concurrent.futures import ThreadPoolExecutor
import io
from PIL import Image
import numpy as np
import logging  # <-- 导入 logging

# --- 导入配置加载器 ---
from config_loader import get_general_config, get_executor_config, get_rec_model_name

# 获取当前模块的日志器实例
logger = logging.getLogger(__name__)

# --- 替换硬编码常量 ---
# 模型基础目录现在必须手动定义在 ocr_engine.py 中，因为它依赖于项目结构，
# 且模型目录 ('models') 和 ocr_engine.py 是兄弟关系
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_MODEL_DIR = os.path.join(CURRENT_DIR, 'models')

# 获取通用配置 (det model name)
GENERAL_CONFIG = get_general_config()
DET_MODEL_NAME = GENERAL_CONFIG.get('det_model', 'PP-OCRv5_server_det')

# 获取执行器配置 (max_workers)
EXECUTOR_CONFIG = get_executor_config()
MAX_WORKERS = EXECUTOR_CONFIG.get('max_workers', 2)


# ----------------------


def init_paddle_ocr(lang='ch', det_path=None, rec_path=None, executor=None):
    """
    初始化 PaddleOCR 与线程池。
    - 根据 lang 参数自动确定模型路径。
    """
    try:
        # 替换 print
        logger.info("正在检测可用设备...")
        has_cuda = device.is_compiled_with_cuda()
        current_device = "gpu" if has_cuda else "cpu"
        # 替换 print
        logger.info(f"检测结果：{current_device.upper()} 模式。")
        set_device(current_device)

        # 替换 print
        logger.info(f"正在初始化 PaddleOCR (语言: {lang})...")

        # 线程执行器：如果外部未提供，则在这里创建
        if executor is None:
            # --- 使用配置中的最大线程数 ---
            executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
            # 替换 print
            logger.info(f"线程执行器已创建，最大线程数: {MAX_WORKERS}")
        else:
            # 替换 print
            logger.info(f"使用传入的线程执行器。")

        # --- 1. 确定最终模型路径 ---

        # a. 确定检测模型路径 (Det)：如果未传入 det_path，则自动查找
        if det_path is None:
            final_det_path = os.path.join(BASE_MODEL_DIR, DET_MODEL_NAME)
        else:
            final_det_path = det_path

        # b. 确定识别模型路径 (Rec)：如果未传入 rec_path，则根据 lang 查找
        if rec_path is None:
            # --- 通过配置加载器动态获取识别模型目录名 ---
            rec_model_dir_name = get_rec_model_name(lang)
            if rec_model_dir_name is None:
                raise ValueError(f"不支持的语言代码: {lang}。请检查 config.yaml。")

            final_rec_path = os.path.join(BASE_MODEL_DIR, rec_model_dir_name)
        else:
            final_rec_path = rec_path

        # --- 2. 构建 OCR 参数 ---

        ocr_kwargs = {
            'lang': lang,
            'use_doc_orientation_classify': False,
            'use_doc_unwarping': False,
            'use_textline_orientation': False
        }

        # 检查路径是否为有效目录，并设置 det_model_dir
        if os.path.isdir(final_det_path):
            ocr_kwargs['det_model_dir'] = final_det_path
            # 替换 print
            logger.info(f"Det 模型路径: {final_det_path}")
        else:
            # 替换 print 为 logger.warning
            logger.warning(f"检测模型目录不存在: {final_det_path}，PaddleOCR 将尝试使用默认行为。")

        # 检查路径是否为有效目录，并设置 rec_model_dir
        if os.path.isdir(final_rec_path):
            ocr_kwargs['rec_model_dir'] = final_rec_path
            # 替换 print
            logger.info(f"Rec 模型路径: {final_rec_path}")
        else:
            # 替换 print 为 logger.warning
            logger.warning(f"识别模型目录不存在: {final_rec_path}，PaddleOCR 将尝试使用默认行为。")

        # 检查 use_gpu 参数
        if "use_gpu" in inspect.signature(PaddleOCR).parameters:
            ocr_kwargs['use_gpu'] = has_cuda

        ocr_instance = PaddleOCR(**ocr_kwargs)
        # 替换 print
        logger.info(f"PaddleOCR 初始化完成 ({current_device.upper()}, 语言: {lang})。")

        return ocr_instance, executor

    except Exception as e:
        # 替换 print 和 traceback.print_exc() 为 logger.exception
        logger.exception(f"PaddleOCR 初始化失败: {e}")
        return None, executor


# recognize_and_get_text 函数保持不变
def recognize_and_get_text(ocr_instance, img_data, is_path=True):
    """
    执行 OCR 并返回纯文本
    :param ocr_instance: PaddleOCR 实例
    :param img_data: 图片路径 (str) 或 图片字节流 (bytes)
    :param is_path: True 表示 img_data 是路径，False 表示是字节流
    """
    if ocr_instance is None:
        return "错误：OCR 未初始化。"

    if is_path and not os.path.exists(img_data):
        return f"错误：图片文件未找到: {img_data}"

    try:
        # ... (图片输入处理、OCR 调用和后处理逻辑保持不变) ...
        # 兼容处理：如果不是路径，我们需要将字节流转换为 NumPy 数组
        if not is_path:
            image_stream = io.BytesIO(img_data)
            img_pil = Image.open(image_stream).convert('RGB')
            img_input = np.array(img_pil)
        else:
            img_input = img_data  # 路径 (str)

        # 关键调用：img_input 现在是路径 (str) 或 NumPy 数组 (np.ndarray)，符合 PaddleOCR 要求
        if hasattr(ocr_instance, 'predict'):
            result = ocr_instance.predict(img_input)
        else:
            result = ocr_instance.ocr(img_input)

        if not isinstance(result, list) or not result or not isinstance(result[0], dict):
            return "图片中未识别到有效文本或返回格式异常。"

        texts = result[0].get('rec_texts', [])

        if not texts:
            return "图片中未识别到有效文本。"

        # =======================================================
        # >>>>>>>>>>>>>> 改进后的文本后处理逻辑 <<<<<<<<<<<<<<<<

        # 1. 用空格连接所有文本行。这解决了“一句话从中间断开”的问题。
        combined_text = " ".join(texts)

        # 2. 清理多余空格：将连续的空白字符（包括空格和因 join 引入的额外空格）缩减为单个空格
        cleaned_text = " ".join(combined_text.split())

        # 3. 【核心改进】：根据标点符号或明显的段落分隔符，重新插入换行。
        separators = ('。', '？', '！', '”', '」', '：', '；')

        final_text = cleaned_text

        # 简单但有效的处理方法：在标点符号后插入换行和空格，然后清理多余空格
        for sep in separators:
            # 替换： [标点符号 + 空格] -> [标点符号 + 两个换行符]
            final_text = final_text.replace(sep + " ", sep + "\n\n")

        # 针对你的示例文本，特别处理标题分隔符（如：一、）
        final_text = final_text.replace(" 一、", "\n\n一、")
        final_text = final_text.replace(" 第一，", "\n\n第一，")

        # 4. 再次清理多余的换行符或空格，防止连续换行过多
        # 替换多个连续换行符为最多两个
        while "\n\n\n" in final_text:
            final_text = final_text.replace("\n\n\n", "\n\n")

        # 移除行首尾的空格和换行
        return final_text.strip()
        # =======================================================

    except Exception as e:
        # 替换 return f"处理出错: {e}\n{traceback.format_exc()}"
        # 使用 logger.exception 记录完整的 Traceback，界面只返回精简错误
        logger.exception(f"OCR 识别任务处理出错: {e}")
        return f"错误：OCR 识别任务执行失败，请查看日志文件了解详情。"


def get_rec_model_path_by_lang(lang_code):
    """
    根据语言代码，计算并返回该语言所需的识别模型目录的完整路径。
    """
    # 从配置加载器获取模型目录名
    rec_model_dir_name = get_rec_model_name(lang_code)

    if rec_model_dir_name is None:
        logger.warning(f"配置中未找到语言代码 '{lang_code}' 对应的识别模型。")
        return None

    # 利用 ocr_engine.py 中定义的 BASE_MODEL_DIR 构建完整路径
    final_rec_path = os.path.join(BASE_MODEL_DIR, rec_model_dir_name)
    return final_rec_path
