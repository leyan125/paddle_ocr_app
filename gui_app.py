# gui_app.py
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import io
import sys
import concurrent.futures
import logging
import time
from PIL import Image, ImageTk

# *****************************************************************

logger = logging.getLogger(__name__)

# --- 定义缩略图最大尺寸 ---
PREVIEW_MAX_SIZE = (100, 100)
PREVIEW_DEFAULT_TEXT = "截图/文件预览区域"
PREVIEW_DEFAULT_WIDTH = 20
PREVIEW_DEFAULT_HEIGHT = 8

# --- 导入配置加载器 ---
try:
    from config_loader import get_languages_config
except ImportError:
    logger.warning("警告: 无法导入 config_loader.py，GUI 将使用硬编码语言列表。")


    # ... (get_languages_config 定义保持不变) ...
    def get_languages_config():
        return [
            {"name": "中文 (简体)", "code": "ch"},
            {"name": "英文", "code": "en"},
        ]

# >>> 关键修改 1: 导入自定义工具类 <<<
try:
    from utils.screenshot_tool import ScreenshotTaker
except ImportError:
    logger.warning("警告: 无法导入 utils.screenshot_tool.ScreenshotTaker。截图功能将不可用。")
    ScreenshotTaker = None


# >>> 关键修改 1 结束 <<<


class OcrApp:
    def __init__(self, master, ocr_instance, executor_instance, recognize_func):
        self.master = master
        self.ocr = ocr_instance
        self.executor = executor_instance
        self.recognize_func = recognize_func

        # --- 新增属性用于管理预览图 ---
        self.preview_image = None  # 持有 PhotoImage 引用，防止被垃圾回收
        self.preview_label = None  # 预览图标签

        # --- 新增属性用于历史记录 ---
        self.history_data = []  # 存储历史记录列表：[{"time": "...", "text": "...", "source": "..."}]
        self.notebook = None  # ttk.Notebook 实例
        self.history_tree = None  # ttk.Treeview 实例

        # --- 替换硬编码语言列表 ---
        languages_config = get_languages_config()
        self.LANGUAGES = {item['name']: item['code'] for item in languages_config}

        if self.LANGUAGES:
            default_lang_name = list(self.LANGUAGES.keys())[0]
        else:
            default_lang_name = "中文 (简体)"

        self.lang_var = tk.StringVar(value=default_lang_name)
        self.current_lang_code = self.LANGUAGES.get(default_lang_name, 'ch')

        try:
            from ocr_engine import get_rec_model_path_by_lang
            self.current_rec_model_path = get_rec_model_path_by_lang(self.current_lang_code)
        except ImportError:
            self.current_rec_model_path = None

        # >>> 关键修改 2: 仅存储类引用，不在此实例化 <<<
        self.screenshot_taker_class = ScreenshotTaker
        # >>> 关键修改 2 结束 <<<

        master.title("PaddleOCR 简易识别工具")
        self.setup_ui(master)

        device_status = "可用" if self.ocr else "初始化失败"
        current_lang = self.lang_var.get()
        self.status_var.set(f"等待操作... | 状态：{device_status} | 语言：{current_lang}")

    def setup_ui(self, master):
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Helvetica', 10))
        self.style.configure('TLabel', font=('Helvetica', 10))

        # =========================================================
        # >>>>>>>>>>>>>>>>> 调整主窗口的行和列伸展权重 <<<<<<<<<<<<<<<<<
        # 0 行用于 Notebook，占据主要空间
        # 1 行用于 Status Bar，不伸缩
        master.grid_columnconfigure(0, weight=1)  # 只有一列
        master.grid_rowconfigure(0, weight=5)  # Notebook 占据主要伸缩空间
        master.grid_rowconfigure(1, weight=0)  # 状态栏不伸缩
        # =========================================================

        # ----------------------------------------------------
        # >>> 关键修改 A: 创建 Notebook (多标签页容器) <<<
        self.notebook = ttk.Notebook(master)
        # Notebook 放置在 row=0，占据主窗口主要部分
        self.notebook.grid(row=0, column=0, sticky='nsew', padx=10, pady=(10, 0))

        # 创建主识别界面 Frame
        self.main_tab_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(self.main_tab_frame, text=" 识别 (OCR) ")

        # 定义主识别标签页内的布局上下文
        main_frame = self.main_tab_frame
        main_frame.grid_columnconfigure(0, weight=1)  # 只有一列
        main_frame.grid_rowconfigure(0, weight=0)  # 顶部控制区不伸缩
        main_frame.grid_rowconfigure(1, weight=5)  # 结果文本框行占据主空间
        # ----------------------------------------------------

        # --- 1. Top Frame：容纳所有控制元素和预览图 (现在位于 main_frame 的 row 0) ---
        top_frame = ttk.Frame(main_frame, padding="5")
        top_frame.grid(row=0, column=0, sticky='new')

        # 调整 Top Frame 内部的列权重
        top_frame.grid_columnconfigure(0, weight=1)  # 左侧控制区可伸缩
        top_frame.grid_columnconfigure(1, weight=0)  # 右侧预览区固定大小

        # ----------------------------------------------------
        # --- 左侧控制区框架 (File/Language/Buttons) ---
        control_frame = ttk.Frame(top_frame)
        control_frame.grid(row=0, column=0, padx=5, pady=5, sticky='nwe')
        control_frame.grid_columnconfigure(1, weight=1)

        row_idx = 0

        # 1. 语言选择（放在顶部）
        language_frame = ttk.Frame(control_frame)
        language_frame.grid(row=row_idx, column=2, padx=(10, 0), sticky='e')

        ttk.Label(language_frame, text="识别语言:").pack(side=tk.LEFT, padx=(0, 5))
        self.lang_combo = ttk.Combobox(
            language_frame,
            textvariable=self.lang_var,
            values=list(self.LANGUAGES.keys()),
            state="readonly",
            width=15
        )
        self.lang_combo.bind("<<ComboboxSelected>>", self.reinitialize_ocr)
        self.lang_combo.pack(side=tk.LEFT)

        # 标题
        ttk.Label(control_frame, text="请选择一张图片进行 OCR 识别:").grid(row=row_idx, column=0,
                                                                           columnspan=2, pady=5, sticky='w')
        row_idx += 1

        # 2. 文件路径显示
        self.file_path_var = tk.StringVar(value="未选择文件")
        ttk.Label(control_frame, textvariable=self.file_path_var, wraplength=350,
                  foreground='blue').grid(row=row_idx, column=0, columnspan=2, pady=5, sticky='w')

        # 3. 选择文件按钮
        self.select_button = ttk.Button(control_frame, text="选择图片文件", command=self.select_file,
                                        state=(tk.NORMAL if self.ocr else tk.DISABLED))
        self.select_button.grid(row=row_idx, column=2, padx=(10, 0), sticky='w')
        row_idx += 1

        # 4. 截图按钮
        self.screenshot_button = ttk.Button(
            control_frame,
            text="屏幕截图 (ESC取消)",
            command=self.screenshot_and_recognize,
            state=(tk.NORMAL if self.ocr and self.screenshot_taker_class else tk.DISABLED)
        )
        self.screenshot_button.grid(row=row_idx, column=2, padx=(10, 0), pady=(5, 10), sticky='w')

        # 5. 识别结果标题
        ttk.Label(control_frame, text="识别结果:", font=('Helvetica', 10, 'bold')).grid(row=row_idx, column=0,
                                                                                        pady=(5, 10), sticky='w')
        row_idx += 1
        # ----------------------------------------------------

        # ----------------------------------------------------
        # --- 右侧预览图区 ---

        preview_container = ttk.Frame(top_frame, padding="5", relief=tk.RIDGE)
        preview_container.grid(row=0, column=1, padx=5, pady=5, sticky='ne')

        ttk.Label(preview_container, text="图片预览").pack(pady=(0, 5))

        # 预览图标签
        self.preview_label = tk.Label(
            preview_container,
            text=PREVIEW_DEFAULT_TEXT,
            bg='light gray',
            relief=tk.SUNKEN,
            anchor=tk.CENTER,
            width=PREVIEW_DEFAULT_WIDTH,
            height=PREVIEW_DEFAULT_HEIGHT
        )
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        # ----------------------------------------------------

        # --- 2. 结果展示区域 (现在位于 main_frame 的 row 1) ---

        self.result_text = scrolledtext.ScrolledText(main_frame, width=70, height=18, wrap=tk.WORD,
                                                     font=('Microsoft YaHei', 10))
        # 结果文本框在 main_frame 的第 1 行
        self.result_text.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')

        # ----------------------------------------------------
        # >>> 关键修改 B: 创建历史记录标签页 <<<
        self._setup_history_tab()
        # ----------------------------------------------------

        # --- 3. 状态栏区域 (放置在 master 窗口底部，Notebook 之外) ---

        # 状态栏容器 (现在位于 master 的 row 1)
        self.status_frame = ttk.Frame(master, relief=tk.SUNKEN)
        self.status_frame.grid(row=1, column=0, sticky='we')  # row 从 2 变为 1

        self.status_frame.grid_columnconfigure(0, weight=1)
        # 进度条长度固定
        self.status_frame.grid_columnconfigure(1, weight=0, minsize=200)

        # 状态文本
        self.status_var = tk.StringVar(value="等待操作...")
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var, anchor=tk.W)
        self.status_label.grid(row=0, column=0, sticky='nw', padx=5, pady=5)

        # 进度条
        self.progressbar = ttk.Progressbar(self.status_frame, mode='indeterminate', length=200)
        self.progressbar.grid(row=0, column=1, sticky='nse', padx=5, pady=5)
        self.progressbar.grid_remove()  # 初始隐藏

    # ----------------------------------------------------------------------
    # >>> 新增方法：历史记录 UI 设置 <<<
    # ----------------------------------------------------------------------
    def _setup_history_tab(self):
        """创建历史记录标签页，包含 Treeview 列表。"""

        history_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(history_tab_frame, text=" 历史记录 ")

        # 允许历史记录标签页的内容伸展
        history_tab_frame.grid_columnconfigure(0, weight=1)
        history_tab_frame.grid_rowconfigure(0, weight=1)

        # --- Treeview (列表) ---

        # 1. 定义列
        columns = ("#", "time", "source", "text")
        self.history_tree = ttk.Treeview(
            history_tab_frame,
            columns=columns,
            show='headings'  # 只显示列标题
        )

        # 2. 定义标题和宽度
        self.history_tree.heading("#", text="ID")
        self.history_tree.heading("time", text="识别时间")
        self.history_tree.heading("source", text="来源")
        self.history_tree.heading("text", text="识别结果 (双击查看)")

        self.history_tree.column("#", width=50, anchor=tk.CENTER, stretch=tk.NO)
        self.history_tree.column("time", width=150, anchor=tk.W, stretch=tk.NO)
        self.history_tree.column("source", width=100, anchor=tk.CENTER, stretch=tk.NO)
        self.history_tree.column("text", width=350, anchor=tk.W, stretch=tk.YES)  # 结果列伸展

        # 3. 添加滚动条
        vsb = ttk.Scrollbar(history_tab_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=vsb.set)

        # 4. 布局
        self.history_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        # 5. 绑定双击事件：查看完整文本
        self.history_tree.bind("<Double-1>", self._show_history_detail)

    def _show_history_detail(self, event):
        """
        处理历史记录列表的双击事件，将完整文本显示在主识别区域。
        """
        selected_item = self.history_tree.selection()
        if not selected_item:
            return

        item_id = selected_item[0]
        # 从 Treeview 获取存储的索引（即 ID 列的值）
        try:
            record_index = int(self.history_tree.set(item_id, '#'))
        except (ValueError, IndexError):
            self.status_var.set("错误：无法获取历史记录索引。")
            return

        try:
            record = self.history_data[record_index]
        except (IndexError, TypeError):
            logger.error(f"历史记录数据索引 {record_index} 查找失败。")
            self.status_var.set("错误：历史记录数据查找失败。")
            return

        # 切换到主识别标签页 (索引 0)
        self.notebook.select(0)

        # 清空并显示历史文本
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END,
                                f"--- 历史记录 ID: {record_index}, 来源: {record['source']}, 时间: {record['time']} ---\n\n")
        self.result_text.insert(tk.END, record['text'])

        self.status_var.set(f"状态：已加载 ID {record_index} 的历史记录。")

    def select_file(self):
        """
        文件选择与异步任务提交
        """
        if self.executor is None or self.ocr is None:
            self.status_var.set("错误：OCR 或执行器不可用。")
            return

        file_path = filedialog.askopenfilename(title="选择图片文件",
                                               filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp"),
                                                          ("所有文件", "*.*")])
        if not file_path:
            return

        # 1. 加载 PIL Image 对象
        try:
            # --- 增加 try-except 块以捕获文件加载错误并记录 ---
            img_pil = Image.open(file_path).convert('RGB')
        except Exception as e:
            # 记录详细的异常信息，并给用户简洁的提示
            self.status_var.set(f"错误：加载文件失败。")
            logger.exception(f"加载文件 {file_path} 失败: {e}")

            # 清除之前的错误信息和预览图
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"文件加载失败，请检查文件格式是否支持或文件是否损坏。详细信息已写入日志。")
            self.preview_label.config(image=None, text=PREVIEW_DEFAULT_TEXT, bg='light gray')
            return

        self.file_path_var.set(f"文件路径: {file_path}")

        # 2. 启动识别任务
        self._start_recognition_from_image(img_pil, is_file=True)

    def update_ui_with_result(self, future, start_time):
        """
        异步任务完成后的 UI 更新。
        """
        # 停止进度显示
        self.progressbar.stop()
        self.progressbar.grid_forget()

        end_time = time.time()
        elapsed_time = end_time - start_time
        time_str = f"{elapsed_time:.2f} 秒"

        try:
            recognized_text = future.result()
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, recognized_text)

            if recognized_text.startswith(("错误", "任务出错", "初始化失败")):
                self.status_var.set(f"状态：识别失败 (耗时: {time_str})")
                logger.error("OCR 任务返回错误结果。")
            else:
                # 状态栏显示耗时
                self.status_var.set(f"状态：识别完成 (耗时: {time_str})，结果已复制到剪贴板。")
                self.master.clipboard_clear()
                self.master.clipboard_append(recognized_text)
                self.master.update()

                # =========================================================
                # >>> 关键修改：添加记录到历史列表 <<<

                # 确定来源
                source_path = self.file_path_var.get()
                source_type = "截图" if "屏幕截图" in source_path else "文件"
                if "未选择文件" in source_path:
                    # 确保截图操作在没有文件路径时仍被正确标识
                    source_type = "截图"

                    # 创建新的历史记录项
                new_record = {
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "text": recognized_text,
                    "source": source_type
                }

                # 1. 添加到数据列表
                self.history_data.append(new_record)
                record_index = len(self.history_data) - 1  # 获取索引作为ID

                # 2. 插入到 Treeview
                if self.history_tree:
                    # Treeview 显示文本的前 30 个字符（去除换行符）
                    display_text = new_record['text'].replace('\n', ' ').strip()
                    display_text = (display_text[:30] + '...') if len(display_text) > 30 else display_text

                    # 使用索引作为 Treeview 的 ID (iid) 和第一列的值 (#)
                    self.history_tree.insert(
                        '', 'end',
                        iid=record_index,
                        values=(
                            record_index,
                            new_record['time'],
                            new_record['source'],
                            display_text
                        )
                    )
                # =========================================================

        except concurrent.futures.CancelledError:
            self.status_var.set(f"状态：任务被取消 (耗时: {time_str})。")
            logger.warning("OCR 任务被取消。")
        except Exception as e:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"任务出错: {e}")
            self.status_var.set(f"状态：任务异常 (耗时: {time_str})。")
            logger.exception(f"OCR 任务执行异常: {e}")

        finally:
            # 恢复 UI 状态
            self._set_ui_state(tk.NORMAL)

    def reinitialize_ocr(self, event=None):
        """
        处理语言下拉菜单选择事件，根据需要重新初始化 OCR 模型。
        """
        try:
            from ocr_engine import init_paddle_ocr, get_rec_model_path_by_lang
        except ImportError:
            self.status_var.set("错误：无法导入 ocr_engine.py 中的所需函数。")
            return

        selected_lang_name = self.lang_var.get()
        new_lang_code = self.LANGUAGES.get(selected_lang_name)

        try:
            if not new_lang_code:
                raise ValueError(f"配置中未找到语言 {selected_lang_name} 的代码。")

            if new_lang_code == self.current_lang_code:
                self.status_var.set(f"状态：语言已是 {selected_lang_name}，无需切换。")
                self._set_ui_state(tk.NORMAL)
                return

            new_rec_path = get_rec_model_path_by_lang(new_lang_code)

            if new_rec_path is None:
                raise ValueError(f"不支持的语言代码 {new_lang_code}，模型路径查找失败。")

            if new_rec_path == self.current_rec_model_path:
                self.status_var.set(f"状态：模型路径相同 ({selected_lang_name})，跳过模型加载。")
                self.current_lang_code = new_lang_code
                self._set_ui_state(tk.NORMAL)
                return

            # --- 如果模型路径不同，则执行耗时的初始化 ---
            self._set_ui_state(tk.DISABLED)
            self.status_var.set(f"状态：正在加载 {selected_lang_name} 模型，请稍候...")
            self.progressbar.grid(row=0, column=1, sticky='nse', padx=5, pady=5)
            self.progressbar.start(10)

            future = self.executor.submit(
                init_paddle_ocr,
                lang=new_lang_code,
                executor=self.executor
            )

            future.add_done_callback(lambda f: self.master.after(0, self.update_ocr_instance, f))

        except ValueError as ve:
            self.status_var.set(f"错误：配置问题 - {ve}")
            logger.error(f"OCR 重新初始化配置失败: {ve}")
            self._set_ui_state(tk.NORMAL)
        except Exception as e:
            self.status_var.set(f"错误：初始化前发生异常 - {e}")
            logger.exception("OCR 重新初始化任务启动前发生异常。")
            self._set_ui_state(tk.NORMAL)

    def update_ocr_instance(self, future):
        """
        处理模型异步加载完成后的结果。
        """
        self.progressbar.stop()
        self.progressbar.grid_forget()

        try:
            new_ocr, _ = future.result()

            if new_ocr:
                self.ocr = new_ocr
                selected_lang_name = self.lang_var.get()
                self.current_lang_code = self.LANGUAGES.get(selected_lang_name)

                from ocr_engine import get_rec_model_path_by_lang
                self.current_rec_model_path = get_rec_model_path_by_lang(self.current_lang_code)

                self.status_var.set(f"状态：模型切换成功 ({self.lang_var.get()})。")
            else:
                self.ocr = None
                self.status_var.set(f"错误：模型切换失败，请检查模型文件。")
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, f"切换语言失败：OCR 实例未返回。")
                logger.error("模型切换失败：OCR 实例未返回。")

        except Exception as e:
            self.ocr = None
            self.status_var.set(f"错误：模型切换任务异常: {e}")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"切换语言任务异常：\n{e}")
            logger.exception("模型切换任务异常。")

        finally:
            self._set_ui_state(tk.NORMAL)

    # ----------------------------------------------------------------------
    # >>> 截图与识别逻辑 <<<
    # ----------------------------------------------------------------------
    def screenshot_and_recognize(self):
        # ... (保持不变) ...
        if self.executor is None or self.ocr is None or self.screenshot_taker_class is None:
            self.status_var.set("错误：OCR 或截图工具不可用。")
            return

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "--- 正在启动截图工具... ---")
        self.status_var.set("状态：请在屏幕上拖动鼠标选择区域 (ESC取消)...")

        self._set_ui_state(tk.DISABLED)
        self.progressbar.grid_forget()

        self.master.withdraw()

        def on_capture_done(img_pil):
            """
            截图完成后的回调函数。
            """
            self.master.deiconify()
            self.master.after(0, self._start_recognition_from_image, img_pil)

        try:
            taker = self.screenshot_taker_class(on_finish=on_capture_done)
            taker.take_screenshot()
        except Exception as e:
            self.master.deiconify()
            self._set_ui_state(tk.NORMAL)
            self.status_var.set(f"错误：截图工具启动失败: {e}")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"截图工具启动失败: {e}")
            logger.exception("截图工具启动失败。")

    def _start_recognition_from_image(self, img_pil: Image.Image or None, is_file=False):
        """
        在主线程中处理截图/文件加载结果，显示预览图，并启动异步 OCR 识别。
        """
        self._set_ui_state(tk.NORMAL)

        if img_pil is None:
            self.preview_label.config(image=None, text=PREVIEW_DEFAULT_TEXT, bg='light gray')
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "截图操作被用户取消或区域无效。")
            self.status_var.set("状态：操作取消。")
            return

        # 2. **>>> [核心：显示预览图逻辑] <<<**
        try:
            # 缩放图片
            thumb = img_pil.copy()
            thumb.thumbnail(PREVIEW_MAX_SIZE)

            # 转换为 Tkinter PhotoImage
            self.preview_image = ImageTk.PhotoImage(thumb)

            # 更新 Label
            self.preview_label.config(
                image=self.preview_image,
                text="",
                bg=self.master.cget('bg'),  # 设为窗口背景色
                width=thumb.width,  # 调整 Label 尺寸以适应图片
                height=thumb.height
            )
            logger.info("预览图已更新。")

        except Exception as e:
            logger.error(f"更新截图预览失败: {e}")
            self.preview_label.config(image=None, text="预览失败", bg='red')
        # ----------------------------------------------------

        # 3. 将 PIL Image 对象转换为内存字节流
        img_byte_arr = io.BytesIO()
        try:
            img_pil.save(img_byte_arr, format='PNG')
        except Exception as e:
            self.status_var.set(f"错误：图片转换为字节流失败: {e}")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"图片转换失败: {e}")
            logger.exception("PIL Image 转换为字节流失败。")
            return

        img_bytes = img_byte_arr.getvalue()

        # 4. 启动识别任务 (识别阶段需要再次禁用 UI 并显示进度)
        if is_file:
            self.result_text.insert(tk.END, "\n--- 文件加载成功，正在识别... ---")
            self.status_var.set("状态：正在处理文件...")
        else:
            self.file_path_var.set("当前图片来自屏幕截图")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "--- 截图捕获成功，正在识别... ---")
            self.status_var.set("状态：正在处理截图...")

        self._set_ui_state(tk.DISABLED)
        self.progressbar.grid(row=0, column=1, sticky='nse', padx=5, pady=5)
        self.progressbar.start(10)

        start_time = time.time()

        # 5. 提交识别任务 (根据来源使用 is_path=False)
        future_recognize = self.executor.submit(self.recognize_func, self.ocr, img_bytes, is_path=False)
        future_recognize.add_done_callback(lambda f: self.master.after(0, self.update_ui_with_result, f, start_time))

    def _set_ui_state(self, state):
        """辅助函数：统一设置 UI 状态"""
        is_normal = (state == tk.NORMAL)

        self.select_button.config(state=state)
        self.lang_combo.config(state=("readonly" if is_normal else tk.DISABLED))

        if self.screenshot_taker_class:
            self.screenshot_button.config(state=state)

        if is_normal and not self.ocr:
            self.select_button.config(state=tk.DISABLED)
            if self.screenshot_taker_class:
                self.screenshot_button.config(state=tk.DISABLED)