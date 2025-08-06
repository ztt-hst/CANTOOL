import json
import os
import sys
from typing import Dict, Optional

class LanguageManager:
    """语言管理器"""
    
    def __init__(self, default_language='chinese'):
        # 获取程序运行路径
        if getattr(sys, 'frozen', False):
            # 打包后的路径
            self.base_path = sys._MEIPASS
        else:
            # 开发环境路径
            self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.languages_dir = os.path.join(self.base_path, 'languages')
        self.current_language = default_language
        self.language_data = {}
        self.available_languages = []
        
        # 加载可用语言
        self.load_available_languages()
        
        # 加载默认语言
        self.load_language(default_language)
    
    def load_available_languages(self):
        """加载可用的语言列表"""
        self.available_languages = []
        
        # 检查languages目录是否存在
        if os.path.exists(self.languages_dir):
            for file in os.listdir(self.languages_dir):
                if file.endswith('.json'):
                    language_name = file.replace('.json', '')
                    self.available_languages.append(language_name)
        else:
            # 如果目录不存在，尝试从打包的资源中加载
            self.available_languages = ['chinese', 'english']
    
    def load_language(self, language: str) -> bool:
        """加载指定语言"""
        try:
            # 首先尝试从文件系统加载
            language_file = os.path.join(self.languages_dir, f'{language}.json')
            if os.path.exists(language_file):
                with open(language_file, 'r', encoding='utf-8') as f:
                    self.language_data = json.load(f)
                self.current_language = language
                return True
            
            # 如果文件不存在，尝试从打包的资源加载
            return self.load_language_from_package(language)
            
        except Exception as e:
            print(f"Error loading language {language}: {str(e)}")
            return False
    
    def load_language_from_package(self, language: str) -> bool:
        """从打包的资源中加载语言"""
        try:
            # 尝试从sys._MEIPASS加载语言文件
            if getattr(sys, 'frozen', False):
                resource_path = os.path.join(sys._MEIPASS, 'languages', f'{language}.json')
                if os.path.exists(resource_path):
                    with open(resource_path, 'r', encoding='utf-8') as f:
                        self.language_data = json.load(f)
                    self.current_language = language
                    return True
            
            # 如果还是找不到，使用内置的默认语言
            return self.load_default_language(language)
            
        except Exception as e:
            print(f"Error loading language from package {language}: {str(e)}")
            return False
    
    def load_default_language(self, language: str) -> bool:
        """加载默认语言（内置在代码中）"""
        if language == 'chinese':
            self.language_data = {
                "window_title": "CAN协议上位机 - 创芯科技CANalyst-II",
                "connection_settings": "连接设置",
                "device_type": "设备类型",
                "device_index": "设备索引",
                "can_channel": "CAN通道",
                "baudrate": "波特率",
                "connect": "连接",
                "disconnect": "断开",
                "not_connected": "未连接",
                "connected": "已连接",
                "control": "控制",
                "send_control": "发送控制",
                "start_sending": "启动发送",
                "stop_sending": "停止发送",
                "receive_control": "接收控制",
                "enable_receiving": "开启接收",
                "statistics": "统计信息",
                "sent": "发送",
                "received": "接收",
                "heartbeat_status": "心跳状态",
                "normal": "正常",
                "waiting": "等待",
                "stopped": "停止",
                "send_data": "发送数据",
                "real_time_data": "实时数据",
                "can_id": "CAN ID",
                "parameter": "参数",
                "value": "数值",
                "unit": "单位",
                "status": "状态",
                "refresh_time": "刷新时间",
                "send_status": "发送状态",
                "send_count": "发送次数",
                "send_time": "发送时间",
                "communication_log": "通信日志",
                "clear_log": "清空日志",
                "auto_save_log": "自动保存日志",
                "connecting_can_device": "正在连接CAN设备...",
                "can_device_connected": "CAN设备连接成功",
                "connection_failed": "连接失败",
                "connection_error": "连接错误",
                "cannot_connect_can_device": "无法连接CAN设备",
                "auto_save_log_enabled": "自动保存日志已开启，日志文件",
                "auto_save_log_disabled": "自动保存日志已停止，日志文件",
                "error": "错误",
                "cannot_create_log_file": "无法创建日志文件",
                "save_success": "保存成功",
                "save_failed": "保存失败",
                "cannot_save_log": "无法保存日志",
                "warning": "警告",
                "heartbeat_timeout": "BMS心跳终止 - 3秒未收到0x351报文",
                "please_connect_first": "请先连接CAN设备",
                "heartbeat_status_param": "心跳状态",
                "charge_voltage_limit": "充电电压限制",
                "max_charge_current": "最大充电电流",
                "max_discharge_current": "最大放电电流",
                "discharge_voltage": "放电电压",
                "soc_value": "SOC值",
                "soh_value": "SOH值",
                "high_precision_soc": "高精度SOC",
                "battery_voltage": "电池电压",
                "battery_current": "电池电流",
                "battery_temperature": "电池温度",
                "battery_high_voltage_alarm": "电池高压报警",
                "battery_low_voltage_alarm": "电池低压报警",
                "battery_high_temp_alarm": "电池高温报警",
                "battery_low_temp_alarm": "电池低温报警",
                "battery_high_current_alarm": "电池过流报警",
                "bms_internal_alarm": "BMS内部报警",
                "cell_imbalance_alarm": "电池不平衡报警",
                "battery_high_voltage_warning": "电池高压警告",
                "battery_low_voltage_warning": "电池低压警告",
                "battery_high_temp_warning": "电池高温警告",
                "battery_low_temp_warning": "电池低温警告",
                "battery_high_current_warning": "电池过流警告",
                "bms_internal_warning": "BMS内部警告",
                "cell_imbalance_warning": "电池不平衡警告",
                "system_status": "系统状态",
                "online": "在线",
                "offline": "离线",
                "stopped_sending": "停止发送",
                "sending": "正在发送",
                "stopped_status": "已停止",
                "waiting_status": "等待",
                "normal_status": "正常",
                "yes": "是",
                "no": "否"
            }
            self.current_language = language
            return True
        elif language == 'english':
            self.language_data = {
                "window_title": "CAN Protocol Host Computer - ZLG CANalyst-II",
                "connection_settings": "Connection Settings",
                "device_type": "Device Type",
                "device_index": "Device Index",
                "can_channel": "CAN Channel",
                "baudrate": "Baudrate",
                "connect": "Connect",
                "disconnect": "Disconnect",
                "not_connected": "Not Connected",
                "connected": "Connected",
                "control": "Control",
                "send_control": "Send Control",
                "start_sending": "Start Sending",
                "stop_sending": "Stop Sending",
                "receive_control": "Receive Control",
                "enable_receiving": "Enable Receiving",
                "statistics": "Statistics",
                "sent": "Sent",
                "received": "Received",
                "heartbeat_status": "Heartbeat Status",
                "normal": "Normal",
                "waiting": "Waiting",
                "stopped": "Stopped",
                "send_data": "Send Data",
                "real_time_data": "Real-time Data",
                "can_id": "CAN ID",
                "parameter": "Parameter",
                "value": "Value",
                "unit": "Unit",
                "status": "Status",
                "refresh_time": "Refresh Time",
                "send_status": "Send Status",
                "send_count": "Send Count",
                "send_time": "Send Time",
                "communication_log": "Communication Log",
                "clear_log": "Clear Log",
                "auto_save_log": "Auto Save Log",
                "connecting_can_device": "Connecting to CAN device...",
                "can_device_connected": "CAN device connected successfully",
                "connection_failed": "Connection failed",
                "connection_error": "Connection Error",
                "cannot_connect_can_device": "Cannot connect to CAN device",
                "auto_save_log_enabled": "Auto save log enabled, log file",
                "auto_save_log_disabled": "Auto save log disabled, log file",
                "error": "Error",
                "cannot_create_log_file": "Cannot create log file",
                "save_success": "Save Success",
                "save_failed": "Save Failed",
                "cannot_save_log": "Cannot save log",
                "warning": "Warning",
                "heartbeat_timeout": "BMS heartbeat terminated - No 0x351 message received for 3 seconds",
                "please_connect_first": "Please connect to CAN device first",
                "heartbeat_status_param": "Heartbeat Status",
                "charge_voltage_limit": "Charge Voltage Limit",
                "max_charge_current": "Max Charge Current",
                "max_discharge_current": "Max Discharge Current",
                "discharge_voltage": "Discharge Voltage",
                "soc_value": "SOC Value",
                "soh_value": "SOH Value",
                "high_precision_soc": "High Precision SOC",
                "battery_voltage": "Battery Voltage",
                "battery_current": "Battery Current",
                "battery_temperature": "Battery Temperature",
                "battery_high_voltage_alarm": "Battery High Voltage Alarm",
                "battery_low_voltage_alarm": "Battery Low Voltage Alarm",
                "battery_high_temp_alarm": "Battery High Temp Alarm",
                "battery_low_temp_alarm": "Battery Low Temp Alarm",
                "battery_high_current_alarm": "Battery High Current Alarm",
                "bms_internal_alarm": "BMS Internal Alarm",
                "cell_imbalance_alarm": "Cell Imbalance Alarm",
                "battery_high_voltage_warning": "Battery High Voltage Warning",
                "battery_low_voltage_warning": "Battery Low Voltage Warning",
                "battery_high_temp_warning": "Battery High Temp Warning",
                "battery_low_temp_warning": "Battery Low Temp Warning",
                "battery_high_current_warning": "Battery High Current Warning",
                "bms_internal_warning": "BMS Internal Warning",
                "cell_imbalance_warning": "Cell Imbalance Warning",
                "system_status": "System Status",
                "online": "Online",
                "offline": "Offline",
                "stopped_sending": "Stopped Sending",
                "sending": "Sending",
                "stopped_status": "Stopped",
                "waiting_status": "Waiting",
                "normal_status": "Normal",
                "yes": "Yes",
                "no": "No"
            }
            self.current_language = language
            return True
        
        return False
    
    def get_text(self, key: str, default: str = None) -> str:
        """获取指定键的文本"""
        return self.language_data.get(key, default or key)
    
    def get_current_language(self) -> str:
        """获取当前语言"""
        return self.current_language
    
    def get_available_languages(self) -> list:
        """获取可用语言列表"""
        return self.available_languages.copy()
    
    def switch_language(self, language: str) -> bool:
        """切换语言"""
        if language in self.available_languages:
            return self.load_language(language)
        return False
    
    def create_language_file(self, language: str, data: Dict[str, str]) -> bool:
        """创建新的语言文件"""
        try:
            language_file = os.path.join(self.languages_dir, f'{language}.json')
            with open(language_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 重新加载可用语言列表
            self.load_available_languages()
            return True
        except Exception as e:
            print(f"Error creating language file: {str(e)}")
            return False
    
    def export_language_template(self, language: str) -> bool:
        """导出语言模板"""
        try:
            template_file = os.path.join(self.languages_dir, f'{language}_template.json')
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(self.language_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting template: {str(e)}")
            return False 