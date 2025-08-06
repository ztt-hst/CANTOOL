import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import time
from datetime import datetime
import json
import struct
import ctypes
from ctypes import *
from can_protocol_config import *  # 导入配置文件
from language_manager import LanguageManager  # 导入语言管理器
import os
import sys

# 创芯科技CAN API常量
VCI_USBCAN2 = 4
STATUS_OK = 1

class VCI_INIT_CONFIG(Structure):  
    _fields_ = [("AccCode", c_uint),
                ("AccMask", c_uint),
                ("Reserved", c_uint),
                ("Filter", c_ubyte),
                ("Timing0", c_ubyte),
                ("Timing1", c_ubyte),
                ("Mode", c_ubyte)
                ]  

class VCI_CAN_OBJ(Structure):  
    _fields_ = [("ID", c_uint),
                ("TimeStamp", c_uint),
                ("TimeFlag", c_ubyte),
                ("SendType", c_ubyte),
                ("RemoteFlag", c_ubyte),
                ("ExternFlag", c_ubyte),
                ("DataLen", c_ubyte),
                ("Data", c_ubyte*8),
                ("Reserved", c_ubyte*3)
                ] 

class VCI_CAN_OBJ_ARRAY(Structure):
    _fields_ = [('SIZE', ctypes.c_uint16), ('STRUCT_ARRAY', ctypes.POINTER(VCI_CAN_OBJ))]

    def __init__(self, num_of_structs):
        self.STRUCT_ARRAY = ctypes.cast((VCI_CAN_OBJ * num_of_structs)(), ctypes.POINTER(VCI_CAN_OBJ))
        self.SIZE = num_of_structs
        self.ADDR = self.STRUCT_ARRAY[0]

class CANalystCANBus:
    """创芯科技CAN总线类"""
    def __init__(self, device_type=VCI_USBCAN2, device_index=0, can_index=0):
        self.device_type = device_type
        self.device_index = device_index
        self.can_index = can_index
        self.can_dll = None
        self.is_connected = False
        
    def connect(self, baudrate=500000):
        """连接CAN设备"""
        try:
            # 加载DLL
            self.can_dll = windll.LoadLibrary('./ControlCAN.dll')
            
            # 打开设备
            ret = self.can_dll.VCI_OpenDevice(self.device_type, self.device_index, 0)
            if ret != STATUS_OK:
                raise Exception("打开设备失败")
                
            # 设置波特率
            timing0, timing1 = self.get_timing(baudrate)
            
            # 初始化CAN
            vci_initconfig = VCI_INIT_CONFIG(0x80000008, 0xFFFFFFFF, 0,
                                           0, timing0, timing1, 0)
            ret = self.can_dll.VCI_InitCAN(self.device_type, self.device_index, 
                                          self.can_index, byref(vci_initconfig))
            if ret != STATUS_OK:
                raise Exception("初始化CAN失败")
                
            # 启动CAN
            ret = self.can_dll.VCI_StartCAN(self.device_type, self.device_index, self.can_index)
            if ret != STATUS_OK:
                raise Exception("启动CAN失败")
                
            self.is_connected = True
            return True
            
        except Exception as e:
            raise Exception(f"连接CAN设备失败: {str(e)}")
            
    def get_timing(self, baudrate):
        """根据波特率获取定时参数"""
        timing_map = {
            250000: (0x03, 0x1C),  # 250kbps
            500000: (0x00, 0x1C),  # 500kbps
        }
        return timing_map.get(baudrate, (0x00, 0x1C))
        
    def send(self, can_id, data):
        """发送CAN报文"""
        if not self.is_connected:
            raise Exception("CAN设备未连接")
            
        # 创建数据数组
        ubyte_array = c_ubyte * 8
        can_data = ubyte_array(*data[:8])
        
        # 创建CAN对象
        ubyte_3array = c_ubyte * 3
        reserved = ubyte_3array(0, 0, 0)
        vci_can_obj = VCI_CAN_OBJ(can_id, 0, 0, 1, 0, 0, len(data), can_data, reserved)
        
        # 发送数据
        ret = self.can_dll.VCI_Transmit(self.device_type, self.device_index, 
                                       self.can_index, byref(vci_can_obj), 1)
        if ret != STATUS_OK:
            raise Exception("发送CAN报文失败")
            
    def receive(self, timeout=100):
        """接收CAN报文"""
        if not self.is_connected:
            return None
            
        try:
            # 创建接收缓冲区
            rx_vci_can_obj = VCI_CAN_OBJ_ARRAY(2500)
            
            # 接收数据
            ret = self.can_dll.VCI_Receive(self.device_type, self.device_index, 
                                          self.can_index, byref(rx_vci_can_obj.ADDR), 2500, timeout)
            
            if ret > 0:
                messages = []
                for i in range(ret):
                    msg = rx_vci_can_obj.STRUCT_ARRAY[i]
                    data = list(msg.Data[:msg.DataLen])
                    messages.append({
                        'id': msg.ID,
                        'data': data,
                        'length': msg.DataLen,
                        'timestamp': msg.TimeStamp
                    })
                return messages
            elif ret == 0:
                # 超时，没有接收到数据
                return None
            else:
                # 接收错误
                print(f"VCI_Receive返回错误: {ret}")
                return None
                
        except Exception as e:
            print(f"接收CAN报文错误: {str(e)}")
            return None
        
    def disconnect(self):
        """断开连接"""
        if self.can_dll and self.is_connected:
            self.can_dll.VCI_CloseDevice(self.device_type, self.device_index)
            self.is_connected = False

class CANHostComputer:
    def __init__(self, root):
        self.root = root
        
        # 初始化语言管理器
        self.lang_manager = LanguageManager('chinese')
        
        self.root.title(self.lang_manager.get_text('window_title'))
        
        # 设置窗口图标
        self.set_window_icon()
        
        # 设置窗口初始大小和最小尺寸
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # CAN相关变量
        self.can_bus = None
        self.is_connected = False
        self.is_running = False
        self.is_receiving = False
        self.last_heartbeat_time = None
        self.heartbeat_monitor_thread = None
        
        # 统计变量
        self.sent_count = 0
        self.received_count = 0
        self.heartbeat_count = 0
        
        # 发送统计变量
        self.sent_305_count = 0
        self.sent_307_count = 0
        
        # 创建界面
        self.create_widgets()
    
    def set_window_icon(self):
        """设置窗口图标"""
        import os
        import sys
        
        # 获取程序运行路径
        if getattr(sys, 'frozen', False):
            # 打包后的路径
            application_path = sys._MEIPASS
        else:
            # 开发环境路径
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        # 尝试多个可能的图标路径
        icon_paths = [
            os.path.join(application_path, 'BQC.ico'),
            os.path.join(application_path, 'icons', 'BQC.ico'),
            'BQC.ico',
            './BQC.ico',
            './icons/BQC.ico'
        ]
        
        icon_loaded = False
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    self.root.iconbitmap(icon_path)
                    icon_loaded = True
                    print(f"成功设置窗口图标: {icon_path}")
                    break
                except Exception as e:
                    print(f"设置图标失败 {icon_path}: {str(e)}")
                    continue
        
        if not icon_loaded:
            print("警告: 未找到有效的图标文件")
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 语言切换按钮 - 添加到顶部
        lang_frame = ttk.Frame(main_frame)
        lang_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(lang_frame, text="Language/语言:").pack(side="left")
        lang_var = tk.StringVar(value=self.lang_manager.get_current_language())
        lang_combo = ttk.Combobox(lang_frame, textvariable=lang_var, 
                                 values=self.lang_manager.get_available_languages(), 
                                 state="readonly", width=10)
        lang_combo.pack(side="left", padx=5)
        lang_combo.bind('<<ComboboxSelected>>', lambda e: self.switch_language(lang_var.get()))
        
        # 连接设置框架
        connection_frame = ttk.LabelFrame(main_frame, text=self.lang_manager.get_text('connection_settings'), padding="10")
        connection_frame.pack(fill="x", pady=5)
        
        # 第一行：设备设置
        row1 = ttk.Frame(connection_frame)
        row1.pack(fill="x", pady=2)
        
        ttk.Label(row1, text=self.lang_manager.get_text('device_type') + ":").pack(side="left", padx=5)
        self.device_type_var = tk.StringVar(value="VCI_USBCAN2")
        device_type_combo = ttk.Combobox(row1, textvariable=self.device_type_var, 
                                       values=["VCI_USBCAN2"], width=15, state="readonly")
        device_type_combo.pack(side="left", padx=5)
        
        ttk.Label(row1, text=self.lang_manager.get_text('device_index') + ":").pack(side="left", padx=5)
        self.device_index_var = tk.StringVar(value="0")
        device_index_combo = ttk.Combobox(row1, textvariable=self.device_index_var, 
                                        values=["0", "1"], width=5)
        device_index_combo.pack(side="left", padx=5)
        
        ttk.Label(row1, text=self.lang_manager.get_text('can_channel') + ":").pack(side="left", padx=5)
        self.can_index_var = tk.StringVar(value="0")
        can_index_combo = ttk.Combobox(row1, textvariable=self.can_index_var, 
                                      values=["0", "1"], width=5)
        can_index_combo.pack(side="left", padx=5)
        
        # 第二行：波特率设置
        row2 = ttk.Frame(connection_frame)
        row2.pack(fill="x", pady=2)
        
        ttk.Label(row2, text=self.lang_manager.get_text('baudrate') + ":").pack(side="left", padx=5)
        self.baudrate_var = tk.StringVar(value="500000")
        baudrate_combo = ttk.Combobox(row2, textvariable=self.baudrate_var,
                                     values=["250000", "500000"], width=10)
        baudrate_combo.pack(side="left", padx=5)
        
        # 连接按钮
        self.connect_btn = ttk.Button(row2, text=self.lang_manager.get_text('connect'), command=self.connect_can)
        self.connect_btn.pack(side="left", padx=10)
        
        self.disconnect_btn = ttk.Button(row2, text=self.lang_manager.get_text('disconnect'), command=self.disconnect_can, state="disabled")
        self.disconnect_btn.pack(side="left", padx=5)
        
        # 控制框架
        control_frame = ttk.LabelFrame(main_frame, text=self.lang_manager.get_text('control'), padding="10")
        control_frame.pack(fill="x", pady=5)
        
        # 控制按钮
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill="x")
        
        # 发送控制
        send_frame = ttk.Frame(btn_frame)
        send_frame.pack(side="left", padx=10)
        
        ttk.Label(send_frame, text=self.lang_manager.get_text('send_control') + ":").pack(side="left")
        self.start_btn = ttk.Button(send_frame, text=self.lang_manager.get_text('start_sending'), command=self.start_sending, state="disabled")
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(send_frame, text=self.lang_manager.get_text('stop_sending'), command=self.stop_sending, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        # 接收控制
        receive_frame = ttk.Frame(btn_frame)
        receive_frame.pack(side="left", padx=10)
        
        ttk.Label(receive_frame, text=self.lang_manager.get_text('receive_control') + ":").pack(side="left")
        self.receive_var = tk.BooleanVar(value=False)
        self.receive_check = ttk.Checkbutton(receive_frame, text=self.lang_manager.get_text('enable_receiving'), 
                                           variable=self.receive_var, 
                                           command=self.toggle_receive, 
                                           state="disabled")
        self.receive_check.pack(side="left", padx=5)
        
        # 状态显示
        self.status_var = tk.StringVar(value=self.lang_manager.get_text('not_connected'))
        status_label = ttk.Label(btn_frame, textvariable=self.status_var)
        status_label.pack(side="right", padx=5)
        
        # 统计信息框架
        stats_frame = ttk.LabelFrame(main_frame, text=self.lang_manager.get_text('statistics'), padding="10")
        stats_frame.pack(fill="x", pady=5)
        
        stats_inner = ttk.Frame(stats_frame)
        stats_inner.pack(fill="x")
        
        # 发送统计
        ttk.Label(stats_inner, text=self.lang_manager.get_text('sent') + ":").grid(row=0, column=0, sticky="w", padx=5)
        self.sent_count_var = tk.StringVar(value="0")
        ttk.Label(stats_inner, textvariable=self.sent_count_var).grid(row=0, column=1, padx=5)
        
        # 接收统计
        ttk.Label(stats_inner, text=self.lang_manager.get_text('received') + ":").grid(row=0, column=2, sticky="w", padx=5)
        self.received_count_var = tk.StringVar(value="0")
        ttk.Label(stats_inner, textvariable=self.received_count_var).grid(row=0, column=3, padx=5)
        
        # 心跳状态
        ttk.Label(stats_inner, text=self.lang_manager.get_text('heartbeat_status') + ":").grid(row=0, column=4, sticky="w", padx=5)
        self.heartbeat_status_var = tk.StringVar(value=self.lang_manager.get_text('waiting'))
        ttk.Label(stats_inner, textvariable=self.heartbeat_status_var).grid(row=0, column=5, padx=5)
        
        # 创建左右分栏布局
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True, pady=5)
        
        # 左侧：发送数据和实时数据
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # 发送数据显示框架
        send_data_frame = ttk.LabelFrame(left_frame, text=self.lang_manager.get_text('send_data'), padding="10")
        send_data_frame.pack(fill="x", pady=5)
        
        # 创建发送数据表格
        self.create_send_data_table(send_data_frame)
        
        # 实时数据表格显示框架
        data_frame = ttk.LabelFrame(left_frame, text=self.lang_manager.get_text('real_time_data'), padding="10")
        data_frame.pack(fill="both", expand=True, pady=5)
        
        # 创建表格
        self.create_data_table(data_frame)
        
        # 右侧：日志框架
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        # 日志框架
        log_frame = ttk.LabelFrame(right_frame, text=self.lang_manager.get_text('communication_log'), padding="10")
        log_frame.pack(fill="both", expand=True)
        
        # 日志控制按钮 - 移到日志文本框上方
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill="x", pady=(0, 5))
        
        clear_btn = ttk.Button(log_btn_frame, text=self.lang_manager.get_text('clear_log'), command=self.clear_log)
        clear_btn.pack(side="left")
        
        # 将保存日志按钮改为勾选框 - 默认不勾选
        self.auto_save_var = tk.BooleanVar(value=False)  # 改为False，默认不勾选
        self.auto_save_check = ttk.Checkbutton(log_btn_frame, text=self.lang_manager.get_text('auto_save_log'), 
                                             variable=self.auto_save_var, 
                                             command=self.toggle_auto_save)
        self.auto_save_check.pack(side="left", padx=5)
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_text.pack(fill="both", expand=True)
        
        # 配置文本标签颜色
        self.log_text.tag_configure("heartbeat_red", foreground="red")
        
        # 初始化日志文件相关变量
        self.log_file = None
        self.log_filename = None
        
        # 移除自动开始保存日志的调用
        # self.start_auto_save_on_startup()  # 注释掉这行
    
    def toggle_auto_save(self):
        """切换自动保存日志功能"""
        if self.auto_save_var.get():
            self.start_auto_save()
        else:
            self.stop_auto_save()
    
    def start_auto_save(self):
        """开始自动保存日志 - 让用户选择保存路径和文件名"""
        try:
            # 弹出文件选择对话框
            filename = filedialog.asksaveasfilename(
                title=self.lang_manager.get_text('select_log_file'),
                defaultextension=".txt",
                filetypes=[
                    ("文本文件", "*.txt"),
                    ("日志文件", "*.log"),
                    ("所有文件", "*.*")
                ],
                initialfile=f"can_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"  # 修正参数名
            )
            
            if filename:  # 用户选择了文件
                # 打开日志文件
                self.log_file = open(filename, 'w', encoding='utf-8')
                self.log_filename = filename
                
                # 写入日志文件头部信息
                header = f"CAN协议上位机日志文件\n"
                header += f"创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                header += f"设备类型: 创芯科技CANalyst-II\n"
                header += "=" * 50 + "\n\n"
                
                self.log_file.write(header)
                self.log_file.flush()  # 立即写入文件
                
                self.log_message(f"自动保存日志已开启，日志文件: {self.log_filename}")
                
            else:
                # 用户取消了文件选择，取消勾选
                self.auto_save_var.set(False)
                
        except Exception as e:
            messagebox.showerror("错误", f"无法创建日志文件: {str(e)}")
            self.auto_save_var.set(False)  # 取消勾选
    
    def stop_auto_save(self):
        """停止自动保存日志"""
        if self.log_file:
            try:
                # 写入日志文件尾部信息
                footer = f"\n" + "=" * 50 + "\n"
                footer += f"日志结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                footer += f"总日志条数: {self.get_log_line_count()}\n"
                
                self.log_file.write(footer)
                self.log_file.close()
                
                self.log_message(f"自动保存日志已停止，日志文件: {self.log_filename}")
                
            except Exception as e:
                self.log_message(f"关闭日志文件时出错: {str(e)}")
            
            self.log_file = None
            self.log_filename = None
    
    def get_log_line_count(self):
        """获取日志行数"""
        try:
            content = self.log_text.get(1.0, tk.END)
            return len(content.split('\n')) - 1  # 减去最后一行空行
        except:
            return 0
    
    def log_message(self, message, color="black"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # 构建完整的日志消息
        log_entry = f"[{timestamp}] {message}\n"
        
        # 插入到界面文本框
        self.log_text.insert(tk.END, log_entry)
        
        # 检查是否包含"心跳状态"并设置颜色
        if "心跳状态" in message:
            # 获取刚插入的行的起始和结束位置
            last_line_start = self.log_text.index("end-2l linestart")
            last_line_end = self.log_text.index("end-1c")
            
            # 为整行设置红色标签
            self.log_text.tag_add("heartbeat_red", last_line_start, last_line_end)
        
        self.log_text.see(tk.END)
        
        # 如果开启了自动保存，同时写入文件
        if self.auto_save_var.get() and self.log_file:
            try:
                self.log_file.write(log_entry)
                self.log_file.flush()  # 立即写入文件，确保数据不丢失
            except Exception as e:
                # 如果写入文件失败，在界面上显示错误
                error_msg = f"[{timestamp}] 写入日志文件失败: {str(e)}\n"
                self.log_text.insert(tk.END, error_msg)
                self.log_text.see(tk.END)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        
        # 如果开启了自动保存，在日志文件中记录清空操作
        if self.auto_save_var.get() and self.log_file:
            try:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                clear_msg = f"[{timestamp}] 用户手动清空日志\n"
                self.log_file.write(clear_msg)
                self.log_file.flush()
            except Exception as e:
                pass  # 忽略清空时的文件写入错误
    
    def save_log(self):
        """手动保存日志到文件（保留原有功能作为备用）"""
        try:
            filename = f"can_log_manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get(1.0, tk.END))
            messagebox.showinfo("保存成功", f"日志已保存到: {filename}")
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存日志: {str(e)}")
    
    def __del__(self):
        """析构函数，确保程序退出时关闭日志文件"""
        if hasattr(self, 'log_file') and self.log_file:
            try:
                self.log_file.close()
            except:
                pass
        
    def connect_can(self):
        """连接CAN总线"""
        try:
            device_type = VCI_USBCAN2
            device_index = int(self.device_index_var.get())
            can_index = int(self.can_index_var.get())
            baudrate = int(self.baudrate_var.get())
            
            self.log_message(f"正在连接CAN设备...")
            self.log_message(f"设备类型: VCI_USBCAN2, 设备索引: {device_index}, CAN通道: {can_index}, 波特率: {baudrate}")
            
            # 创建CAN总线对象
            self.can_bus = CANalystCANBus(device_type, device_index, can_index)
            self.can_bus.connect(baudrate)
            
            self.is_connected = True
            
            self.connect_btn.config(state="disabled")
            self.disconnect_btn.config(state="normal")
            self.start_btn.config(state="normal")
            self.receive_check.config(state="normal")  # 确保复选框可用
            
            self.status_var.set(self.lang_manager.get_text('connected'))
            self.heartbeat_status_var.set(self.lang_manager.get_text('waiting'))  # 初始状态为等待
            self.heartbeat_count = 0  # 重置心跳计数
            
            # 重置表格中的心跳状态
            current_time = datetime.now().strftime("%H:%M:%S")
            self.update_table_item('0x351', self.lang_manager.get_text('heartbeat_status_param'), '0', '', self.lang_manager.get_text('stopped'), current_time)
            
            # 重置发送数据表格状态
            self.update_send_data_table(0x305, self.lang_manager.get_text('stopped_sending'), 0, current_time)
            self.update_send_data_table(0x307, self.lang_manager.get_text('stopped_sending'), 0, current_time)
            
            self.log_message(self.lang_manager.get_text('can_device_connected'))
            
        except Exception as e:
            messagebox.showerror("连接错误", f"无法连接CAN设备: {str(e)}")
            self.log_message(f"连接失败: {str(e)}")
    
    def _initial_receive_test(self):
        """连接后立即测试接收"""
        try:
            # 测试接收3秒
            start_time = time.time()
            received_count = 0
            
            while time.time() - start_time < 3:
                messages = self.can_bus.receive(timeout=100)
                if messages:
                    received_count += len(messages)
                    for msg in messages:
                        self.log_message(f"初始测试接收: ID=0x{msg['id']:03X}, 数据: {bytes(msg['data']).hex()}")
                time.sleep(0.1)
            
            if received_count > 0:
                self.log_message(f"初始测试成功，接收到 {received_count} 个报文")
            else:
                self.log_message("初始测试未接收到报文，请检查通道设置")
                
        except Exception as e:
            self.log_message(f"初始测试错误: {str(e)}")
            
    def disconnect_can(self):
        """断开CAN连接"""
        if self.can_bus:
            self.stop_sending()
            self.stop_receiving()
            self.can_bus.disconnect()
            self.can_bus = None
            
        self.is_connected = False
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.receive_check.config(state="disabled")  # 禁用接收复选框
        self.receive_var.set(False)  # 取消勾选
        
        self.status_var.set(self.lang_manager.get_text('not_connected'))
        self.heartbeat_count = 0  # 重置心跳计数
        
        # 重置表格中的心跳状态
        current_time = datetime.now().strftime("%H:%M:%S")
        self.update_table_item('0x351', self.lang_manager.get_text('heartbeat_status_param'), '0', '', self.lang_manager.get_text('stopped'), current_time)
        
        # 重置发送数据表格状态
        self.update_send_data_table(0x305, self.lang_manager.get_text('stopped_sending'), 0, current_time)
        self.update_send_data_table(0x307, self.lang_manager.get_text('stopped_sending'), 0, current_time)
        
        self.log_message("CAN设备已断开")
    
    def start_sending(self):
        """开始发送CAN报文"""
        if not self.is_connected:
            return
            
        self.is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        
        # 重置发送计数
        self.sent_305_count = 0
        self.sent_307_count = 0
        
        # 更新发送数据表格初始状态 - 改为"正在发送"
        current_time = datetime.now().strftime("%H:%M:%S")
        self.update_send_data_table(0x305, self.lang_manager.get_text('sending'), 0, current_time)
        self.update_send_data_table(0x307, self.lang_manager.get_text('sending'), 0, current_time)
        
        # 启动发送线程
        self.send_thread = threading.Thread(target=self.send_messages, daemon=True)
        self.send_thread.start()
        
        self.log_message("开始发送CAN报文")
    
    def stop_sending(self):
        """停止发送CAN报文"""
        self.is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        
        # 更新发送数据表格停止状态 - 改为"已停止"
        current_time = datetime.now().strftime("%H:%M:%S")
        self.update_send_data_table(0x305, self.lang_manager.get_text('stopped_status'), self.sent_305_count, current_time)
        self.update_send_data_table(0x307, self.lang_manager.get_text('stopped_status'), self.sent_307_count, current_time)
        
        self.log_message("停止发送CAN报文")
        
    def send_messages(self):
        """发送CAN报文的线程函数"""
        while self.is_running and self.is_connected:
            try:
                # 发送ID为0x305的报文
                msg_305_data = self.create_305_message()
                self.can_bus.send(0x305, msg_305_data)
                self.sent_count += 1
                self.sent_305_count += 1
                self.sent_count_var.set(str(self.sent_count))
                
                # 更新发送数据表格 - 保持"正在发送"状态
                current_time = datetime.now().strftime("%H:%M:%S")
                self.update_send_data_table(0x305, self.lang_manager.get_text('sending'), self.sent_305_count, current_time)
                
                self.log_message(f"发送: ID=0x305, 数据: {msg_305_data.hex()}")
                
                # 发送ID为0x307的报文
                msg_307_data = self.create_307_message()
                self.can_bus.send(0x307, msg_307_data)
                self.sent_count += 1
                self.sent_307_count += 1
                self.sent_count_var.set(str(self.sent_count))
                
                # 更新发送数据表格 - 保持"正在发送"状态
                current_time = datetime.now().strftime("%H:%M:%S")
                self.update_send_data_table(0x307, self.lang_manager.get_text('sending'), self.sent_307_count, current_time)
                
                self.log_message(f"发送: ID=0x307, 数据: {msg_307_data.hex()}")
                
                time.sleep(1)  # 每秒发送一次
                
            except Exception as e:
                self.log_message(f"发送错误: {str(e)}")
                break
                
    def create_305_message(self):
        """创建0x305报文数据 - Keepalive from inverter to BMS"""
        # 根据协议文档：8个字节都是0
        data = bytearray(8)
        # 所有字节都是0，不需要额外设置，bytearray默认就是0
        return data
        
    def create_307_message(self):
        """创建0x307报文数据 - Inverter identification from inverter to BMS"""
        # 根据协议文档：0x12 0x34 0x56 0x78 V I C 0x00
        data = bytearray(8)
        data[0] = 0x12  # Byte 0
        data[1] = 0x34  # Byte 1
        data[2] = 0x56  # Byte 2
        data[3] = 0x78  # Byte 3
        data[4] = ord('V')  # Byte 4: ASCII 'V'
        data[5] = ord('I')  # Byte 5: ASCII 'I'
        data[6] = ord('C')  # Byte 6: ASCII 'C'
        data[7] = 0x00  # Byte 7: reserved for future use
        return data
                
    def parse_heartbeat_message(self, msg):
        """解析0x351报文 - 充放电信息（用作心跳标志）"""
        try:
            data = msg['data']
            parsed_data = parse_351_message(data)
            
            if parsed_data:
                # 更新表格
                self.update_table_data(0x351, parsed_data)
                
                self.log_message(f"充放电信息 - 充电电压限制: {parsed_data['charge_voltage_limit']:.1f}V, 最大充电电流: {parsed_data['max_charge_current']:.1f}A, 最大放电电流: {parsed_data['max_discharge_current']:.1f}A, 放电电压: {parsed_data['discharge_voltage']:.1f}V")
            else:
                self.log_message(f"0x351报文数据长度不足: {len(data)} 字节")
                
        except Exception as e:
            self.log_message(f"解析0x351报文错误: {str(e)}")
    
    def parse_bms_status_message(self, msg):
        """解析BMS状态报文 (0x355)"""
        try:
            data = msg['data']
            parsed_data = parse_355_message(data)
            
            if parsed_data:
                # 更新表格
                self.update_table_data(0x355, parsed_data)
                
                self.log_message(f"BMS状态 - SOC: {parsed_data['soc_value']}%, SOH: {parsed_data['soh_value']}%, 高精度SOC: {parsed_data['high_res_soc']:.2f}%")
            else:
                self.log_message(f"0x355报文数据长度不足: {len(data)} 字节")
                
        except Exception as e:
            self.log_message(f"解析BMS状态报文错误: {str(e)}")
    
    def parse_battery_info_message(self, msg):
        """解析电池信息报文 (0x356)"""
        try:
            data = msg['data']
            parsed_data = parse_356_message(data)
            
            if parsed_data:
                # 更新表格
                self.update_table_data(0x356, parsed_data)
                
                self.log_message(f"电池信息 - 电压: {parsed_data['battery_voltage']:.2f}V, 电流: {parsed_data['battery_current']:.1f}A, 温度: {parsed_data['battery_temperature']:.1f}°C")
            else:
                self.log_message(f"0x356报文数据长度不足: {len(data)} 字节")
                
        except Exception as e:
            self.log_message(f"解析电池信息报文错误: {str(e)}")
    
    def parse_error_message(self, msg):
        """解析错误报文 (0x35A)"""
        try:
            data = msg['data']
            parsed_data = parse_35A_message(data)
            
            if parsed_data:
                # 更新表格
                self.update_table_data(0x35A, parsed_data)
                
                # 记录警告信息
                warnings = parsed_data['warnings']
                active_warnings = [name for name, active in warnings.items() if active]
                if active_warnings:
                    self.log_message(f"检测到警告: {', '.join(active_warnings)}")
                else:
                    self.log_message("无警告信息")
            else:
                self.log_message(f"0x35A报文数据长度不足: {len(data)} 字节")
                
        except Exception as e:
            self.log_message(f"解析错误报文错误: {str(e)}")
    
    def monitor_heartbeat(self):
        """监控心跳的线程函数"""
        self.log_message("心跳监控线程已启动")
        while self.is_receiving and self.is_connected:
            try:
                # 接收CAN报文
                messages = self.can_bus.receive(timeout=50)
                
                if messages:
                    self.log_message(f"接收到 {len(messages)} 个报文")
                    for msg in messages:
                        self.received_count += 1
                        self.received_count_var.set(str(self.received_count))
                        self.process_received_message(msg)
                        
                        # 检查心跳报文（0x351作为心跳标志）
                        if msg['id'] == 0x351:
                            self.last_heartbeat_time = time.time()
                            self.heartbeat_count += 1  # 增加心跳计数
                            self.heartbeat_status_var.set(self.lang_manager.get_text('normal'))
                            
                            # 更新表格中的心跳状态
                            current_time = datetime.now().strftime("%H:%M:%S")
                            self.update_table_item('0x351', self.lang_manager.get_text('heartbeat_status_param'), str(self.heartbeat_count), '', self.lang_manager.get_text('normal'), current_time)
                            
                            self.log_message(f"收到心跳标志: ID=0x351, 数据: {bytes(msg['data']).hex()}")
                            
            except Exception as e:
                self.log_message(f"接收线程错误: {str(e)}")
                
            # 检查心跳超时（3秒未收到0x351）
            if self.last_heartbeat_time and (time.time() - self.last_heartbeat_time) > 3:
                self.root.after(0, self.handle_heartbeat_timeout)
    
    def process_received_message(self, msg):
        """处理接收到的CAN报文"""
        msg_id = msg['id']
        
        if msg_id in [0x351, 0x355, 0x356, 0x35A]:
            self.log_message(f"解析报文: ID=0x{msg_id:03X}, 数据: {bytes(msg['data']).hex()}")
            
            # 根据协议解析具体内容
            if msg_id == 0x351:
                self.parse_heartbeat_message(msg)
            elif msg_id == 0x355:
                self.parse_bms_status_message(msg)
            elif msg_id == 0x356:
                self.parse_battery_info_message(msg)
            elif msg_id == 0x35A:
                self.parse_error_message(msg)
                
    def handle_heartbeat_timeout(self):
        """处理心跳超时"""
        self.heartbeat_status_var.set(self.lang_manager.get_text('stopped'))
        
        # 更新表格中的心跳状态
        current_time = datetime.now().strftime("%H:%M:%S")
        self.update_table_item('0x351', self.lang_manager.get_text('heartbeat_status_param'), str(self.heartbeat_count), '', self.lang_manager.get_text('stopped'), current_time)
        
        messagebox.showwarning("心跳超时", self.lang_manager.get_text('heartbeat_timeout'))
        self.log_message(self.lang_manager.get_text('warning') + ": " + self.lang_manager.get_text('heartbeat_timeout'))
        # 注意：这里不自动断开连接，只是提示心跳停止

    def test_receive(self):
        """手动测试接收功能"""
        if not self.is_connected:
            messagebox.showwarning("警告", self.lang_manager.get_text('please_connect_first'))
            return
            
        self.log_message("开始测试接收功能...")
        
        # 在单独的线程中测试接收
        test_thread = threading.Thread(target=self._test_receive_thread, daemon=True)
        test_thread.start()
    
    def _test_receive_thread(self):
        """测试接收线程"""
        try:
            # 测试接收5秒
            start_time = time.time()
            while time.time() - start_time < 5:
                messages = self.can_bus.receive(timeout=100)
                if messages:
                    for msg in messages:
                        self.log_message(f"测试接收: ID=0x{msg['id']:03X}, 数据: {bytes(msg['data']).hex()}")
                time.sleep(0.1)
            
            self.log_message("接收测试完成")
            
        except Exception as e:
            self.log_message(f"接收测试错误: {str(e)}")

    def diagnose_connection(self):
        """诊断连接问题"""
        if not self.is_connected:
            self.log_message("设备未连接，无法诊断")
            return
            
        self.log_message("开始连接诊断...")
        
        # 检查设备状态
        try:
            # 这里可以添加更多的诊断代码
            self.log_message("设备连接正常")
            self.log_message("建议检查：")
            self.log_message("1. CAN总线连接是否正确")
            self.log_message("2. 波特率是否匹配")
            self.log_message("3. 目标设备是否发送数据")
            self.log_message("4. CAN通道选择是否正确")
            
        except Exception as e:
            self.log_message(f"诊断错误: {str(e)}")

    def switch_channel(self):
        """切换CAN通道"""
        if not self.is_connected:
            messagebox.showwarning("警告", self.lang_manager.get_text('please_connect_first'))
            return
            
        current_channel = int(self.can_index_var.get())
        new_channel = 1 if current_channel == 0 else 0
        
        self.log_message(f"切换CAN通道: {current_channel} -> {new_channel}")
        
        # 断开当前连接
        self.disconnect_can()
        
        # 更新通道设置
        self.can_index_var.set(str(new_channel))
        
        # 重新连接
        self.connect_can()

    def force_receive_test(self):
        """强制接收测试"""
        if not self.is_connected:
            messagebox.showwarning("警告", self.lang_manager.get_text('please_connect_first'))
            return
            
        self.log_message("开始强制接收测试...")
        
        # 在单独的线程中测试接收
        test_thread = threading.Thread(target=self._force_receive_thread, daemon=True)
        test_thread.start()
    
    def _force_receive_thread(self):
        """强制接收测试线程"""
        try:
            # 测试接收10秒
            start_time = time.time()
            total_received = 0
            
            while time.time() - start_time < 10:
                messages = self.can_bus.receive(timeout=50)
                if messages:
                    total_received += len(messages)
                    for msg in messages:
                        self.log_message(f"强制测试接收: ID=0x{msg['id']:03X}, 数据: {bytes(msg['data']).hex()}")
                time.sleep(0.05)  # 更频繁的检查
            
            self.log_message(f"强制接收测试完成，总共接收: {total_received} 个报文")
            
            if total_received == 0:
                self.log_message("未接收到任何报文，建议：")
                self.log_message("1. 检查CAN通道设置（尝试切换通道）")
                self.log_message("2. 确认波特率设置正确")
                self.log_message("3. 检查CAN总线连接")
            
        except Exception as e:
            self.log_message(f"强制接收测试错误: {str(e)}")

    def toggle_receive(self):
        """切换接收状态"""
        if self.receive_var.get():
            self.start_receiving()
        else:
            self.stop_receiving()

    def start_receiving(self):
        """启动接收CAN报文的线程"""
        if not self.is_connected:
            self.log_message(self.lang_manager.get_text('please_connect_first'), color="orange")
            self.receive_check.config(state="disabled")
            return
        
        if self.is_receiving:
            self.log_message("接收线程已在运行。", color="orange")
            return
        
        self.is_receiving = True
        
        # 重置心跳状态
        self.heartbeat_status_var.set(self.lang_manager.get_text('waiting'))
        self.heartbeat_count = 0
        self.last_heartbeat_time = None
        
        # 重置表格中的心跳状态
        current_time = datetime.now().strftime("%H:%M:%S")
        self.update_table_item('0x351', self.lang_manager.get_text('heartbeat_status_param'), '0', '', self.lang_manager.get_text('waiting'), current_time)
        
        self.receive_thread = threading.Thread(target=self.monitor_heartbeat, daemon=True)
        self.receive_thread.start()
        self.log_message(self.lang_manager.get_text('已开启接收CAN报文'), color="green")
    
    def stop_receiving(self):
        """停止接收CAN报文的线程"""
        if not self.is_receiving:
            self.log_message("接收线程未运行。", color="orange")
            return
        
        self.is_receiving = False
        # Wait for the thread to finish (optional, but good practice for clean shutdown)
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1) # Give it a second to finish
        
        # 重置心跳状态
        self.heartbeat_status_var.set(self.lang_manager.get_text('stopped'))
        self.heartbeat_count = 0
        self.last_heartbeat_time = None
        
        # 重置表格中的心跳状态
        current_time = datetime.now().strftime("%H:%M:%S")
        self.update_table_item('0x351', self.lang_manager.get_text('heartbeat_status_param'), '0', '', self.lang_manager.get_text('stopped'), current_time)
        
        self.log_message(self.lang_manager.get_text('停止接收CAN报文'), color="green")

    def monitor_receive(self):
        """接收报文的独立线程函数"""
        self.log_message("接收报文线程已启动")
        while self.is_running and self.is_connected and self.receive_var.get():
            try:
                messages = self.can_bus.receive(timeout=50) # 更短的超时时间
                if messages:
                    self.log_message(f"接收到 {len(messages)} 个报文")
                    for msg in messages:
                        self.received_count += 1
                        self.received_count_var.set(str(self.received_count))
                        self.process_received_message(msg)
                        
                        # 检查心跳报文
                        if msg['id'] == 0x351:
                            self.last_heartbeat_time = time.time()
                            self.heartbeat_status_var.set(self.lang_manager.get_text('normal'))
                            self.log_message(f"收到心跳: ID=0x351, 数据: {bytes(msg['data']).hex()}")
                else:
                    # 减少调试信息频率
                    if time.time() % 10 < 0.1:  # 每10秒显示一次
                        self.log_message("正在监听CAN报文...")
                            
            except Exception as e:
                self.log_message(f"接收线程错误: {str(e)}")
                # 检查心跳超时
                if self.last_heartbeat_time and (time.time() - self.last_heartbeat_time) > 3:
                    self.root.after(0, self.handle_heartbeat_timeout)

    def create_data_table(self, parent):
        """创建数据表格"""
        # 创建表格框架
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="both", expand=True)
        
        # 创建Treeview表格 - 调整高度
        columns = (self.lang_manager.get_text('can_id'), self.lang_manager.get_text('parameter'), self.lang_manager.get_text('value'), self.lang_manager.get_text('unit'), self.lang_manager.get_text('status'), self.lang_manager.get_text('refresh_time'))
        self.data_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)  # 增加高度
        
        # 设置列标题
        for col in columns:
            self.data_tree.heading(col, text=col)
            # 调整列宽
            if col == self.lang_manager.get_text('can_id'):
                self.data_tree.column(col, width=80, anchor='center')
            elif col == self.lang_manager.get_text('parameter'):
                self.data_tree.column(col, width=150, anchor='w')
            elif col == self.lang_manager.get_text('value'):
                self.data_tree.column(col, width=100, anchor='center')
            elif col == self.lang_manager.get_text('unit'):
                self.data_tree.column(col, width=60, anchor='center')
            elif col == self.lang_manager.get_text('status'):
                self.data_tree.column(col, width=80, anchor='center')
            elif col == self.lang_manager.get_text('refresh_time'):
                self.data_tree.column(col, width=120, anchor='center')
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.data_tree.yview)
        self.data_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.data_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 初始化表格数据
        self.initialize_table_data()
    
    def initialize_table_data(self):
        """初始化表格数据"""
        # 清空现有数据
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)
        
        # 添加0x351数据项（包括心跳状态）
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('heartbeat_status'), '0', '', self.lang_manager.get_text('stopped'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('charge_voltage_limit'), '--', self.lang_manager.get_text('unit'), self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('max_charge_current'), '--', self.lang_manager.get_text('unit'), self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('max_discharge_current'), '--', self.lang_manager.get_text('unit'), self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('discharge_voltage'), '--', self.lang_manager.get_text('unit'), self.lang_manager.get_text('waiting'), '--'))
        
        # 添加0x355数据项
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('soc_value'), '--', self.lang_manager.get_text('unit'), self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('soh_value'), '--', self.lang_manager.get_text('unit'), self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('high_precision_soc'), '--', self.lang_manager.get_text('unit'), self.lang_manager.get_text('waiting'), '--'))
        
        # 添加0x356数据项
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_voltage'), '--', self.lang_manager.get_text('unit'), self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_current'), '--', self.lang_manager.get_text('unit'), self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_temperature'), '--', self.lang_manager.get_text('unit'), self.lang_manager.get_text('waiting'), '--'))
        
        # 添加0x35A数据项（包含Alarm和Warning信息）
        # Alarm信息
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_high_voltage_alarm'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_low_voltage_alarm'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_high_temp_alarm'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_low_temp_alarm'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_high_current_alarm'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('bms_internal_alarm'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('cell_imbalance_alarm'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        
        # Warning信息
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_high_voltage_warning'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_low_voltage_warning'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_high_temp_warning'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_low_temp_warning'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_high_current_warning'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('bms_internal_warning'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('cell_imbalance_warning'), '--', '', self.lang_manager.get_text('waiting'), '--'))
        self.data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('system_status'), '--', '', self.lang_manager.get_text('waiting'), '--'))
    
    def update_table_data(self, can_id, parsed_data):
        """更新表格数据"""
        current_time = datetime.now().strftime("%H:%M:%S")
        
        if can_id == 0x351:
            # 更新0x351数据
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('charge_voltage_limit'), f"{parsed_data.get('charge_voltage_limit', 0):.1f}", self.lang_manager.get_text('unit'), self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('max_charge_current'), f"{parsed_data.get('max_charge_current', 0):.1f}", self.lang_manager.get_text('unit'), self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('max_discharge_current'), f"{parsed_data.get('max_discharge_current', 0):.1f}", self.lang_manager.get_text('unit'), self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('discharge_voltage'), f"{parsed_data.get('discharge_voltage', 0):.1f}", self.lang_manager.get_text('unit'), self.lang_manager.get_text('normal'), current_time)
            
        elif can_id == 0x355:
            # 更新0x355数据
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('soc_value'), f"{parsed_data.get('soc_value', 0)}", self.lang_manager.get_text('unit'), self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('soh_value'), f"{parsed_data.get('soh_value', 0)}", self.lang_manager.get_text('unit'), self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('high_precision_soc'), f"{parsed_data.get('high_res_soc', 0):.2f}", self.lang_manager.get_text('unit'), self.lang_manager.get_text('normal'), current_time)
            
        elif can_id == 0x356:
            # 更新0x356数据
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_voltage'), f"{parsed_data.get('battery_voltage', 0):.2f}", self.lang_manager.get_text('unit'), self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_current'), f"{parsed_data.get('battery_current', 0):.1f}", self.lang_manager.get_text('unit'), self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_temperature'), f"{parsed_data.get('battery_temperature', 0):.1f}", self.lang_manager.get_text('unit'), self.lang_manager.get_text('normal'), current_time)
            
        elif can_id == 0x35A:
            # 更新0x35A报警和警告状态
            alarms = parsed_data.get('alarms', {})
            warnings = parsed_data.get('warnings', {})
            
            # 更新Alarm信息
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_high_voltage_alarm'), self.lang_manager.get_text('yes') if alarms.get('battery_high_voltage_alarm', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_low_voltage_alarm'), self.lang_manager.get_text('yes') if alarms.get('battery_low_voltage_alarm', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_high_temp_alarm'), self.lang_manager.get_text('yes') if alarms.get('battery_high_temp_alarm', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_low_temp_alarm'), self.lang_manager.get_text('yes') if alarms.get('battery_low_temp_alarm', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_high_current_alarm'), self.lang_manager.get_text('yes') if alarms.get('battery_high_current_alarm', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('bms_internal_alarm'), self.lang_manager.get_text('yes') if alarms.get('bms_internal_alarm', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('cell_imbalance_alarm'), self.lang_manager.get_text('yes') if alarms.get('cell_imbalance_alarm', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            
            # 更新Warning信息
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_high_voltage_warning'), self.lang_manager.get_text('yes') if warnings.get('battery_high_voltage', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_low_voltage_warning'), self.lang_manager.get_text('yes') if warnings.get('battery_low_voltage', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_high_temp_warning'), self.lang_manager.get_text('yes') if warnings.get('battery_high_temp', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_low_temp_warning'), self.lang_manager.get_text('yes') if warnings.get('battery_low_temp', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('battery_high_current_warning'), self.lang_manager.get_text('yes') if warnings.get('battery_high_current', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('bms_internal_warning'), self.lang_manager.get_text('yes') if warnings.get('bms_internal', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('cell_imbalance_warning'), self.lang_manager.get_text('yes') if warnings.get('cell_imbalance', False) else self.lang_manager.get_text('no'), '', self.lang_manager.get_text('normal'), current_time)
            self.update_table_item(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('system_status'), self.lang_manager.get_text('online') if warnings.get('system_online', False) else self.lang_manager.get_text('offline'), '', self.lang_manager.get_text('normal'), current_time)
    
    def update_table_item(self, can_id, parameter, value, unit, status, update_time):
        """更新表格中的单个项目"""
        for item in self.data_tree.get_children():
            values = self.data_tree.item(item)['values']
            if values[0] == can_id and values[1] == parameter:
                self.data_tree.item(item, values=(can_id, parameter, value, unit, status, update_time))
                break

    def create_send_data_table(self, parent):
        """创建发送数据表格"""
        # 创建表格框架
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="x")
        
        # 创建Treeview表格 - 调整高度
        columns = (self.lang_manager.get_text('can_id'), self.lang_manager.get_text('send_status'), self.lang_manager.get_text('send_count'), self.lang_manager.get_text('status'), self.lang_manager.get_text('send_time'))
        self.send_data_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=3)  # 减少高度
        
        # 设置列标题
        for col in columns:
            self.send_data_tree.heading(col, text=col)
            # 调整列宽
            if col == self.lang_manager.get_text('can_id'):
                self.send_data_tree.column(col, width=80, anchor='center')
            elif col == self.lang_manager.get_text('send_status'):
                self.send_data_tree.column(col, width=150, anchor='w')
            elif col == self.lang_manager.get_text('send_count'):
                self.send_data_tree.column(col, width=100, anchor='center')
            elif col == self.lang_manager.get_text('status'):
                self.send_data_tree.column(col, width=80, anchor='center')
            elif col == self.lang_manager.get_text('send_time'):
                self.send_data_tree.column(col, width=120, anchor='center')
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.send_data_tree.yview)
        self.send_data_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.send_data_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 初始化发送数据表格
        self.initialize_send_data_table()
    
    def initialize_send_data_table(self):
        """初始化发送数据表格"""
        # 清空现有数据
        for item in self.send_data_tree.get_children():
            self.send_data_tree.delete(item)
        
        # 添加0x305数据项 - 初始状态为"停止发送"
        self.send_data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('stopped_sending'), '0', self.lang_manager.get_text('stopped'), '--'))
        
        # 添加0x307数据项 - 初始状态为"停止发送"
        self.send_data_tree.insert('', 'end', values=(self.lang_manager.get_text('can_id'), self.lang_manager.get_text('stopped_sending'), '0', self.lang_manager.get_text('stopped'), '--'))
    
    def update_send_data_table(self, can_id, status, count, send_time):
        """更新发送数据表格"""
        if can_id == 0x305:
            self.update_send_table_item(self.lang_manager.get_text('can_id'), status, str(count), self.lang_manager.get_text('normal'), send_time)
        elif can_id == 0x307:
            self.update_send_table_item(self.lang_manager.get_text('can_id'), status, str(count), self.lang_manager.get_text('normal'), send_time)
    
    def update_send_table_item(self, can_id, send_status, count, status, send_time):
        """更新发送表格中的单个项目"""
        for item in self.send_data_tree.get_children():
            values = self.send_data_tree.item(item)['values']
            if values[0] == can_id:
                self.send_data_tree.item(item, values=(can_id, send_status, count, status, send_time))
                break

    def start_auto_save_on_startup(self):
        """程序启动时自动开始保存日志 - 现在不自动开始"""
        # 移除自动开始保存的逻辑
        pass

    def switch_language(self, language):
        """切换语言"""
        if self.lang_manager.switch_language(language):
            # 更新窗口标题
            self.root.title(self.lang_manager.get_text('window_title'))
            
            # 只更新界面文本，不重新创建整个界面
            self.update_ui_language()
    
    def update_ui_language(self):
        """更新界面语言文本"""
        # 保存当前状态
        current_state = self.save_current_state()
        
        # 更新连接设置框架
        self.update_connection_frame_text()
        
        # 更新控制框架
        self.update_control_frame_text()
        
        # 更新统计信息框架
        self.update_statistics_frame_text()
        
        # 更新发送数据框架
        self.update_send_data_frame_text()
        
        # 更新实时数据框架
        self.update_real_time_data_frame_text()
        
        # 更新日志框架
        self.update_log_frame_text()
        
        # 恢复状态
        self.restore_state(current_state)
    
    def update_connection_frame_text(self):
        """更新连接设置框架文本"""
        # 更新框架标题
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.LabelFrame):
                        if "连接设置" in child.cget("text") or "Connection Settings" in child.cget("text"):
                            child.configure(text=self.lang_manager.get_text('connection_settings'))
                            break
        
        # 更新按钮文本
        if hasattr(self, 'connect_btn'):
            self.connect_btn.configure(text=self.lang_manager.get_text('connect'))
        if hasattr(self, 'disconnect_btn'):
            self.disconnect_btn.configure(text=self.lang_manager.get_text('disconnect'))
    
    def update_control_frame_text(self):
        """更新控制框架文本"""
        # 更新框架标题
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.LabelFrame):
                        if "控制" in child.cget("text") or "Control" in child.cget("text"):
                            child.configure(text=self.lang_manager.get_text('control'))
                            break
        
        # 更新按钮文本
        if hasattr(self, 'start_btn'):
            self.start_btn.configure(text=self.lang_manager.get_text('start_sending'))
        if hasattr(self, 'stop_btn'):
            self.stop_btn.configure(text=self.lang_manager.get_text('stop_sending'))
        if hasattr(self, 'receive_check'):
            self.receive_check.configure(text=self.lang_manager.get_text('enable_receiving'))
    
    def update_statistics_frame_text(self):
        """更新统计信息框架文本"""
        # 更新框架标题
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.LabelFrame):
                        if "统计信息" in child.cget("text") or "Statistics" in child.cget("text"):
                            child.configure(text=self.lang_manager.get_text('statistics'))
                            break
    
    def update_send_data_frame_text(self):
        """更新发送数据框架文本"""
        # 更新框架标题
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.LabelFrame):
                        if "发送数据" in child.cget("text") or "Send Data" in child.cget("text"):
                            child.configure(text=self.lang_manager.get_text('send_data'))
                            break
    
    def update_real_time_data_frame_text(self):
        """更新实时数据框架文本"""
        # 更新框架标题
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.LabelFrame):
                        if "实时数据" in child.cget("text") or "Real-time Data" in child.cget("text"):
                            child.configure(text=self.lang_manager.get_text('real_time_data'))
                            break
    
    def update_log_frame_text(self):
        """更新日志框架文本"""
        # 更新框架标题
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.LabelFrame):
                        if "通信日志" in child.cget("text") or "Communication Log" in child.cget("text"):
                            child.configure(text=self.lang_manager.get_text('communication_log'))
                            break
        
        # 更新按钮文本
        if hasattr(self, 'auto_save_check'):
            self.auto_save_check.configure(text=self.lang_manager.get_text('auto_save_log'))
    
    def recreate_widgets(self):
        """重新创建界面（语言切换时调用）"""
        # 保存当前状态
        current_state = self.save_current_state()
        
        # 保存日志文件状态
        log_file_state = {
            'log_file': self.log_file,
            'log_filename': self.log_filename,
            'auto_save_enabled': self.auto_save_var.get() if hasattr(self, 'auto_save_var') else False
        }
        
        # 清空现有界面
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 重新创建界面
        self.create_widgets()
        
        # 恢复状态
        self.restore_state(current_state)
        
        # 恢复日志文件状态
        if log_file_state['auto_save_enabled'] and not hasattr(self, '_auto_save_initialized'):
            self.auto_save_var.set(True)
            # 不重新创建日志文件，继续使用现有的
            self.log_file = log_file_state['log_file']
            self.log_filename = log_file_state['log_filename']
    
    def save_current_state(self):
        """保存当前状态"""
        return {
            'is_connected': self.is_connected,
            'is_running': self.is_running,
            'is_receiving': self.is_receiving,
            'auto_save_enabled': self.auto_save_var.get() if hasattr(self, 'auto_save_var') else False,
            'receive_enabled': self.receive_var.get() if hasattr(self, 'receive_var') else False,
            'device_settings': {
                'device_type': self.device_type_var.get() if hasattr(self, 'device_type_var') else 'VCI_USBCAN2',
                'device_index': self.device_index_var.get() if hasattr(self, 'device_index_var') else '0',
                'can_index': self.can_index_var.get() if hasattr(self, 'can_index_var') else '0',
                'baudrate': self.baudrate_var.get() if hasattr(self, 'baudrate_var') else '500000'
            }
        }
    
    def restore_state(self, state):
        """恢复状态"""
        # 恢复设备设置
        if 'device_settings' in state:
            settings = state['device_settings']
            if hasattr(self, 'device_type_var'):
                self.device_type_var.set(settings.get('device_type', 'VCI_USBCAN2'))
            if hasattr(self, 'device_index_var'):
                self.device_index_var.set(settings.get('device_index', '0'))
            if hasattr(self, 'can_index_var'):
                self.can_index_var.set(settings.get('can_index', '0'))
            if hasattr(self, 'baudrate_var'):
                self.baudrate_var.set(settings.get('baudrate', '500000'))
        
        # 恢复连接状态
        if state.get('is_connected', False):
            self.status_var.set(self.lang_manager.get_text('connected'))
            self.connect_btn.config(state="disabled")
            self.disconnect_btn.config(state="normal")
            self.start_btn.config(state="normal")
            self.receive_check.config(state="normal")
        else:
            self.status_var.set(self.lang_manager.get_text('not_connected'))
        
        # 恢复自动保存状态
        if state.get('auto_save_enabled', False) and hasattr(self, 'auto_save_var'):
            self.auto_save_var.set(True)
            self.start_auto_save()
        
        # 恢复接收状态
        if state.get('receive_enabled', False) and hasattr(self, 'receive_var'):
            self.receive_var.set(True)
            if state.get('is_connected', False):
                self.start_receiving()

def main():
    root = tk.Tk()
    app = CANHostComputer(root)
    
    # 设置窗口关闭事件处理
    def on_closing():
        if app.auto_save_var.get():
            app.stop_auto_save()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()