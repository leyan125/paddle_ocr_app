🚀 PaddleOCR 异步识别桌面工具 (Tkinter/Python)这是一个基于 PaddlePaddle 深度学习框架的 OCR (光学字符识别) 桌面应用。它使用 Python 的 tkinter 库构建用户界面，并利用 concurrent.futures 实现异步识别，确保在进行耗时的 OCR 任务时，用户界面不会冻结。✨ 主要功能亮点特性描述优势异步/并发处理使用 ThreadPoolExecutor 隔离 OCR 识别任务，UI 保持流畅响应。解决传统 GUI 应用在执行耗时任务时卡顿的问题。历史记录管理通过 ttk.Notebook 和 ttk.Treeview 记录所有成功的识别结果，并支持双击加载。极大地提升用户体验和工作效率。实时屏幕截图集成自定义截图工具，支持拖动选区后立即进行 OCR 识别。最快的识别方式，无需保存文件。多语言支持通过配置文件轻松切换不同的 OCR 识别语言（如中文、英文等）。适应全球化的识别需求。专业化 UI完善的日志系统、状态栏反馈（耗时/进度）、文件加载预览图、窗口图标设置。提升应用在功能和外观上的专业度。健壮性与错误处理增加 try-except 块和日志记录，捕获文件加载、模型初始化和异步任务执行中的异常。应用稳定可靠，易于排查问题。💻 环境要求操作系统: Windows / Linux / macOSPython 版本: 3.8+ (推荐)📥 安装与配置1. 克隆项目Bashgit clone <你的仓库URL>
cd paddle_ocr_app
2. 创建并激活虚拟环境Bashpython -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
3. 安装依赖本项目依赖 PaddleOCR 及其必要的运行库、Tkinter 扩展（Pillow）和截图工具。Bashpip install -r requirements.txt
4. 模型配置与下载本项目使用 PaddleOCR 的轻量级模型。你需要将模型文件放入项目根目录下的 models/ 文件夹中。创建目录:Bashmkdir models
下载模型: 访问 PaddleOCR 官方 GitHub 下载您需要的模型文件，并根据 config.yaml 的要求命名。示例 (中文超轻量模型):将 推理模型 文件放入 models/ch_ppocr_v4_rec/ 和 models/ch_ppocr_mobile_v2_det/ 目录。注意: 配置文件 config.yaml 中已指定了模型路径和语言配置。5. 图标设置 (可选)为了使窗口显示图标，请在 assets/ 文件夹中放置您的图标文件：assets/app_icon.icoassets/app_icon.png▶️ 如何运行在激活虚拟环境并完成所有配置后，运行主程序：Bashpython main.py
使用说明选择语言: 在右上角下拉菜单中选择所需的识别语言。选择文件: 点击 "选择图片文件" 加载图片并开始异步识别。截图识别: 点击 "屏幕截图"，程序窗口将隐藏，您可以在屏幕上拖动鼠标选择区域。释放鼠标后自动开始识别。查看历史: 识别完成后，切换到 "历史记录" 标签页，双击列表项可将完整文本重新加载到主识别区。⚙️ 项目结构paddle_ocr_app/
├── main.py                 # 程序启动、日志配置、模型/线程池初始化
├── gui_app.py              # 核心 GUI 逻辑 (OcrApp 类)
├── ocr_engine.py           # PaddleOCR 初始化和识别函数的封装
├── config_loader.py        # 负责加载 config.yaml 配置
├── requirements.txt        # Python 依赖列表
├── config.yaml             # 核心配置，用于定义语言、模型路径
├── assets/                 # 窗口图标等资源
├── utils/
│   └── screenshot_tool.py  # 跨平台截图实现
└── README.md
🤝 贡献与致谢欢迎所有形式的贡献！如果您有任何建议或发现 Bug，请随时提交 Issue 或 Pull Request。特别感谢：PaddlePaddle/PaddleOCR 提供了强大的识别核心。Python/Tkinter 提供了原生 GUI 解决方案。PIL/Pillow 提供了图像处理能力。Enjoy the efficient OCR experience!