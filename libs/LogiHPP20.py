import sys, os, struct
from .HidppFeatures import Feature
from .utils import pretty_list, pretty_list2
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

class LogiHPP20:
    def __init__(self, pid = 0, name = '', index_list = []):
        """init hidpp device

        Args:
            pid (int): usb pid
            name (str): partial name string
            index_list (list, optional): a list of possible connection id. 
                    0 for bluetooth, 0xFF for wired, 1-6 for receiver. Defaults to [0xFF].
        """
        assert pid > 0 or name, 'error: pid or name muse be set'
        self.debug = False
        vid = 0x046D
        self.swid = 0xF
        self.port_short = None
        self.port_long = None
        self.port_very_long = None
        self.functions = []
        self.SHORT_REGS = [0x80, 0x81]  #RAP registers: 80 set 81 get
        self.LONG_REGS = [0x82, 0x83]   #82 set 83 get
        self.product_name = ''
        list_short = []
        list_long = []
        list_very_long = []
        devs = hid.enumerate(vid = vid, pid = pid)
        #print(devs)
        for dev in devs:
            if dev['usage_page'] >= 0xFF00:
                h = hid.Device(path = dev['path'])
                data = h.get_report_descriptor()
                if len(data) > 10 and 0x85 in data:
                    if data[data.index(0x85)+1] == 0x10:
                        list_short.append((dev['path'], dev['product_id']))
                    elif data[data.index(0x85)+1] == 0x11:
                        list_long.append((dev['path'], dev['product_id']))
                    elif data[data.index(0x85)+1] == 0x12: #64bytes??
                        list_very_long.append((dev['path'], dev['product_id']))
                h.close()
        path_long, dev_name_hidpp, product_id = self.detect_device(list_long, name, index_list)
        assert list_long and path_long, 'error while opening device!'
        self.port_long = hid.Device(path=path_long)
        print(f'{dev_name_hidpp} pid 0x{product_id:04X} at 0x{self.device_index:02X}')
        #print('device info', self.device_index, dev_name_hidpp,'\n')

    def close(self):
        for p in [self.port_short, self.port_long, self.port_very_long]:
            if p is not None:
                p.close()

    def detect_device(self, long_path_list, name, _dev_index_list):
        path_long = None
        dev_name_hidpp = ''
        product_id = ''
        for path, pid in long_path_list:
            if path_long:
                break
            dev = hid.Device(path=path)
            self.port_long = dev
            is_receiver = 'receiver' in dev.product.lower()
            if not _dev_index_list:
                dev_index_list = [1,2,3,4,5,6] if is_receiver else [255,0]
            else:
                dev_index_list = _dev_index_list
            for i in dev_index_list:
                if is_receiver:
                    print(f'checking receiver 046D:{pid:04X} sub-id {i}')
                self.device_index = i            
                dev_name = self.get_device_name()
                if not dev_name:
                    continue
                #print(f'{dev_name} at {i}')
                if (name and name in dev_name) or not name:
                    path_long = path
                    dev_name_hidpp = dev_name
                    product_id = pid
                    break
            dev.close()
        return path_long, dev_name_hidpp, product_id
        
    @staticmethod
    def list_devices(pid = 0):
        devs = hid.enumerate(vid = 0x046D, pid = pid)
        sn = set()
        for dev in devs:
            if dev['serial_number'] not in sn:
                sn.add(dev['serial_number'])
                print(dev['manufacturer_string'], dev['product_string'])
                print('SN: ', dev['serial_number'])
                print(f'PID  0x{dev['product_id']:04X}\n')

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

    def ping_device(self, data, read_back = False):
        if self.port_short is not None and data[0] == 0x10 and len(data) <= 7:
            data = (data + [0]*7)[:7]
            self.port_short.write(bytes(data))
        else:
            data = (data + [0]*20)[:20]
            data[0] = 0x11
            self.port_long.write(bytes(data))
        
        #RAP w/short register, read from short
        #everything else from long
        data[0] = 0x11
        out = self.port_long.read(size = 255, timeout = 5000) if read_back else []

        if self.debug:
            print('fap ping:')
            print(pretty_list2(data))
            print(pretty_list2(out) if read_back else 'no readback')
        
        if read_back and data[:4] != list(out[:4]):
            #print(f'error r/w hid++2 {data[:4]} {out[:4]}')
            return None
        return out
    
    def find_feature_index(self, val):
        if val == 0:
            return 0
        out = self.call_feature(0, 0, list(struct.pack(">H", val)))
        if out:
            out = list(self.call_feature(0, 0, list(struct.pack(">H", val))))
            return out[4] if out[4] > 0 else -1
        else:
            return -1

    def has_feature(self, val):
        return self.find_feature_index(val) >= 0

    def call_feature(self, feature_val, func_id, params = [0], read_back = True):
        feature_idx = self.find_feature_index(feature_val)
        if feature_idx == -1:
            return None
        if isinstance(params, bytes) or isinstance(params, bytearray):
            params_arr = list(params)
        elif isinstance(params, list):
            params_arr = params
        else:
            raise Exception('wrong params')
        
        data = [0x10, self.device_index, feature_idx, func_id << 4 | self.swid] + params_arr
        return self.ping_device(data, read_back)

    def hidpp20_info(self, prop=''):
        dev = self.port_long
        if prop == 'product':
            return dev.product
        elif prop == 'serial':
            return dev.serial
        elif prop == 'protocol':
            return self.protocol()
        else:
            return f'{dev.product}\nSN: {dev.serial}\nProtocol {self.protocol()}\n'
    
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


    def get_device_name(self):
        """use feature 0005 to get device name
        """
        if not self.has_feature(Feature.device_name):
            return None
        out = self.call_feature(Feature.device_name, 0, [0])
        name_length = out[4]
        name = b''
        while len(name) < name_length:
            frag = self.call_feature(Feature.device_name, 1, [len(name)])
            if frag:
                name += frag[4:4+name_length - len(name)]
            else:
                print('error while reading name')
                return None
        return name.decode('utf-8')