 # CAN协议配置文件

# 波特率设置
BAUDRATE_250K = 250000
BAUDRATE_500K = 500000

# CAN报文ID定义
CAN_IDS = {
    'INVERTER_TO_BMS': 0x305,    # 逆变器到BMS
    'INVERTER_CONTROL': 0x307,   # 逆变器控制
    'BMS_HEARTBEAT': 0x351,      # BMS心跳
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
        'name': 'BMS心跳',
        'length': 8,
        'fields': [
            {'name': 'heartbeat_status', 'offset': 0, 'length': 1, 'description': '心跳状态'},
            {'name': 'reserved', 'offset': 1, 'length': 7, 'description': '保留字节'},
        ]
    },
    0x355: {
        'name': 'BMS状态',
        'length': 8,
        'fields': [
            {'name': 'bms_status', 'offset': 0, 'length': 1, 'description': 'BMS状态'},
            {'name': 'reserved', 'offset': 1, 'length': 7, 'description': '保留字节'},
        ]
    },
    0x356: {
        'name': '电池信息',
        'length': 8,
        'fields': [
            {'name': 'battery_voltage', 'offset': 0, 'length': 2, 'description': '电池电压'},
            {'name': 'battery_current', 'offset': 2, 'length': 2, 'description': '电池电流'},
            {'name': 'battery_soc', 'offset': 4, 'length': 1, 'description': '电池SOC'},
            {'name': 'reserved', 'offset': 5, 'length': 3, 'description': '保留字节'},
        ]
    },
    0x35A: {
        'name': '错误信息',
        'length': 8,
        'fields': [
            {'name': 'error_code', 'offset': 0, 'length': 2, 'description': '错误代码'},
            {'name': 'error_level', 'offset': 2, 'length': 1, 'description': '错误等级'},
            {'name': 'reserved', 'offset': 3, 'length': 5, 'description': '保留字节'},
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