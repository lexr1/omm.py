from .HidppConstants import *
import struct, io
from .utils import crc16_ccitt, pretty_list
from .HidppMacro import Macro

class Profile:
    def __init__(self, x8100):
        self._report_rate = 0
        self.x8100 = x8100
        self.num_pages = x8100.num_pages if x8100 else 16

    def load_profile_bin(self, data):
        file = io.BytesIO(data)
        self._report_rate, self.dpi_default, self.dpi_shift = struct.unpack('BBB', file.read(3))
        self.dpi_list = []
        for _ in range(5):
            #little endian 2 bytes short
            self.dpi_list.append(struct.unpack('<H', file.read(2))[0])
        #finished at index 13, save next 19 bytes to 32
        self.color = file.read(3).hex()
        self.chunk1 = file.read(32-file.tell())

        #64 bytes(max 16 buttons) total, end at 32+64=96. save the rest as padding
        self.buttons = []
        for _ in range(self.x8100.num_buttons):
            self.buttons.append(file.read(4).hex())
        self.buttons_padding = file.read(96-file.tell())
        
        #96+64=160
        self.buttons_gshift = []        
        for _ in range(self.x8100.num_gbuttons):
            self.buttons_gshift.append(file.read(4).hex())
        self.buttons_gshift_padding = file.read(160-file.tell())

        #read 48 bytes as profile name
        self.profile_name = str(file.read(48).decode('utf-16'))
        #now at 160+48 = 208
        #read rgb info 11 bytes each
        #4 rgb zones(?)
        self.rgb = []
        for _ in range(0, 4):
            self.rgb.append(file.read(11))
        #at 208+44 = 252
        #read till the end - 2
        self.chunk2 = file.read(self.x8100.page_size - 2 - file.tell())
        #read last 2 bytes as checksum 
        self.checksum = struct.unpack('>H', file.read(2))[0]
        return
    
    def _rgb_to_json(self, data):
        try:
            mode = (RGBMode)(data[0]).name
        except:
            mode = 'unknown'

        color = '0x' + data[1:4].hex()
        mode_params = data[4:]
        ret = {}
        ret['mode'] = mode
        duration = 0
        brightness = 0        
        if mode in (RGBMode.off.name, RGBMode.on.name):
            pass
        elif mode == RGBMode.cycling.name:
            duration = struct.unpack('>H', mode_params[2:4])[0]
            brightness = mode_params[4]
        elif mode == RGBMode.breathing.name:
            duration = struct.unpack('>H', mode_params[0:2])[0]
            brightness = mode_params[3]
        else:
            ret['bytes'] = data.decode('all-escapes')
        
        if 'bytes' not in ret:
            ret['color'] = color
            ret['duration'] = duration
            ret['brightness'] = brightness
        return ret
    
    def _rgb_from_json(self, j):
        ret = bytearray()

        if j['mode'] in RGBMode:
            ret.append(RGBMode[j['mode']])
        elif j['mode'] == 'unknown':
            ret += j['bytes'].encode('all-escapes')
            assert len(ret) == 11, f'wrong rgb data size! {ret} {j}'
            return ret
        else:
            raise Exception(f'invalid color mode: {j['mode']}')

        rgb  = int(j['color'], 16) if 'color' in j else 0
        color = struct.pack('>I', rgb)
        duration = min(max(j['duration'],50), 60000)
        brightness = min(max(j['brightness'],0), 100)
        if j['mode'] == RGBMode.off.name:
            ret += bytearray(10)
        elif j['mode'] == RGBMode.on.name:
            ret += color[1:]
            ret += bytearray(7)
        elif j['mode'] == RGBMode.cycling.name:
            ret += bytearray(5)
            ret += struct.pack('>H', duration)
            ret.append(brightness)
            ret += bytearray(2)
        elif j['mode'] == RGBMode.breathing.name:
            ret += color[1:]
            ret += struct.pack('>H', duration)
            ret.append(0)
            ret.append(brightness)
            ret += bytearray(3)
        else:
            raise Exception('wrong rgb data!')
        assert len(ret) == 11, f'wrong rgb data size! {ret} {j}'
        return ret
    
    def _keymap_to_json(self, keystr : str):
        keyval = int(keystr, 16)
        ret = {}
        if keyval in MouseButton:
            ret['action'] = 'button'
            ret['value'] = (MouseButton)(keyval).name
        elif keystr.startswith('8002'):
            flag = keyval & 0xff00
            key = keyval & 0xff
            out = []
            ret['action'] = 'key'
            for m in Modifier:
                if flag & m.value:
                    out.append(m.name)
            ret['modifier'] = '+'.join(out)
            ret['value'] = (KeyCode)(key).name if key in KeyCode else ''
        elif keystr.startswith('00'):
            ret['action'] = 'macro'
            ret['bytes'] = struct.pack('>I', keyval).hex()            
            data = Macro.read_macro_bytes(self.x8100, keyval)
            ret['value'] = Macro.macro_bin_to_text(data)
        else:
            ret['action'] = 'unknown'
            ret['bytes'] = struct.pack('>I', keyval).decode('all-escapes')
        return ret


    def _keymap_from_json(self, j):
        if j['action'] == 'unknown':
            return j['bytes'].encode('all-escapes')
        elif j['action'] == 'button':
            return struct.pack('>I', MouseButton[j['value']])
        elif j['action'] == 'key':
            flag  = 0
            if 'modifier' in j:
                for m in [x.strip() for x in j['modifier'].replace(',', '+').split('+') if x.strip()]:
                    assert m in Modifier, f'wrong modifier key: {m}'
                    flag = flag | Modifier[m]
            key = KeyCode[j['value']] if j['value'] in KeyCode else 0
            return struct.pack('>I', 0x80020000 | flag | key)
        elif j['action'] == 'macro':
            data = Macro.macro_bin_from_text(j['value'])
            return data
        print(j)
        raise Exception('error handling keymap')


    @property        
    def report_rate(self):
        """get report rate in hz from raw byte
            regular:
            rate_1 = 1000
            rate_2 = 500
            rate_4 = 250
            rate_8 = 125 
            extended:
            [125, 250, 500, 1000, 2000, 4000, 8000]

        Returns:
            int: report rate in hz
        """
        if self.x8100.extended_report_rate:
            return [125, 250, 500, 1000, 2000, 4000, 8000][self._report_rate]
        else:
            assert self._report_rate in [1,2,4,8], f'wrong report rate byte f{self._report_rate}'
            return int(1000/self._report_rate)
    
    @report_rate.setter
    def report_rate(self, val):
        if self.x8100.extended_report_rate:
            rates = [125, 250, 500, 1000, 2000, 4000, 8000]
            assert val in rates, f'invalid report rate: {val}' 
            self._report_rate = rates.index(val)
        else:
            assert val in [1000, 500, 250, 125], f'invalid report rate: {val}' 
            self._report_rate = int(1000/val)
    
    def profile_to_json(self):
        ret = {}
        ret['profile_name'] = self.profile_name.rstrip('\u0000')
        if self.x8100.extended_report_rate:
            ret['extended_report_rate'] = self.report_rate
        else:
            ret['report_rate'] = self.report_rate
        ret['dpi_default'] = self.dpi_default
        ret['dpi_shift'] = self.dpi_shift
        ret['dpi_list'] = self.dpi_list
        ret['color'] = '0x' + self.color
        ret['chunk1'] = self.chunk1.decode('all-escapes')

        ret['buttons'] = []
        for x in self.buttons:
            ret['buttons'].append(self._keymap_to_json(x))
        ret['buttons_padding'] = self.buttons_padding.decode('all-escapes')

        ret['buttons_gshift'] = []
        for x in self.buttons_gshift:
            ret['buttons_gshift'].append(self._keymap_to_json(x)) 
        ret['buttons_gshift_padding'] = self.buttons_gshift_padding.decode('all-escapes') 

        ret['rgb'] = []
        for rgb in self.rgb:
            ret['rgb'].append(self._rgb_to_json(rgb))
        #custom_animation_index + unused bytes
        ret['chunk2'] = self.chunk2.decode('all-escapes')
        ret['checksum'] = hex(self.checksum)
        return ret
    
    def profile_bytes_from_json(self, j, profile_index):
        ret = bytearray()
        macro_rec = []
        page_map = self.x8100.page_layout
        if 'extended_report_rate' in j:
            self.report_rate = j['extended_report_rate']
        else:
            self.report_rate = j['report_rate']
        ret.append(self._report_rate)
        ret.append(j['dpi_default'])
        ret.append(j['dpi_shift'])
        for i in range(5):
            ret += struct.pack('<H', j['dpi_list'][i])
        ret += struct.pack('>I', int(j['color'], 16))[1:]
        ret += j['chunk1'].encode('all-escapes')
        assert len(j['buttons']) * 4 + len(j['buttons_padding'].encode('all-escapes')) == 64, f"wrong buttons size!"

        for buttons in ('buttons', 'buttons_gshift'):
            for x in j[buttons]:
                data = self._keymap_from_json(x)
                if isinstance(data, bytes) or isinstance(data, bytearray):
                    ret += data
                #is a macro, save position & actual macro binary, put a 4-byte filler here and calculate later                    
                elif isinstance(data, list): 
                    macro_rec.append((len(ret), data))
                    ret += b'\xFF\xFF\xFF\xFF'                    
            ret += j[buttons + '_padding'].encode('all-escapes')

        ret += (j['profile_name'].encode('utf-16le')+b'\x00'*48)[:48]
        for rgb in j['rgb']:
            ret += self._rgb_from_json(rgb)
        ret += j['chunk2'].encode('all-escapes')
        ret += struct.pack('>H', crc16_ccitt(ret))
        ret = [ret]

        #now combine macro and update ret[0].
        pos = 0        

        #calculated page map, allow manual override.
        idx = 1
        page = bytearray(b'\xFF'*256)
        size = self.x8100.page_size
        for macro in macro_rec:
            data = macro[1] #array of ops
            ret[0][macro[0]:macro[0]+4] = bytearray([0, page_map[profile_index][idx], 0, pos])
            #read data every 3 bytes
            while data:
                op_bin = data.pop(0)
                if pos + len(op_bin) <= size - 11:
                    page[pos:pos+len(op_bin)] = op_bin
                    pos += len(op_bin)
                else:
                    #new page
                    idx += 1
                    #bytes[pos: pos + 5] = bytearray([MacroControl.next_page, 0, page, 0, 0])
                    page[pos:pos+5] = struct.pack('>BHH', MacroControl.next_page, page_map[profile_index][idx], 0)
                    ret.append(page)
                    page = bytearray(b'\xFF'*size)           
                    pos = 0
            page[pos] = MacroControl.macro_end
            pos += 1
        ret.append(page)
        return ret
    
