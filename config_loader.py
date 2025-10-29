# config_loader.py
import yaml
import os

# ======================
# 1. 路径配置部分
# ======================

# 获取当前脚本 (config_loader.py) 所在的目录
# 例如：paddle_ocr_app/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 定义配置文件名称和目录名
CONFIG_FILE_NAME = 'config.yaml'
CONFIG_FOLDER_NAME = 'config'

# 构建完整的配置文件路径：CURRENT_DIR/config/config.yaml
# 例如：/path/to/paddle_ocr_app/config/config.yaml
CONFIG_PATH = os.path.join(CURRENT_DIR, CONFIG_FOLDER_NAME, CONFIG_FILE_NAME)

# 定义全局变量，用于缓存已加载的配置数据
# 目的：避免重复加载配置文件（实现单例效果）
_CONFIG_DATA = None


# ======================
# 2. 配置加载函数
# ======================
def load_config():
    """
    加载 YAML 配置文件。
    - 首次调用时从磁盘读取并解析 YAML；
    - 后续调用直接返回缓存结果；
    - 若文件不存在或格式错误，会抛出异常。
    """
    global _CONFIG_DATA  # 使用全局变量

    # 如果配置已经加载过，则直接返回，避免重复 IO 操作
    if _CONFIG_DATA is not None:
        return _CONFIG_DATA

    # 输出提示信息
    print(f"正在加载配置文件: {CONFIG_PATH}")

    # 检查配置文件是否存在
    if not os.path.exists(CONFIG_PATH):
        # 如果不存在，抛出 FileNotFoundError，并打印完整路径，便于排查问题
        raise FileNotFoundError(f"配置加载失败: 未找到文件 {CONFIG_PATH}")

    try:
        # 打开配置文件并安全解析 YAML
        # yaml.safe_load 能防止执行潜在的恶意代码（比 load 更安全）
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            _CONFIG_DATA = yaml.safe_load(f)
            print("配置文件加载成功。")
            return _CONFIG_DATA

    # 如果 YAML 格式错误，则捕获并提示
    except yaml.YAMLError as e:
        print(f"YAML 解析错误: {e}")
        raise

    # 捕获其他未知异常
    except Exception as e:
        print(f"加载配置文件时发生未知错误: {e}")
        raise


# ======================
# 3. 配置访问接口
# ======================
# 以下函数封装了常用配置项的访问逻辑，
# 每次调用时都会自动触发 load_config()（如果尚未加载）。

def get_languages_config():
    """
    获取语言相关配置列表。
    返回示例:
    [
        {"code": "ch", "rec_model": "ch_PP-OCRv4_rec"},
        {"code": "en", "rec_model": "en_PP-OCRv4_rec"}
    ]
    """
    config = load_config()
    return config.get('supported_languages', [])


def get_general_config():
    """
    获取通用配置。
    例如：日志路径、线程数、输出选项等。
    """
    config = load_config()
    return config.get('general_config', {})


def get_logging_config():
    """
    获取日志相关配置。
    """
    config = load_config()
    # 默认值设置：如果配置中没有 logging_config，返回一个合理的默认配置
    return config.get('logging_config', {
        'level': 'INFO',
        'file_path': 'app.log'
    })


def get_executor_config():
    """
    获取执行器（Executor）相关配置。
    例如：是否启用 GPU、多线程参数、OCR 模型路径等。
    """
    config = load_config()
    return config.get('executor_config', {})


def get_rec_model_name(lang_code):
    """
    根据语言代码（如 'ch', 'en'）获取对应的识别模型名称。
    若找不到匹配语言，则返回 None。
    """
    lang_list = get_languages_config()
    for lang in lang_list:
        if lang.get('code') == lang_code:
            return lang.get('rec_model')
    return None


# ======================
# 4. 测试辅助函数
# ======================
def _reset_config_for_testing():
    """
    仅供单元测试使用：
    手动重置全局配置缓存，使得下次调用 load_config() 时重新读取文件。
    """
    global _CONFIG_DATA
    _CONFIG_DATA = None
