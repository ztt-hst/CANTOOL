import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import time
from datetime import datetime
import json
import struct
import ctypes
from ctypes import *

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
        self.root.title("CAN协议上位机 - 创芯科技CANalyst-II")
        self.root.geometry("1000x700")
        
        # CAN相关变量
        self.can_bus = None
        self.is_connected = False
        self.is_running = False
        self.last_heartbeat_time = None
        self.heartbeat_monitor_thread = None
        
        # 统计变量
        self.sent_count = 0
        self.received_count = 0
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 连接设置框架
        connection_frame = ttk.LabelFrame(main_frame, text="连接设置", padding="10")
        connection_frame.pack(fill="x", pady=5)
        
        # 第一行：设备设置
        row1 = ttk.Frame(connection_frame)
        row1.pack(fill="x", pady=2)
        
        ttk.Label(row1, text="设备类型:").pack(side="left", padx=5)
        self.device_type_var = tk.StringVar(value="VCI_USBCAN2")
        device_type_combo = ttk.Combobox(row1, textvariable=self.device_type_var, 
                                       values=["VCI_USBCAN2"], width=15, state="readonly")
        device_type_combo.pack(side="left", padx=5)
        
        ttk.Label(row1, text="设备索引:").pack(side="left", padx=5)
        self.device_index_var = tk.StringVar(value="0")
        device_index_combo = ttk.Combobox(row1, textvariable=self.device_index_var, 
                                        values=["0", "1"], width=5)
        device_index_combo.pack(side="left", padx=5)
        
        ttk.Label(row1, text="CAN通道:").pack(side="left", padx=5)
        self.can_index_var = tk.StringVar(value="0")
        can_index_combo = ttk.Combobox(row1, textvariable=self.can_index_var, 
                                      values=["0", "1"], width=5)
        can_index_combo.pack(side="left", padx=5)
        
        # 第二行：波特率设置
        row2 = ttk.Frame(connection_frame)
        row2.pack(fill="x", pady=2)
        
        ttk.Label(row2, text="波特率:").pack(side="left", padx=5)
        self.baudrate_var = tk.StringVar(value="500000")
        baudrate_combo = ttk.Combobox(row2, textvariable=self.baudrate_var,
                                     values=["250000", "500000"], width=10)
        baudrate_combo.pack(side="left", padx=5)
        
        # 连接按钮
        self.connect_btn = ttk.Button(row2, text="连接", command=self.connect_can)
        self.connect_btn.pack(side="left", padx=10)
        
        self.disconnect_btn = ttk.Button(row2, text="断开", command=self.disconnect_can, state="disabled")
        self.disconnect_btn.pack(side="left", padx=5)
        
        # 控制框架
        control_frame = ttk.LabelFrame(main_frame, text="控制", padding="10")
        control_frame.pack(fill="x", pady=5)
        
        # 控制按钮
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill="x")
        
        self.start_btn = ttk.Button(btn_frame, text="启动发送", command=self.start_sending, state="disabled")
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="停止发送", command=self.stop_sending, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        # 状态显示
        self.status_var = tk.StringVar(value="未连接")
        status_label = ttk.Label(btn_frame, textvariable=self.status_var)
        status_label.pack(side="right", padx=5)
        
        # 统计信息框架
        stats_frame = ttk.LabelFrame(main_frame, text="统计信息", padding="10")
        stats_frame.pack(fill="x", pady=5)
        
        stats_inner = ttk.Frame(stats_frame)
        stats_inner.pack(fill="x")
        
        # 发送统计
        ttk.Label(stats_inner, text="发送:").grid(row=0, column=0, sticky="w", padx=5)
        self.sent_count_var = tk.StringVar(value="0")
        ttk.Label(stats_inner, textvariable=self.sent_count_var).grid(row=0, column=1, padx=5)
        
        # 接收统计
        ttk.Label(stats_inner, text="接收:").grid(row=0, column=2, sticky="w", padx=5)
        self.received_count_var = tk.StringVar(value="0")
        ttk.Label(stats_inner, textvariable=self.received_count_var).grid(row=0, column=3, padx=5)
        
        # 心跳状态
        ttk.Label(stats_inner, text="心跳状态:").grid(row=0, column=4, sticky="w", padx=5)
        self.heartbeat_status_var = tk.StringVar(value="正常")
        ttk.Label(stats_inner, textvariable=self.heartbeat_status_var).grid(row=0, column=5, padx=5)
        
        # 日志框架
        log_frame = ttk.LabelFrame(main_frame, text="通信日志", padding="10")
        log_frame.pack(fill="both", expand=True, pady=5)
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_text.pack(fill="both", expand=True)
        
        # 日志控制按钮
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill="x", pady=5)
        
        clear_btn = ttk.Button(log_btn_frame, text="清空日志", command=self.clear_log)
        clear_btn.pack(side="left")
        
        save_btn = ttk.Button(log_btn_frame, text="保存日志", command=self.save_log)
        save_btn.pack(side="left", padx=5)
        
        # 在控制按钮区域添加测试按钮
        test_btn = ttk.Button(btn_frame, text="测试接收", command=self.test_receive)
        test_btn.pack(side="left", padx=5)
        
        # 在控制按钮区域添加诊断按钮
        diagnose_btn = ttk.Button(btn_frame, text="连接诊断", command=self.diagnose_connection)
        diagnose_btn.pack(side="left", padx=5)
        
        # 在控制按钮区域添加通道切换按钮
        switch_channel_btn = ttk.Button(btn_frame, text="切换通道", command=self.switch_channel)
        switch_channel_btn.pack(side="left", padx=5)
        
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        
    def save_log(self):
        """保存日志到文件"""
        try:
            filename = f"can_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get(1.0, tk.END))
            messagebox.showinfo("保存成功", f"日志已保存到: {filename}")
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存日志: {str(e)}")
        
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
            
            self.status_var.set("已连接")
            self.log_message("CAN设备连接成功")
            
            # 立即测试接收
            self.log_message("开始测试接收...")
            test_thread = threading.Thread(target=self._initial_receive_test, daemon=True)
            test_thread.start()
            
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
            self.can_bus.disconnect()
            self.can_bus = None
            
        self.is_connected = False
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        
        self.status_var.set("未连接")
        self.log_message("CAN设备已断开")
        
    def start_sending(self):
        """开始发送CAN报文"""
        if not self.is_connected:
            return
            
        self.is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        
        # 启动发送线程
        self.send_thread = threading.Thread(target=self.send_messages, daemon=True)
        self.send_thread.start()
        
        # 启动心跳监控线程
        self.heartbeat_monitor_thread = threading.Thread(target=self.monitor_heartbeat, daemon=True)
        self.heartbeat_monitor_thread.start()
        
        self.log_message("开始发送CAN报文")
        
    def stop_sending(self):
        """停止发送CAN报文"""
        self.is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.log_message("停止发送CAN报文")
        
    def send_messages(self):
        """发送CAN报文的线程函数"""
        while self.is_running and self.is_connected:
            try:
                # 发送ID为0x305的报文
                msg_305_data = self.create_305_message()
                self.can_bus.send(0x305, msg_305_data)
                self.sent_count += 1
                self.sent_count_var.set(str(self.sent_count))
                self.log_message(f"发送: ID=0x305, 数据: {msg_305_data.hex()}")
                
                # 发送ID为0x307的报文
                msg_307_data = self.create_307_message()
                self.can_bus.send(0x307, msg_307_data)
                self.sent_count += 1
                self.sent_count_var.set(str(self.sent_count))
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
                
    def monitor_heartbeat(self):
        """监控心跳的线程函数"""
        self.log_message("心跳监控线程已启动")
        while self.is_running and self.is_connected:
            try:
                # 接收CAN报文 - 减少超时时间
                messages = self.can_bus.receive(timeout=50)  # 从100ms改为50ms
                
                if messages:
                    self.log_message(f"接收到 {len(messages)} 个报文")
                    for msg in messages:
                        self.received_count += 1
                        self.received_count_var.set(str(self.received_count))
                        self.process_received_message(msg)
                        
                        # 检查心跳报文
                        if msg['id'] == 0x351:
                            self.last_heartbeat_time = time.time()
                            self.heartbeat_status_var.set("正常")
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
                
    def parse_heartbeat_message(self, msg):
        """解析心跳报文 (0x351)"""
        try:
            data = msg['data']
            status = data[0] if len(data) > 0 else 0
            self.log_message(f"心跳状态: {status}")
        except Exception as e:
            self.log_message(f"解析心跳报文错误: {str(e)}")
        
    def parse_bms_status_message(self, msg):
        """解析BMS状态报文 (0x355)"""
        try:
            data = msg['data']
            # 根据协议解析BMS状态
            self.log_message("解析BMS状态报文")
        except Exception as e:
            self.log_message(f"解析BMS状态报文错误: {str(e)}")
        
    def parse_battery_info_message(self, msg):
        """解析电池信息报文 (0x356)"""
        try:
            data = msg['data']
            # 根据协议解析电池信息
            self.log_message("解析电池信息报文")
        except Exception as e:
            self.log_message(f"解析电池信息报文错误: {str(e)}")
        
    def parse_error_message(self, msg):
        """解析错误报文 (0x35A)"""
        try:
            data = msg['data']
            # 根据协议解析错误信息
            self.log_message("解析错误报文")
        except Exception as e:
            self.log_message(f"解析错误报文错误: {str(e)}")
        
    def handle_heartbeat_timeout(self):
        """处理心跳超时"""
        self.heartbeat_status_var.set("超时")
        messagebox.showwarning("心跳超时", "BMS心跳终止")
        self.log_message("警告: BMS心跳终止，断开CAN连接")
        self.disconnect_can()

    def test_receive(self):
        """手动测试接收功能"""
        if not self.is_connected:
            messagebox.showwarning("警告", "请先连接CAN设备")
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
            messagebox.showwarning("警告", "请先连接CAN设备")
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
            messagebox.showwarning("警告", "请先连接CAN设备")
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

def main():
    root = tk.Tk()
    app = CANHostComputer(root)
    root.mainloop()

if __name__ == "__main__":
    main()