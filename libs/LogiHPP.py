import sys, os, struct

if sys.platform == 'win32':
    if struct.calcsize("P") * 8 == 64:
        os.add_dll_directory(os.path.dirname(os.path.abspath(__file__)) + '/x64')
    else:
        os.add_dll_directory(os.path.dirname(os.path.abspath(__file__)) + '/x86')

#hid.dll binary from
#https://github.com/libusb/hidapi

#py hid binding:
#https://github.com/apmorton/pyhidapi
import hid

class LogiHPP:
    def __init__(self, pid, index_list = [0xFF]):
        """init hidpp device

        Args:
            pid (int): usb pid
            index_list (list, optional): a list of possible connection id. 
                    0 for bluetooth, 0xFF for wired, 1-6 for receiver. Defaults to [0xFF].
        """
        self.debug = False
        vid = 0x046D
        self.swid = 0xF
        self.port_short = None
        self.port_long = None
        self.port_very_long = None
        self.functions = []
        self.SHORT_REGS = [0x80, 0x81]  #RAP registers: 80 set 81 get
        self.LONG_REGS = [0x82, 0x83]   #82 set 83 get

        devs = hid.enumerate(vid = vid, pid = pid)
        #print(devs)
        for dev in devs:
            if dev['usage_page'] >= 0xFF00:
                h = hid.Device(path = dev['path'])
                data = h.get_report_descriptor()
                if len(data) > 10 and 0x85 in data:
                    if data[data.index(0x85)+1] == 0x10:
                        self.port_short = h
                    elif data[data.index(0x85)+1] == 0x11:
                        self.port_long = h
                    elif data[data.index(0x85)+1] == 0x12: #64bytes??
                        self.port_very_long = h
                    else:
                        h.close()
        assert self.port_long is not None, 'Error while opening device!'
        if self.port_short and self.port_long:
            assert self.port_short.serial == self.port_long.serial, 'SN mismatch!'
        self.device_index = self.detect_device_index(index_list)
        print('device connection index:', self.device_index, '\n')


    def close(self):
        for p in [self.port_short, self.port_long, self.port_very_long]:
            if p is not None:
                p.close()

    @staticmethod
    def list_devices(pid = 0):
        devs = hid.enumerate(vid = 0x046D, pid = pid)
        sn = set()
        for dev in devs:
            if dev['serial_number'] not in sn:
                sn.add(dev['serial_number'])
                print(dev['manufacturer_string'], dev['product_string'])
                print('SN: ', dev['serial_number'])
                print('PID ', "0x{:04X}\n".format(dev['product_id']))

    @staticmethod
    def is_receiver(pid):
        """detect if a usb dev is receiver by checking product name string.

        Args:
            pid (int): usb pic

        Returns:
            bool: True if "receiver" in product name
        """
        devs = hid.enumerate(vid = 0x046D, pid = pid)
        for dev in devs:
            if "receiver" in dev['product_string'].lower():
                return True
        return False

    def get_feature_list(self):
        data = list(self.call_feature(1, 0))
        features = []
        for function_index in range(0, data[4]+1):
            out = list(self.call_feature(1, 1, [function_index]))
            features.append(out[4]<< 8 | out[5])
        return features
            
    def ping_device(self, data, is_rap_ping = False):
        if self.port_short is not None and data[0] == 0x10 and len(data) <= 7:
            data = (data + [0]*7)[:7]
            self.port_short.write(bytes(data))
        else:
            data = (data + [0]*20)[:20]
            data[0] = 0x11
            self.port_long.write(bytes(data))
        
        #RAP w/short register, read from short
        #everything else from long
        if is_rap_ping and data[2] in self.SHORT_REGS:
            out = self.port_short.read(size = 255, timeout = 5000)
        else:
            out = self.port_long.read(size = 255, timeout = 5000)

        if self.debug:
            print('rap' if is_rap_ping else 'fap', 'ping:', list(map(hex, data)), list(map(hex, out)))
        return out            
    
    def find_feature_index(self, val):
        if val == 0:
            return 0
        out = list(self.call_feature(0, 0, list(struct.pack(">H", val))))
        return out[4] if out[4] > 0 else -1

    def has_feature(self, val):
        return self.find_feature_index(val) >= 0
    
    def detect_device_index(self, index_list):
        found_dev = False
        feature_val = 1
        for i in index_list:
            self.device_index = i
            out = list(self.call_feature(feature_val, 0))
            if self.debug:
                print(i, out)
            if out[2] == feature_val:
                return i
        assert found_dev, 'device not found!'
        print(f'device found!')

    def call_feature(self, feature_val, func_id, params = [0]):
        feature_idx = self.find_feature_index(feature_val)
        assert feature_idx != -1, f'Unsupported feature {feature_val:#06x}'
        if isinstance(params, bytes) or isinstance(params, bytearray):
            params_arr = list(params)
        elif isinstance(params, list):
            params_arr = params
        else:
            raise Exception('wrong params')
        
        data = [0x10, self.device_index, feature_idx, func_id << 4 | self.swid] + params_arr
        return self.ping_device(data)

    def hidpp20_info(self, prop=''):
        dev = self.port_long
        if prop == 'product':
            return dev.product
        elif prop == 'serial':
            return dev.serial
        elif prop == 'protocol':
            return self.protocol
        else:
            return f'{dev.product}\nSN: {dev.serial}\nProtocol {self.protocol}\n'
        
    @property
    def protocol(self):
        data = list(self.call_feature(0, 1))
        if data[4] == 4:
            desc = 'hid++ 2.0'
        elif data[4] == 2:
            desc = 'hid++ 2.0 - legacy'
        elif data[4] == 0x8f:
            desc = 'hid++ 1.0'
        else:
            desc = 'unknown'
        return f'{str(data[4])}.{str(data[5])} {desc}'

