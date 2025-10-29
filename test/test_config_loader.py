# test_config_loader.py
import os
import pytest
from paddle_ocr_app import config_loader


@pytest.fixture(autouse=True)
def reset_config():
    """
    pytest fixture：在每个测试函数运行前后自动执行。
    作用：
    - 测试前重置 _CONFIG_DATA（确保每次测试环境独立）
    - 测试后再清理（防止状态污染）
    """
    config_loader._reset_config_for_testing()
    yield
    config_loader._reset_config_for_testing()


# ---------------------------
# TEST 1: 配置加载与单例机制
# ---------------------------
def test_load_config_and_singleton(capsys):
    """测试配置文件加载是否正常，以及单例机制是否生效。"""
    # 第一次加载：应打印“正在加载配置文件”
    config_data_1 = config_loader.load_config()
    captured = capsys.readouterr()
    assert "正在加载配置文件" in captured.out
    assert isinstance(config_data_1, dict)
    assert len(config_data_1) > 0

    # 第二次加载：不应再次打印“正在加载配置文件”
    config_data_2 = config_loader.load_config()
    captured = capsys.readouterr()
    assert "正在加载配置文件" not in captured.out
    assert config_data_1 is config_data_2  # 验证单例


# ---------------------------
# TEST 2: 语言配置
# ---------------------------
def test_get_languages_config():
    """测试语言配置是否正确加载。"""
    languages = config_loader.get_languages_config()
    assert isinstance(languages, list)
    assert len(languages) > 0

    first_lang = languages[0]
    assert "code" in first_lang and "rec_model" in first_lang
    assert first_lang["code"] == "ch"  # 默认语言应为中文


# ---------------------------
# TEST 3: 通用配置
# ---------------------------
def test_get_general_config():
    """测试 general_config 内容。"""
    general_config = config_loader.get_general_config()
    assert isinstance(general_config, dict)
    assert general_config.get("det_model") == "PP-OCRv5_server_det"


# ---------------------------
# TEST 4: 执行器配置
# ---------------------------
def test_get_executor_config():
    """测试 executor_config 内容。"""
    executor_config = config_loader.get_executor_config()
    assert isinstance(executor_config, dict)
    assert executor_config.get("max_workers") == 2


# ---------------------------
# TEST 5: 按语言代码获取识别模型名称
# ---------------------------
@pytest.mark.parametrize(
    "lang_code, expected",
    [
        ("ch", "PP-OCRv5_server_rec"),
        ("japan", "PP-OCRv5_server_rec"),
        ("xx", None),
    ],
)
def test_get_rec_model_name(lang_code, expected):
    """测试不同语言代码的识别模型返回值。"""
    model_name = config_loader.get_rec_model_name(lang_code)
    assert model_name == expected


# ---------------------------
# TEST 6: 文件不存在异常
# ---------------------------
def test_file_not_found(tmp_path):
    """测试当 config.yaml 不存在时，是否正确抛出 FileNotFoundError。"""
    # 备份原始路径
    original_path = config_loader.CONFIG_PATH
    temp_path = original_path + ".bak"

    # 模拟配置文件丢失
    if os.path.exists(original_path):
        os.rename(original_path, temp_path)

    # 强制重置缓存
    config_loader._CONFIG_DATA = None

    try:
        with pytest.raises(FileNotFoundError):
            config_loader.load_config()
    finally:
        # 恢复文件
        if os.path.exists(temp_path):
            os.rename(temp_path, original_path)
        config_loader._CONFIG_DATA = None
        config_loader.load_config()  # 恢复环境


# ---------------------------
# 运行 pytest 命令
# ---------------------------
# 可在命令行执行以下命令运行所有测试：
# pytest -v test_config_loader.py
#
# 或在 CI/CD 环境中添加：
#   - name: Run unit tests
#     run: pytest -v --maxfail=1 --disable-warnings --tb=short
