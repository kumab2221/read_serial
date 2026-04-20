import serial
import struct
import time

# =========================
# 設定
# =========================
PORT = "COM3"        # Linuxなら "/dev/ttyUSB0"
BAUDRATE = 115200

# =========================
# 補助関数
# =========================
def int24_to_bytes(value: int):
    """
    signed 24bit -> [MSB, MID, LSB]
    """
    if value < 0:
        value = (1 << 24) + value
    return [
        (value >> 16) & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF,
    ]

def temp_to_raw(temp_c: float):
    """
    温度(℃) -> Q8.8 raw値（オフセット -25℃）
    """
    raw = int((temp_c + 25.0) * 256)
    return raw & 0xFFFF

# =========================
# フレーム生成
# =========================
def make_frame(
    gyro_x, gyro_y, gyro_z,
    acc_x, acc_y, acc_z,
    temp_c
):
    frame = []

    # ヘッダ
    frame += [0xAA, 0x55]
    frame += [0x41]        # ID
    frame += [0x14]        # Data length = 20

    # Gyro
    frame += int24_to_bytes(gyro_x)
    frame += int24_to_bytes(gyro_y)
    frame += int24_to_bytes(gyro_z)

    # Acc
    frame += int24_to_bytes(acc_x)
    frame += int24_to_bytes(acc_y)
    frame += int24_to_bytes(acc_z)

    # Temp (16bit, MSB→LSB)
    temp_raw = temp_to_raw(temp_c)
    frame += [(temp_raw >> 8) & 0xFF, temp_raw & 0xFF]

    # 予約
    frame += [0x00]

    assert len(frame) == 25
    return bytes(frame)

# =========================
# 送信処理
# =========================
with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:
    while True:
        frame = make_frame(
            gyro_x=0,
            gyro_y=10,
            gyro_z=0,
            acc_x=0,
            acc_y=0,
            acc_z=0,
            temp_c=0
        )

        ser.write(frame)
        print("Sent:", frame.hex(" "))

        time.sleep(0.1)