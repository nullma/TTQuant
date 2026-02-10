"""
简单的 Protobuf 解码器用于测试 OKX 行情数据
"""
import struct

def decode_market_data(data):
    """
    手动解码 MarketData protobuf 消息
    这是一个简化版本，仅用于测试
    """
    result = {}
    i = 0

    while i < len(data):
        # 读取字段标签和类型
        if i >= len(data):
            break

        tag_byte = data[i]
        i += 1

        field_number = tag_byte >> 3
        wire_type = tag_byte & 0x07

        # wire_type: 0=varint, 1=64bit, 2=length-delimited, 5=32bit

        if wire_type == 2:  # length-delimited (string)
            length, bytes_read = decode_varint(data[i:])
            i += bytes_read
            value = data[i:i+length].decode('utf-8')
            i += length

            if field_number == 1:
                result['symbol'] = value
            elif field_number == 6:
                result['exchange'] = value

        elif wire_type == 1:  # 64-bit (double)
            value = struct.unpack('<d', data[i:i+8])[0]
            i += 8

            if field_number == 2:
                result['last_price'] = value
            elif field_number == 3:
                result['volume'] = value

        elif wire_type == 0:  # varint (int64)
            value, bytes_read = decode_varint(data[i:])
            i += bytes_read

            if field_number == 4:
                result['exchange_time'] = value
            elif field_number == 5:
                result['local_time'] = value

    return result

def decode_varint(data):
    """解码 protobuf varint"""
    result = 0
    shift = 0
    i = 0

    while i < len(data):
        byte = data[i]
        i += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7

    return result, i

if __name__ == "__main__":
    import zmq
    import time

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect('tcp://localhost:5558')
    socket.setsockopt_string(zmq.SUBSCRIBE, 'md.')

    print('Listening for OKX market data...')
    count = 0
    start = time.time()

    while time.time() - start < 10:
        if socket.poll(1000):
            topic = socket.recv_string()
            data_bytes = socket.recv()

            try:
                md = decode_market_data(data_bytes)
                count += 1
                print(f"[{count}] {md.get('symbol', 'N/A')}: ${md.get('last_price', 0):.2f} (exchange: {md.get('exchange', 'N/A')})")

                if count >= 5:
                    break
            except Exception as e:
                print(f"Error decoding: {e}")

    print(f"\n✅ Received {count} OKX market data messages")
    socket.close()
    context.term()
