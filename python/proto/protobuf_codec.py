"""
Protobuf 编码器 - 用于与 Rust Gateway 通信

由于没有 protoc，我们手动实现简单的 Protobuf 编码
"""
import struct


class ProtobufEncoder:
    """简单的 Protobuf 编码器"""

    @staticmethod
    def encode_string(field_number: int, value: str) -> bytes:
        """编码字符串字段"""
        if not value:
            return b''
        data = value.encode('utf-8')
        tag = (field_number << 3) | 2  # wire type 2 = length-delimited
        return bytes([tag]) + ProtobufEncoder._encode_varint(len(data)) + data

    @staticmethod
    def encode_double(field_number: int, value: float) -> bytes:
        """编码 double 字段"""
        if value == 0.0:
            return b''
        tag = (field_number << 3) | 1  # wire type 1 = 64-bit
        return bytes([tag]) + struct.pack('<d', value)

    @staticmethod
    def encode_int32(field_number: int, value: int) -> bytes:
        """编码 int32 字段"""
        if value == 0:
            return b''
        tag = (field_number << 3) | 0  # wire type 0 = varint
        return bytes([tag]) + ProtobufEncoder._encode_varint(value)

    @staticmethod
    def encode_int64(field_number: int, value: int) -> bytes:
        """编码 int64 字段"""
        if value == 0:
            return b''
        tag = (field_number << 3) | 0  # wire type 0 = varint
        return bytes([tag]) + ProtobufEncoder._encode_varint(value)

    @staticmethod
    def _encode_varint(value: int) -> bytes:
        """编码 varint"""
        result = []
        while value > 0x7f:
            result.append((value & 0x7f) | 0x80)
            value >>= 7
        result.append(value & 0x7f)
        return bytes(result)


def encode_order(order_id: str, strategy_id: str, symbol: str,
                 price: float, volume: int, side: str, timestamp: int) -> bytes:
    """
    编码订单消息

    message Order {
      string order_id = 1;
      string strategy_id = 2;
      string symbol = 3;
      double price = 4;
      int32 volume = 5;
      string side = 6;
      int64 timestamp = 7;
    }
    """
    parts = []
    parts.append(ProtobufEncoder.encode_string(1, order_id))
    parts.append(ProtobufEncoder.encode_string(2, strategy_id))
    parts.append(ProtobufEncoder.encode_string(3, symbol))
    parts.append(ProtobufEncoder.encode_double(4, price))
    parts.append(ProtobufEncoder.encode_int32(5, volume))
    parts.append(ProtobufEncoder.encode_string(6, side))
    parts.append(ProtobufEncoder.encode_int64(7, timestamp))

    return b''.join(parts)


def decode_trade(data: bytes) -> dict:
    """
    解码成交回报消息

    message Trade {
      string trade_id = 1;
      string order_id = 2;
      string strategy_id = 3;
      string symbol = 4;
      string side = 5;
      double filled_price = 6;
      int32 filled_volume = 7;
      int64 trade_time = 8;
      string status = 9;
      int32 error_code = 10;
      string error_message = 11;
      bool is_retryable = 12;
      double commission = 13;
    }
    """
    result = {}
    pos = 0

    while pos < len(data):
        # 读取 tag
        tag, pos = _read_varint(data, pos)
        field_number = tag >> 3
        wire_type = tag & 0x7

        if wire_type == 0:  # varint
            value, pos = _read_varint(data, pos)
            if field_number == 7:
                result['filled_volume'] = value
            elif field_number == 8:
                result['trade_time'] = value
            elif field_number == 10:
                result['error_code'] = value
            elif field_number == 12:
                result['is_retryable'] = bool(value)

        elif wire_type == 1:  # 64-bit
            value = struct.unpack('<d', data[pos:pos+8])[0]
            pos += 8
            if field_number == 6:
                result['filled_price'] = value
            elif field_number == 13:
                result['commission'] = value

        elif wire_type == 2:  # length-delimited
            length, pos = _read_varint(data, pos)
            value = data[pos:pos+length].decode('utf-8')
            pos += length

            if field_number == 1:
                result['trade_id'] = value
            elif field_number == 2:
                result['order_id'] = value
            elif field_number == 3:
                result['strategy_id'] = value
            elif field_number == 4:
                result['symbol'] = value
            elif field_number == 5:
                result['side'] = value
            elif field_number == 9:
                result['status'] = value
            elif field_number == 11:
                result['error_message'] = value

        else:
            raise ValueError(f"Unknown wire type: {wire_type}")

    return result


def decode_market_data(data: bytes) -> dict:
    """
    解码行情数据消息

    message MarketData {
      string symbol = 1;
      double last_price = 2;
      double volume = 3;
      int64 exchange_time = 4;
      int64 local_time = 5;
      string exchange = 6;
    }
    """
    result = {}
    pos = 0

    while pos < len(data):
        # 读取 tag
        tag, pos = _read_varint(data, pos)
        field_number = tag >> 3
        wire_type = tag & 0x7

        if wire_type == 0:  # varint
            value, pos = _read_varint(data, pos)
            if field_number == 4:
                result['exchange_time'] = value
            elif field_number == 5:
                result['local_time'] = value

        elif wire_type == 1:  # 64-bit
            value = struct.unpack('<d', data[pos:pos+8])[0]
            pos += 8
            if field_number == 2:
                result['last_price'] = value
            elif field_number == 3:
                result['volume'] = value

        elif wire_type == 2:  # length-delimited
            length, pos = _read_varint(data, pos)
            value = data[pos:pos+length].decode('utf-8')
            pos += length

            if field_number == 1:
                result['symbol'] = value
            elif field_number == 6:
                result['exchange'] = value

        else:
            raise ValueError(f"Unknown wire type: {wire_type}")

    return result


def _read_varint(data: bytes, pos: int) -> tuple:
    """读取 varint"""
    result = 0
    shift = 0
    while True:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7f) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    return result, pos


if __name__ == "__main__":
    # 测试编码
    order_bytes = encode_order(
        order_id="ORDER_123",
        strategy_id="test_strategy",
        symbol="BTCUSDT",
        price=50000.0,
        volume=1,
        side="BUY",
        timestamp=1234567890000000000
    )
    print(f"Encoded order: {len(order_bytes)} bytes")
    print(f"Hex: {order_bytes.hex()}")
