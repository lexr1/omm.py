import json, os

def pretty_json(j):
    return json.dumps(j, indent=2, ensure_ascii=False)

def save_file(filename, data):
    print(f'saving {filename}')
    try:
        if isinstance(data, str):
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(data)
        if isinstance(data, bytearray) or isinstance(data, bytes):
            with open(filename, 'wb') as f:
                f.write(data)
        return True
    except Exception as e:
        print(e)
        return False
        
def save_json_to_file(filename, j):
    save_file(filename, pretty_json(j))

def load_from_file(filename, filetype):
    assert os.path.exists(filename), f'error opening {filename}'    
    if filetype == 'json':
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    if filetype == 'bin':
        with open(filename, 'rb') as f:
            return f.read()
    if filetype == 'string':
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
        
def load_bin_from_file(filename):
    if (os.path.exists(filename)):
        with open(filename, 'rb') as f:
            return f.read()
    else:
        print('error while loading', filename)
        return b''

def pretty_print(data):
    if isinstance(data, bytearray):
        data = list(data)
    print(" ".join("0x{:02x}".format(x) for x in data))

#https://stackoverflow.com/a/30357446/5007748
def crc16_ccitt(data):
    crc = 0xFFFF
    data = bytearray(data)
    msb = crc >> 8
    lsb = crc & 0xFF
    for c in data:
        x = c ^ msb
        x ^= (x >> 4)
        msb = (lsb ^ (x >> 3) ^ (x << 4)) & 0xFF
        lsb = (x ^ (x << 5)) & 0xFF
    return (msb << 8) + lsb

def str2int(v):
    if v.lower() in ['yes', 'true', 'y', '1', 'on']:
        return 1
    elif v.lower() in ['no', 'false', 'n', '0', 'off']:
        return 0
    else:
        return -1