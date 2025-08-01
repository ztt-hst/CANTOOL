 # CAN协议配置文件

# 波特率设置
BAUDRATE_250K = 250000
BAUDRATE_500K = 500000

# CAN报文ID定义
CAN_IDS = {
    'INVERTER_TO_BMS': 0x305,    # 逆变器到BMS
    'INVERTER_CONTROL': 0x307,   # 逆变器控制
    'BMS_CHARGE_DISCHARGE': 0x351,  # BMS充放电信息（用作心跳标志）
    'BMS_STATUS': 0x355,         # BMS状态
    'BATTERY_INFO': 0x356,       # 电池信息
    'ERROR_MESSAGE': 0x35A,      # 错误信息
}

# 报文数据结构定义
MESSAGE_STRUCTURES = {
    0x305: {
        'name': '逆变器到BMS',
        'length': 8,
        'fields': [
            {'name': 'status', 'offset': 0, 'length': 1, 'description': '状态字节'},
            {'name': 'control', 'offset': 1, 'length': 1, 'description': '控制字节'},
            {'name': 'reserved', 'offset': 2, 'length': 6, 'description': '保留字节'},
        ]
    },
    0x307: {
        'name': '逆变器控制',
        'length': 8,
        'fields': [
            {'name': 'status', 'offset': 0, 'length': 1, 'description': '状态字节'},
            {'name': 'control', 'offset': 1, 'length': 1, 'description': '控制字节'},
            {'name': 'reserved', 'offset': 2, 'length': 6, 'description': '保留字节'},
        ]
    },
    0x351: {
        'name': 'BMS充放电信息（心跳标志）',
        'length': 8,
        'fields': [
            {'name': 'charge_voltage_limit', 'offset': 0, 'length': 2, 'data_type': 'un16', 'scaling': 0.1, 'unit': 'V', 'description': '充电电压限制'},
            {'name': 'max_charge_current', 'offset': 2, 'length': 2, 'data_type': 'un16', 'scaling': 0.1, 'unit': 'A', 'description': '最大充电电流'},
            {'name': 'max_discharge_current', 'offset': 4, 'length': 2, 'data_type': 'un16', 'scaling': 0.1, 'unit': 'A', 'description': '最大放电电流'},
            {'name': 'discharge_voltage', 'offset': 6, 'length': 2, 'data_type': 'un16', 'scaling': 0.1, 'unit': 'V', 'description': '放电电压'},
        ]
    },
    0x355: {
        'name': 'BMS状态',
        'length': 8,
        'fields': [
            {'name': 'soc_value', 'offset': 0, 'length': 2, 'data_type': 'un16', 'scaling': 1, 'unit': '%', 'description': 'SOC值'},
            {'name': 'soh_value', 'offset': 2, 'length': 2, 'data_type': 'un16', 'scaling': 1, 'unit': '%', 'description': 'SOH值'},
            {'name': 'high_res_soc', 'offset': 4, 'length': 2, 'data_type': 'un16', 'scaling': 0.01, 'unit': '%', 'description': '高精度SOC'},
        ]
    },
    0x356: {
        'name': '电池信息',
        'length': 8,
        'fields': [
            {'name': 'battery_voltage', 'offset': 0, 'length': 2, 'data_type': 'sn16', 'scaling': 0.01, 'unit': 'V', 'description': '电池电压'},
            {'name': 'battery_current', 'offset': 2, 'length': 2, 'data_type': 'sn16', 'scaling': 0.1, 'unit': 'A', 'description': '电池电流'},
            {'name': 'battery_temperature', 'offset': 4, 'length': 2, 'data_type': 'sn16', 'scaling': 0.1, 'unit': '°C', 'description': '电池温度'},
        ]
    },
    0x35A: {
        'name': 'BMS警告信息',
        'length': 8,
        'fields': [
            {'name': 'warnings', 'offset': 4, 'length': 4, 'data_type': 'bit_flags', 'description': '警告位'},
        ]
    }
}

# 心跳超时设置（秒）
HEARTBEAT_TIMEOUT = 3

# 发送间隔设置（秒）
SEND_INTERVAL = 1

# 创芯科技设备设置
CANALYST_DEVICE_TYPE = 4  # VCI_USBCAN2
CANALYST_DEVICE_INDEX = 0
CANALYST_CAN_INDEX = 0

# 定时参数映射
TIMING_PARAMS = {
    250000: (0x03, 0x1C),  # 250kbps
    500000: (0x00, 0x1C),  # 500kbps
}

def signed_16bit(high_byte, low_byte):
    """将两个字节转换为有符号16位整数"""
    value = (high_byte << 8) | low_byte
    if value > 32767:  # 负数
        value -= 65536
    return value

def parse_351_message(data):
    """解析0x351报文 - 充放电信息（用作心跳标志）"""
    if len(data) >= 8:
        # 解析充放电信息
        charge_voltage_limit = (data[1] << 8 | data[0]) * 0.1  # 充电电压限制 (V)
        max_charge_current = (data[3] << 8 | data[2]) * 0.1    # 最大充电电流 (A)
        max_discharge_current = (data[5] << 8 | data[4]) * 0.1  # 最大放电电流 (A)
        discharge_voltage = (data[7] << 8 | data[6]) * 0.1      # 放电电压 (V)
        
        return {
            'charge_voltage_limit': charge_voltage_limit,
            'max_charge_current': max_charge_current,
            'max_discharge_current': max_discharge_current,
            'discharge_voltage': discharge_voltage
        }
    else:
        return None

def parse_355_message(data):
    """解析0x355报文 - BMS状态信息"""
    if len(data) >= 6:
        # 解析SOC和SOH信息
        soc_value = (data[1] << 8 | data[0])  # SOC值 (%)
        soh_value = (data[3] << 8 | data[2])  # SOH值 (%)
        high_res_soc = (data[5] << 8 | data[4]) * 0.01  # 高精度SOC (%)
        
        return {
            'soc_value': soc_value,
            'soh_value': soh_value,
            'high_res_soc': high_res_soc
        }
    else:
        return None

def parse_356_message(data):
    """解析0x356报文 - 电池信息"""
    if len(data) >= 6:
        # 解析电池信息（注意：sn16是有符号16位整数）
        battery_voltage = signed_16bit(data[1], data[0]) * 0.01  # 电池电压 (V)
        battery_current = signed_16bit(data[3], data[2]) * 0.1    # 电池电流 (A)
        battery_temperature = signed_16bit(data[5], data[4]) * 0.1 # 电池温度 (°C)
        
        return {
            'battery_voltage': battery_voltage,
            'battery_current': battery_current,
            'battery_temperature': battery_temperature
        }
    else:
        return None

def parse_35A_message(data):
    """解析0x35A报文 - BMS警告信息"""
    if len(data) >= 8:
        # 解析警告位
        warnings = {}
        
        # Byte 4: 警告信息
        byte4 = data[4]
        warnings['general_warning'] = bool(byte4 & 0x03)        # bits 0+1
        warnings['battery_high_voltage'] = bool(byte4 & 0x0C)    # bits 2+3
        warnings['battery_low_voltage'] = bool(byte4 & 0x30)     # bits 4+5
        warnings['battery_high_temp'] = bool(byte4 & 0xC0)       # bits 6+7
        
        # Byte 5: 更多警告信息
        byte5 = data[5]
        warnings['battery_low_temp'] = bool(byte5 & 0x03)        # bits 0+1
        warnings['battery_high_temp_charge'] = bool(byte5 & 0x0C) # bits 2+3
        warnings['battery_low_temp_charge'] = bool(byte5 & 0x30)  # bits 4+5
        warnings['battery_high_current'] = bool(byte5 & 0xC0)     # bits 6+7
        
        # Byte 6: 更多警告信息
        byte6 = data[6]
        warnings['battery_high_charge_current'] = bool(byte6 & 0x03) # bits 0+1
        warnings['contactor_warning'] = bool(byte6 & 0x0C)           # bits 2+3
        warnings['short_circuit_warning'] = bool(byte6 & 0x30)       # bits 4+5
        warnings['bms_internal'] = bool(byte6 & 0xC0)                # bits 6+7
        
        # Byte 7: 更多警告信息
        byte7 = data[7]
        warnings['cell_imbalance'] = bool(byte7 & 0x03)          # bits 0+1
        # bits 2-7: Reserved (保留位)
        
        return {'warnings': warnings}
    else:
        return None


# 通用解析函数
def parse_can_message(can_id, data):
    """通用CAN报文解析函数"""
    if can_id == 0x351:
        return parse_351_message(data)
    elif can_id == 0x355:
        return parse_355_message(data)
    elif can_id == 0x356:
        return parse_356_message(data)
    elif can_id == 0x35A:
        return parse_35A_message(data)
    else:
        return None