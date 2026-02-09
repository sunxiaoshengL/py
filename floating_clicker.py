import sys
import threading
import random
import time
from datetime import datetime

import pyautogui
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
                             QLabel, QSpinBox, QDoubleSpinBox, QRadioButton, QButtonGroup,
                             QCheckBox, QGroupBox, QTabWidget, QListWidget, QDialog,
                             QMessageBox, QComboBox, QFrame, QScrollArea, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QKeySequence
from pynput import mouse, keyboard as kb


class WorkerSignals(QObject):
    """工作线程信号"""
    status_update = pyqtSignal(str)
    finished = pyqtSignal()
    recording_update = pyqtSignal(str)


class FloatingClicker(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("智能连点器 Pro")
        self.setGeometry(350, 150, 500, 650)
        self.setMinimumSize(450, 500)  # 设置最小尺寸
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        # 设置简洁现代的样式
        self.setStyleSheet("""
            QWidget {
                background: #ffffff;
                color: #2c3e50;
                font-family: 'Microsoft YaHei', 'Segoe UI', Arial;
                font-size: 10pt;
            }
            QGroupBox {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #34495e;
                background: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #2c3e50;
                background: transparent;
            }
            QSpinBox, QDoubleSpinBox {
                background: white;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                padding: 5px;
                color: #2c3e50;
                min-width: 100px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #3498db;
            }
            QRadioButton, QCheckBox {
                color: #2c3e50;
                spacing: 5px;
                background: transparent;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:checked {
                background: #3498db;
                border: 2px solid #2980b9;
                border-radius: 8px;
            }
            QRadioButton::indicator:unchecked {
                background: white;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:checked {
                background: #3498db;
                border: 2px solid #2980b9;
            }
            QCheckBox::indicator:unchecked {
                background: white;
                border: 2px solid #bdc3c7;
            }
            QListWidget {
                background: white;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                padding: 5px;
                color: #2c3e50;
            }
            QListWidget::item {
                padding: 6px;
                border-radius: 3px;
                margin: 1px;
            }
            QListWidget::item:selected {
                background: #e3f2fd;
                color: #1976d2;
            }
            QListWidget::item:hover {
                background: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background: white;
                top: -1px;
            }
            QTabBar::tab {
                background: #f0f0f0;
                color: #7f8c8d;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: white;
                color: #3498db;
                border-bottom: 2px solid #3498db;
            }
            QTabBar::tab:hover {
                background: #e8e8e8;
            }
            QPushButton {
                background: white;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                padding: 8px;
                color: #2c3e50;
            }
            QPushButton:hover {
                background: #f5f5f5;
                border: 1px solid #3498db;
            }
            QPushButton:pressed {
                background: #e8e8e8;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        # 状态控制
        self.stop_event = threading.Event()
        self.stop_event.set()
        self.signals = WorkerSignals()
        self.signals.status_update.connect(self.update_status)
        self.signals.finished.connect(self.on_task_finished)
        self.signals.recording_update.connect(self.update_recording_status)
        
        # 多点模式数据
        self.recorded_actions = []
        self.is_recording = False
        self.recording_start_time = 0
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # 设置全局快捷键监听
        self.setup_global_hotkey()
        
        self.init_ui()
    
    def setup_global_hotkey(self):
        """设置全局快捷键 F9 切换录制"""
        def on_press(key):
            try:
                if key == kb.Key.f9:
                    # 只在多点模式下响应快捷键
                    if self.tabs.currentIndex() == 1:
                        self.toggle_recording()
            except:
                pass
        
        self.keyboard_listener = kb.Listener(on_press=on_press)
        self.keyboard_listener.start()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题
        title = QLabel("智能连点器 Pro")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            color: #3498db;
            padding: 10px;
            background: #e3f2fd;
            border-radius: 8px;
        """)
        main_layout.addWidget(title)
        
        # 状态显示
        self.status_label = QLabel("● 就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.status_label.setStyleSheet("""
            padding: 8px;
            background: #e8f5e9;
            border: 1px solid #4caf50;
            border-radius: 6px;
            color: #2e7d32;
        """)
        main_layout.addWidget(self.status_label)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(10)
        
        # 模式选择标签页
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_single_mode_tab(), "单点模式")
        self.tabs.addTab(self.create_multi_mode_tab(), "多点模式")
        content_layout.addWidget(self.tabs)
        
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # 开始/停止按钮
        self.start_btn = QPushButton("▶ 开始执行")
        self.start_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #4caf50;
                color: white;
                padding: 12px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background: #45a049;
            }
            QPushButton:pressed {
                background: #3d8b40;
            }
        """)
        self.start_btn.clicked.connect(self.toggle_clicking)
        main_layout.addWidget(self.start_btn)
        
        self.setLayout(main_layout)
    
    def create_single_mode_tab(self):
        """创建单点模式界面"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 使用说明
        help_text = QLabel("📖 使用说明：设置参数后点击「开始执行」，程序会在当前鼠标位置自动点击")
        help_text.setWordWrap(True)
        help_text.setStyleSheet("""
            padding: 8px;
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 4px;
            color: #856404;
            font-size: 9pt;
        """)
        layout.addWidget(help_text)
        
        # 点击间隔设置
        interval_group = QGroupBox("点击间隔")
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("间隔时间:"))
        self.single_interval = QDoubleSpinBox()
        self.single_interval.setRange(0.01, 60.0)
        self.single_interval.setValue(0.15)
        self.single_interval.setSuffix(" 秒")
        self.single_interval.setDecimals(2)
        interval_layout.addWidget(self.single_interval)
        interval_layout.addStretch()
        interval_group.setLayout(interval_layout)
        layout.addWidget(interval_group)
        
        # 循环模式设置
        loop_group = QGroupBox("循环模式")
        loop_layout = QVBoxLayout()
        loop_layout.setSpacing(8)
        
        self.loop_mode_group = QButtonGroup()
        self.loop_infinite = QRadioButton("无限循环")
        self.loop_infinite.setChecked(True)
        self.loop_time = QRadioButton("定时循环")
        self.loop_count = QRadioButton("次数循环")
        
        self.loop_mode_group.addButton(self.loop_infinite, 0)
        self.loop_mode_group.addButton(self.loop_time, 1)
        self.loop_mode_group.addButton(self.loop_count, 2)
        
        loop_layout.addWidget(self.loop_infinite)
        
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.loop_time)
        self.loop_time_value = QSpinBox()
        self.loop_time_value.setRange(1, 1440)
        self.loop_time_value.setValue(5)
        self.loop_time_value.setSuffix(" 分钟")
        time_layout.addWidget(self.loop_time_value)
        time_layout.addStretch()
        loop_layout.addLayout(time_layout)
        
        count_layout = QHBoxLayout()
        count_layout.addWidget(self.loop_count)
        self.loop_count_value = QSpinBox()
        self.loop_count_value.setRange(1, 999999)
        self.loop_count_value.setValue(100)
        self.loop_count_value.setSuffix(" 次")
        count_layout.addWidget(self.loop_count_value)
        count_layout.addStretch()
        loop_layout.addLayout(count_layout)
        
        loop_group.setLayout(loop_layout)
        layout.addWidget(loop_group)
        
        # 反检测设置
        detect_group = QGroupBox("反检测设置")
        detect_layout = QVBoxLayout()
        self.anti_detect = QCheckBox("启用反检测 (随机间隔±20% 和位置±3px)")
        self.anti_detect.setChecked(True)
        detect_layout.addWidget(self.anti_detect)
        detect_group.setLayout(detect_layout)
        layout.addWidget(detect_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_multi_mode_tab(self):
        """创建多点模式界面"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 使用说明
        help_text = QLabel("📖 使用说明：\n1. 点击「开始录制」或按 F9\n2. 在屏幕上点击要自动化的位置\n3. 再次点击「停止录制」或按 F9\n4. 双击列表项可修改间隔时间\n5. 点击「开始执行」重放操作")
        help_text.setWordWrap(True)
        help_text.setStyleSheet("""
            padding: 8px;
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 4px;
            color: #856404;
            font-size: 9pt;
        """)
        layout.addWidget(help_text)
        
        # 录制状态
        self.recording_status = QLabel("⏺ 未录制")
        self.recording_status.setAlignment(Qt.AlignCenter)
        self.recording_status.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.recording_status.setStyleSheet("""
            padding: 8px;
            background: #f5f5f5;
            border: 1px solid #bdbdbd;
            border-radius: 6px;
            color: #757575;
        """)
        layout.addWidget(self.recording_status)
        
        # 录制控制按钮
        record_btn_layout = QHBoxLayout()
        
        self.record_btn = QPushButton("⏺ 开始录制 (F9)")
        self.record_btn.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.record_btn.setStyleSheet("""
            QPushButton {
                background: #f44336;
                color: white;
                padding: 10px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #da190b;
            }
            QPushButton:pressed {
                background: #c62828;
            }
        """)
        self.record_btn.clicked.connect(self.toggle_recording)
        record_btn_layout.addWidget(self.record_btn)
        
        clear_btn = QPushButton("🗑 清空")
        clear_btn.setFont(QFont("Microsoft YaHei", 10))
        clear_btn.clicked.connect(self.clear_recording)
        record_btn_layout.addWidget(clear_btn)
        
        layout.addLayout(record_btn_layout)
        
        # 操作列表
        actions_group = QGroupBox("已录制操作 (双击可修改间隔)")
        actions_layout = QVBoxLayout()
        self.actions_list = QListWidget()
        self.actions_list.setMinimumHeight(150)
        self.actions_list.itemDoubleClicked.connect(self.edit_action_interval)
        actions_layout.addWidget(self.actions_list)
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # 循环设置
        loop_group = QGroupBox("循环设置")
        loop_layout = QHBoxLayout()
        loop_layout.addWidget(QLabel("循环次数:"))
        self.multi_loop_count = QSpinBox()
        self.multi_loop_count.setRange(1, 9999)
        self.multi_loop_count.setValue(1)
        self.multi_loop_count.setSuffix(" 次")
        loop_layout.addWidget(self.multi_loop_count)
        loop_layout.addStretch()
        loop_group.setLayout(loop_layout)
        layout.addWidget(loop_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        return widget
    
    def toggle_clicking(self):
        """切换开始/停止"""
        if self.stop_event.is_set():
            self.start_clicking()
        else:
            self.stop_clicking()
    
    def start_clicking(self):
        """开始点击"""
        current_mode = self.tabs.currentIndex()
        
        if current_mode == 1 and len(self.recorded_actions) == 0:
            QMessageBox.warning(self, "警告", "多点模式下请先录制操作！")
            return
        
        if current_mode == 1 and self.is_recording:
            QMessageBox.warning(self, "警告", "请先停止录制！")
            return
        
        self.stop_event.clear()
        self.start_btn.setText("⏸ 停止执行")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #f44336;
                color: white;
                padding: 12px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background: #da190b;
            }
            QPushButton:pressed {
                background: #c62828;
            }
        """)
        
        if current_mode == 0:
            threading.Thread(target=self.single_mode_worker, daemon=True).start()
        else:
            threading.Thread(target=self.multi_mode_worker, daemon=True).start()
    
    def stop_clicking(self):
        """停止点击"""
        self.stop_event.set()
        self.start_btn.setText("▶ 开始执行")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #4caf50;
                color: white;
                padding: 12px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background: #45a049;
            }
            QPushButton:pressed {
                background: #3d8b40;
            }
        """)
        self.signals.status_update.emit("● 已停止")
        self.status_label.setStyleSheet("""
            padding: 8px;
            background: #ffebee;
            border: 1px solid #f44336;
            border-radius: 6px;
            color: #c62828;
        """)
    
    def single_mode_worker(self):
        """单点模式工作线程"""
        try:
            loop_mode = self.loop_mode_group.checkedId()
            interval = self.single_interval.value()
            anti_detect = self.anti_detect.isChecked()
            
            start_time = time.time()
            click_count = 0
            max_clicks = self.loop_count_value.value() if loop_mode == 2 else float('inf')
            max_duration = self.loop_time_value.value() * 60 if loop_mode == 1 else float('inf')
            
            time.sleep(1)  # 初始延迟
            
            self.signals.status_update.emit("● 运行中")
            self.status_label.setStyleSheet("""
                padding: 8px;
                background: #e8f5e9;
                border: 1px solid #4caf50;
                border-radius: 6px;
                color: #2e7d32;
            """)
            
            while not self.stop_event.is_set():
                if click_count >= max_clicks:
                    break
                if time.time() - start_time >= max_duration:
                    break
                
                x, y = pyautogui.position()
                
                if anti_detect:
                    x += random.randint(-3, 3)
                    y += random.randint(-3, 3)
                    pyautogui.moveTo(x, y, duration=random.uniform(0.03, 0.08))
                
                pyautogui.click(x, y)
                click_count += 1
                
                self.signals.status_update.emit(f"● 运行中 | 已点击: {click_count} 次")
                
                actual_interval = interval
                if anti_detect:
                    actual_interval *= random.uniform(0.8, 1.2)
                
                time.sleep(actual_interval)
            
            self.signals.finished.emit()
            
        except Exception as e:
            print(f"Error: {e}")
            self.signals.finished.emit()
    
    def multi_mode_worker(self):
        """多点模式工作线程"""
        try:
            loop_count_max = self.multi_loop_count.value()
            
            time.sleep(1)  # 初始延迟
            
            self.signals.status_update.emit("● 状态: 运行中")
            self.status_label.setStyleSheet("""
                padding: 12px;
                background: rgba(46, 204, 113, 0.2);
                border: 2px solid #2ecc71;
                border-radius: 8px;
                color: #2ecc71;
                font-weight: bold;
            """)
            
            for cycle in range(loop_count_max):
                if self.stop_event.is_set():
                    break
                
                self.signals.status_update.emit(f"● 状态: 运行中 | 循环: {cycle + 1}/{loop_count_max}")
                
                last_time = 0
                for action_data in self.recorded_actions:
                    if self.stop_event.is_set():
                        break
                    
                    action_type, x, y, timestamp = action_data
                    
                    # 等待到指定时间
                    delay = timestamp - last_time
                    if delay > 0:
                        time.sleep(delay)
                    
                    # 执行点击
                    pyautogui.click(x, y)
                    last_time = timestamp
            
            self.signals.finished.emit()
            
        except Exception as e:
            print(f"Error: {e}")
            self.signals.finished.emit()
    
    def update_status(self, text):
        """更新状态显示"""
        self.status_label.setText(text)
    
    def on_task_finished(self):
        """任务完成回调"""
        self.stop_clicking()
        self.signals.status_update.emit("● 已完成")
        self.status_label.setStyleSheet("""
            padding: 8px;
            background: #e3f2fd;
            border: 1px solid #2196f3;
            border-radius: 6px;
            color: #1565c0;
        """)
    
    def toggle_recording(self):
        """切换录制状态"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """开始录制"""
        self.is_recording = True
        self.recorded_actions = []
        self.actions_list.clear()
        self.recording_start_time = time.time()
        
        self.record_btn.setText("⏹ 停止录制 (F9)")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background: #757575;
                color: white;
                padding: 10px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #616161;
            }
            QPushButton:pressed {
                background: #424242;
            }
        """)
        
        self.recording_status.setText("⏺ 录制中...")
        self.recording_status.setStyleSheet("""
            padding: 8px;
            background: #ffebee;
            border: 1px solid #f44336;
            border-radius: 6px;
            color: #c62828;
        """)
        
        # 启动鼠标监听
        def on_click(x, y, button, pressed):
            if pressed and self.is_recording:
                # 检查点击是否在应用窗口内
                window_geometry = self.geometry()
                window_x = self.x()
                window_y = self.y()
                window_width = window_geometry.width()
                window_height = window_geometry.height()
                
                # 如果点击在窗口范围内，则忽略
                if (window_x <= x <= window_x + window_width and 
                    window_y <= y <= window_y + window_height):
                    return
                
                # 记录窗口外的点击
                elapsed = time.time() - self.recording_start_time
                self.recorded_actions.append(('click', x, y, elapsed))
                
                # 计算与上次点击的间隔
                if len(self.recorded_actions) > 1:
                    prev_time = self.recorded_actions[-2][3]
                    interval = elapsed - prev_time
                    self.signals.recording_update.emit(
                        f"#{len(self.recorded_actions)} | 位置: ({x}, {y}) | 间隔: {interval:.2f}秒"
                    )
                else:
                    self.signals.recording_update.emit(
                        f"#{len(self.recorded_actions)} | 位置: ({x}, {y}) | 间隔: 0.00秒"
                    )
        
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()
    
    def stop_recording(self):
        """停止录制"""
        self.is_recording = False
        
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        
        self.record_btn.setText("⏺ 开始录制 (F9)")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background: #f44336;
                color: white;
                padding: 10px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #da190b;
            }
            QPushButton:pressed {
                background: #c62828;
            }
        """)
        
        if len(self.recorded_actions) > 0:
            self.recording_status.setText(f"✓ 已录制 {len(self.recorded_actions)} 个操作")
            self.recording_status.setStyleSheet("""
                padding: 8px;
                background: #e8f5e9;
                border: 1px solid #4caf50;
                border-radius: 6px;
                color: #2e7d32;
            """)
        else:
            self.recording_status.setText("⏺ 未录制")
            self.recording_status.setStyleSheet("""
                padding: 8px;
                background: #f5f5f5;
                border: 1px solid #bdbdbd;
                border-radius: 6px;
                color: #757575;
            """)
    
    def clear_recording(self):
        """清空录制"""
        if self.is_recording:
            self.stop_recording()
        
        self.recorded_actions = []
        self.actions_list.clear()
        self.recording_status.setText("⏺ 未录制")
        self.recording_status.setStyleSheet("""
            padding: 8px;
            background: #f5f5f5;
            border: 1px solid #bdbdbd;
            border-radius: 6px;
            color: #757575;
        """)
    
    def edit_action_interval(self, item):
        """编辑操作的间隔时间"""
        row = self.actions_list.row(item)
        if row < 0 or row >= len(self.recorded_actions):
            return
        
        action_type, x, y, timestamp = self.recorded_actions[row]
        
        # 计算当前间隔
        if row > 0:
            prev_timestamp = self.recorded_actions[row - 1][3]
            current_interval = timestamp - prev_timestamp
        else:
            current_interval = timestamp
        
        # 弹出对话框让用户输入新的间隔
        from PyQt5.QtWidgets import QInputDialog
        dialog = QInputDialog(self)
        dialog.setWindowTitle("修改间隔时间")
        dialog.setLabelText(f"当前间隔: {current_interval:.2f}秒\n请输入新的间隔时间(秒):")
        dialog.setDoubleRange(0.0, 3600.0)
        dialog.setDoubleValue(current_interval)
        dialog.setDoubleDecimals(2)
        
        # 设置按钮文本为中文
        dialog.setOkButtonText("完成")
        dialog.setCancelButtonText("取消")
        
        if dialog.exec_() == QInputDialog.Accepted:
            new_interval = dialog.doubleValue()
            ok = True
        else:
            new_interval = current_interval
            ok = False
        
        if ok:
            # 更新时间戳
            if row > 0:
                prev_timestamp = self.recorded_actions[row - 1][3]
                new_timestamp = prev_timestamp + new_interval
            else:
                new_timestamp = new_interval
            
            # 更新当前操作的时间戳
            self.recorded_actions[row] = (action_type, x, y, new_timestamp)
            
            # 更新后续所有操作的时间戳
            time_diff = new_timestamp - timestamp
            for i in range(row + 1, len(self.recorded_actions)):
                act_type, act_x, act_y, act_time = self.recorded_actions[i]
                self.recorded_actions[i] = (act_type, act_x, act_y, act_time + time_diff)
            
            # 刷新列表显示
            self.refresh_actions_list()
    
    def refresh_actions_list(self):
        """刷新操作列表显示"""
        self.actions_list.clear()
        for i, (action_type, x, y, timestamp) in enumerate(self.recorded_actions):
            if i > 0:
                prev_time = self.recorded_actions[i - 1][3]
                interval = timestamp - prev_time
            else:
                interval = timestamp
            
            self.actions_list.addItem(
                f"#{i + 1} | 位置: ({x}, {y}) | 间隔: {interval:.2f}秒"
            )
    
    def update_recording_status(self, text):
        """更新录制列表"""
        self.actions_list.addItem(text)


if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    
    app = QApplication(sys.argv)
    win = FloatingClicker()
    win.show()
    sys.exit(app.exec_())