# 🚀 PaddleOCR 异步识别桌面工具

[![GitHub license](https://img.shields.io/github/license/leyan125/paddle_ocr_app?style=flat-square)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square)](https://www.python.org/)
[![Built with Tkinter](https://img.shields.io/badge/GUI-Tkinter-yellowgreen?style=flat-square)]()
[![Async Supported](https://img.shields.io/badge/Concurrency-Async/Thread-orange?style=flat-square)]()

基于 PaddlePaddle 的高性能 OCR (光学字符识别) 桌面应用。本工具使用 Python `tkinter` 构建 UI，并采用 `concurrent.futures` 线程池技术实现**异步识别**，确保在进行耗时操作时，用户界面保持流畅响应。

---

## ✨ 核心功能亮点

| 特性 | 描述 | 优势 |
| :--- | :--- | :--- |
| **异步处理** | 使用线程池隔离 OCR 任务，确保主 UI 线程永不阻塞。 | 解决传统 GUI 应用在处理深度学习任务时的卡顿问题。 |
| **历史记录** | 设有独立的标签页，记录所有识别结果，支持双击列表项加载完整文本。 | 极大地提升多任务处理和回顾的效率。 |
| **实时截图** | 集成自定义截图工具 (`utils/screenshot_tool.py`)，支持拖动选区后立即识别。 | 最高效的识别方式，无需中间文件存储。 |
| **多语言配置** | 通过 `config.yaml` 轻松配置和切换 PaddleOCR 支持的多种语言模型。 | 灵活适应不同语言环境下的识别需求。 |
| **GPU 加速支持** | 依赖于您的环境配置，可支持 PaddleOCR 的 GPU 加速运行。 | 适用于需要快速处理大量识别任务的用户。 |
| **专业 UI 反馈** | 实时状态栏（进度条、耗时、状态提示）、文件加载预览图及完善的错误日志。 | 提升应用的用户体验和专业性。 |

---

## 💻 安装指南

### 1. 克隆项目

```bash
git clone [https://github.com/leyan125/paddle_ocr_app.git](https://github.com/leyan125/paddle_ocr_app.git)
cd paddle_ocr_app
