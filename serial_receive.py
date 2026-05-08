import argparse
import sys
from datetime import datetime

import serial


DEFAULT_PORT = "COM3"
DEFAULT_BAUDRATE = 115200

HEADER = bytes([0xAA, 0x55])
FRAME_ID = 0x41
DATA_LENGTH = 0x14
FRAME_SIZE = 25


def bytes_to_int24(data: bytes) -> int:
    """Convert 3 big-endian bytes to a signed 24-bit integer."""
    if len(data) != 3:
        raise ValueError("int24 requires exactly 3 bytes")

    value = int.from_bytes(data, byteorder="big", signed=False)
    if value & 0x800000:
        value -= 1 << 24
    return value


def bytes_to_temp(data: bytes) -> int:
    """Convert 2 big-endian bytes to a signed 16-bit temperature value."""
    if len(data) != 2:
        raise ValueError("temperature requires exactly 2 bytes")

    value = int.from_bytes(data, byteorder="big", signed=False)
    if value & 0x8000:
        value -= 1 << 16
    return value


def parse_frame(frame: bytes) -> dict:
    if len(frame) != FRAME_SIZE:
        raise ValueError(f"frame must be {FRAME_SIZE} bytes")
    if frame[0:2] != HEADER:
        raise ValueError("invalid header")
    if frame[2] != FRAME_ID:
        raise ValueError(f"invalid frame id: 0x{frame[2]:02X}")
    if frame[3] != DATA_LENGTH:
        raise ValueError(f"invalid data length: {frame[3]}")

    return {
        "gyro_x": bytes_to_int24(frame[4:7]),
        "gyro_y": bytes_to_int24(frame[7:10]),
        "gyro_z": bytes_to_int24(frame[10:13]),
        "acc_x": bytes_to_int24(frame[13:16]),
        "acc_y": bytes_to_int24(frame[16:19]),
        "acc_z": bytes_to_int24(frame[19:22]),
        "temp_c": bytes_to_temp(frame[22:24]),
        "reserved": frame[24],
    }


def find_frame(buffer: bytearray) -> bytes | None:
    header_index = buffer.find(HEADER)
    if header_index < 0:
        buffer.clear()
        return None

    if header_index > 0:
        del buffer[:header_index]

    if len(buffer) < FRAME_SIZE:
        return None

    frame = bytes(buffer[:FRAME_SIZE])
    del buffer[:FRAME_SIZE]
    return frame


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Receive and decode frames sent by serial_send.py"
    )
    parser.add_argument("--port", default=DEFAULT_PORT, help="Serial port")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUDRATE, help="Baud rate")
    parser.add_argument("--timeout", type=float, default=0.1, help="Read timeout")
    parser.add_argument("--raw", action="store_true", help="Show raw frame bytes")
    args = parser.parse_args()

    buffer = bytearray()

    try:
        with serial.Serial(args.port, args.baud, timeout=args.timeout) as ser:
            print(f"Listening on {args.port} @ {args.baud} bps")
            print("Press Ctrl+C to stop.\n")

            while True:
                data = ser.read(256)
                if not data:
                    continue

                buffer.extend(data)

                while True:
                    frame = find_frame(buffer)
                    if frame is None:
                        break

                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    try:
                        values = parse_frame(frame)
                    except ValueError as exc:
                        print(
                            f"[{timestamp}] Invalid frame: {exc} "
                            f"raw={frame.hex(' ').upper()}"
                        )
                        continue

                    if args.raw:
                        print(f"[{timestamp}] RAW: {frame.hex(' ').upper()}")

                    print(
                        f"[{timestamp}] "
                        f"gyro=({values['gyro_x']}, {values['gyro_y']}, {values['gyro_z']}) "
                        f"acc=({values['acc_x']}, {values['acc_y']}, {values['acc_z']}) "
                        f"temp={values['temp_c']} "
                        f"reserved=0x{values['reserved']:02X}"
                    )

    except serial.SerialException as exc:
        print(f"Serial error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
