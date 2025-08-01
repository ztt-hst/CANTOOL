import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
from datetime import datetime
import json
import struct

class CANHostComputer:
    def __init__(self, root):
        self.root = root
        self.root.title("CAN协议上位机 - Windows版本")
        self.root.geometry("900x700")
        
        # CAN相关变量
        self.can_bus = None
        self.is_connected = False
        self.is_running = False
        self.last_heartbeat_time = None
        self.heartbeat_monitor_thread = None
        self.simulation_mode = False
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 连接设置框架
        connection_frame = ttk.LabelFrame(main_frame, text="连接设置", padding="10")
        connection_frame.pack(fill="x", pady=5)
        
        # 第一行：接口选择
        row1 = ttk.Frame(connection_frame)
        row1.pack(fill="x", pady=2)
        
        ttk.Label(row1, text="接口类型:").pack(side="left", padx=5)
        self.interface_var = tk.StringVar(value="simulation")
        interface_combo = ttk.Combobox(row1, textvariable=self.interface_var, 
                                     values=["simulation", "pcan", "usb-can", "serial-can"], width=15)
        interface_combo.pack(side="left", padx=5)
        
        ttk.Label(row1, text="通道:").pack(side="left", padx=5)
        self.channel_var = tk.StringVar(value="USB0")
        channel_entry = ttk.Entry(row1, textvariable=self.channel_var, width=10)
        channel_entry.pack(side="left", padx=5)
        
        # 第二行：波特率和其他设置
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
        
        # 初始化统计变量
        self.sent_count = 0
        self.received_count = 0
        
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
            interface = self.interface_var.get()
            channel = self.channel_var.get()
            baudrate = int(self.baudrate_var.get())
            
            if interface == "simulation":
                self.simulation_mode = True
                self.can_bus = SimulationCANBus()
                self.log_message("进入模拟模式")
            else:
                # 这里可以添加真实的CAN接口连接代码
                # 例如使用PCAN、USB-CAN等
                self.simulation_mode = False
                self.can_bus = RealCANBus(interface, channel, baudrate)
                
            self.is_connected = True
            
            self.connect_btn.config(state="disabled")
            self.disconnect_btn.config(state="normal")
            self.start_btn.config(state="normal")
            
            self.status_var.set("已连接")
            self.log_message(f"CAN总线连接成功 - 接口: {interface}, 通道: {channel}, 波特率: {baudrate}")
            
        except Exception as e:
            messagebox.showerror("连接错误", f"无法连接CAN总线: {str(e)}")
            self.log_message(f"连接失败: {str(e)}")
            
    def disconnect_can(self):
        """断开CAN连接"""
        if self.can_bus:
            self.stop_sending()
            if hasattr(self.can_bus, 'shutdown'):
                self.can_bus.shutdown()
            self.can_bus = None
            
        self.is_connected = False
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        
        self.status_var.set("未连接")
        self.log_message("CAN总线已断开")
        
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
                # 发送ID为0x305的报文 (Inverter to BMS)
                msg_305_data = self.create_305_message()
                msg_305 = CANMessage(0x305, msg_305_data)
                self.can_bus.send(msg_305)
                self.sent_count += 1
                self.sent_count_var.set(str(self.sent_count))
                self.log_message(f"发送: ID=0x305, 数据: {msg_305_data.hex()}")
                
                # 发送ID为0x307的报文
                msg_307_data = self.create_307_message()
                msg_307 = CANMessage(0x307, msg_307_data)
                self.can_bus.send(msg_307)
                self.sent_count += 1
                self.sent_count_var.set(str(self.sent_count))
                self.log_message(f"发送: ID=0x307, 数据: {msg_307_data.hex()}")
                
                time.sleep(1)  # 每秒发送一次
                
            except Exception as e:
                self.log_message(f"发送错误: {str(e)}")
                break
                
    def create_305_message(self):
        """创建0x305报文数据"""
        # 根据协议文档创建具体的数据
        # 这里提供一个示例实现
        data = bytearray(8)
        data[0] = 0x01  # 状态字节
        data[1] = 0x02  # 控制字节
        # 其他字节根据协议设置
        return data
        
    def create_307_message(self):
        """创建0x307报文数据"""
        # 根据协议文档创建具体的数据
        data = bytearray(8)
        data[0] = 0x03  # 状态字节
        data[1] = 0x04  # 控制字节
        # 其他字节根据协议设置
        return data
                
    def monitor_heartbeat(self):
        """监控心跳的线程函数"""
        while self.is_running and self.is_connected:
            try:
                # 接收CAN报文
                msg = self.can_bus.recv(timeout=0.1)
                
                if msg:
                    self.received_count += 1
                    self.received_count_var.set(str(self.received_count))
                    self.process_received_message(msg)
                    
                    # 检查心跳报文
                    if msg.arbitration_id == 0x351:
                        self.last_heartbeat_time = time.time()
                        self.heartbeat_status_var.set("正常")
                        self.log_message(f"收到心跳: ID=0x351, 数据: {msg.data.hex()}")
                        
            except Exception as e:
                # 检查心跳超时
                if self.last_heartbeat_time and (time.time() - self.last_heartbeat_time) > 3:
                    self.root.after(0, self.handle_heartbeat_timeout)
                    
    def process_received_message(self, msg):
        """处理接收到的CAN报文"""
        msg_id = msg.arbitration_id
        
        if msg_id in [0x351, 0x355, 0x356, 0x35A]:
            self.log_message(f"解析报文: ID=0x{msg_id:03X}, 数据: {msg.data.hex()}")
            
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
            # 解析心跳报文的具体字段
            data = msg.data
            status = data[0] if len(data) > 0 else 0
            self.log_message(f"心跳状态: {status}")
        except Exception as e:
            self.log_message(f"解析心跳报文错误: {str(e)}")
        
    def parse_bms_status_message(self, msg):
        """解析BMS状态报文 (0x355)"""
        try:
            data = msg.data
            # 根据协议解析BMS状态
            self.log_message("解析BMS状态报文")
        except Exception as e:
            self.log_message(f"解析BMS状态报文错误: {str(e)}")
        
    def parse_battery_info_message(self, msg):
        """解析电池信息报文 (0x356)"""
        try:
            data = msg.data
            # 根据协议解析电池信息
            self.log_message("解析电池信息报文")
        except Exception as e:
            self.log_message(f"解析电池信息报文错误: {str(e)}")
        
    def parse_error_message(self, msg):
        """解析错误报文 (0x35A)"""
        try:
            data = msg.data
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

class CANMessage:
    """CAN报文类"""
    def __init__(self, arbitration_id, data, is_extended_id=False):
        self.arbitration_id = arbitration_id
        self.data = data
        self.is_extended_id = is_extended_id
        self.timestamp = time.time()

class SimulationCANBus:
    """模拟CAN总线类"""
    def __init__(self):
        self.received_messages = []
        self.sent_messages = []
        
    def send(self, message):
        """发送CAN报文"""
        self.sent_messages.append(message)
        
    def recv(self, timeout=0.1):
        """接收CAN报文"""
        if self.received_messages:
            return self.received_messages.pop(0)
        time.sleep(timeout)
        return None
        
    def shutdown(self):
        """关闭连接"""
        pass

class RealCANBus:
    """真实CAN总线类"""
    def __init__(self, interface, channel, baudrate):
        self.interface = interface
        self.channel = channel
        self.baudrate = baudrate
        # 这里可以添加真实的CAN接口初始化代码
        
    def send(self, message):
        """发送CAN报文"""
        # 实现真实的CAN发送
        pass
        
    def recv(self, timeout=0.1):
        """接收CAN报文"""
        # 实现真实的CAN接收
        return None
        
    def shutdown(self):
        """关闭连接"""
        pass

def main():
    root = tk.Tk()
    app = CANHostComputer(root)
    root.mainloop()

if __name__ == "__main__":
    main()