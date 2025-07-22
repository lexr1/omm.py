from .HidppConstants import *
import struct, re

    
class Macro:

    @staticmethod
    def get_op_length(op_code):
        b = (op_code & 0xE0) >> 4
        if b == 0x0:
            return 1
        elif b == 0x2:
            return 2
        elif b == 0x4:
            return 3
        elif b == 0x6:
            return 5
        else:
            return 1

    @staticmethod
    def read_macro_bytes(x8100, offset):
        """read macro from device with offset

        Args:
            x8100 (LogiX8100): the x8100 interface
            offset (int): offset, '>HH' to page and pos

        Returns:
            bytearray: macro bin. from offset
        """
        page, pos = struct.unpack('>HH', offset.to_bytes(4))
        assert page in range(x8100.num_profiles+1,x8100.num_pages+1) and pos < x8100.page_size - 10, f'wrong offset: {page}, {pos}'
        data = x8100.read_memory_page(page, False)[pos:]
        ret = []
        pos = 0
        while True:
            op_code = data[pos]
            assert op_code in MacroControl, f'wrong macro option! {op_code}'
            if op_code == MacroControl.next_page:
                _, page, pos = struct.unpack('>BHH', data[pos:pos+5])
                assert page in range(x8100.num_profiles+1,x8100.num_pages+1) and pos < x8100.page_size - 10, f'wrong offset: {page}, {pos}'
                data = x8100.read_memory_page(page, False)[pos:]            
            elif op_code == MacroControl.macro_end:
                break
            else:
                step = Macro.get_op_length(op_code)
                ret.append(data[pos : pos+step])
                pos += step
        return ret
    
    @staticmethod
    def macro_bin_to_text(data_List):
        """translate binary to text format macro

        Args:
            data_List (list[bytearray]): macro bytes

        Returns:
            str: a comma seperated string for each macro steps
        """
        ret = []
        for data in data_List:
            op = data[0]
            if op in [MacroControl.key_down, MacroControl.key_up]:
                val = struct.unpack('>H', data[1:])[0]
                if val in Modifier:  #single modifer key
                    key = Modifier(val).name
                elif val in KeyCode:
                    key = KeyCode(val).name
                else:
                    raise Exception(f'wrong macro control! {data}')
                if op == MacroControl.key_down:
                    ret.append('+' + key)
                else:
                    ret.append('-' + key)
            elif op == MacroControl.sleep:
                val = struct.unpack('>H', data[1:])[0]
                ret.append(f'{MacroControl(op).name}({val})')
            elif op in [MacroControl.wheel, MacroControl.wheelh]:
                val = struct.unpack('b', data[1:])[0]
                ret.append(f'{MacroControl(op).name}({val})')
            elif op == MacroControl.move:
                y, x = struct.unpack('>hh', data[1:])
                ret.append(f'{MacroControl(op).name}({x},{y})')
            elif op in [MacroControl.pause, MacroControl.repeat, MacroControl.loop]:
                ret.append(f'{MacroControl(op).name}()')
                #break # skip everything after repeat/repeat??
            elif op in [MacroControl.btn_down, MacroControl.btn_up]:
                val = struct.unpack('>H', data[1:])[0]
                btns = []
                for i in range(0,5):  # btn 1 2 3 4 5
                    if val & (1 << i):
                        btns.append(str(i+1))
                opname = f'btn({",".join(btns)})'
                if op == MacroControl.btn_down:
                    ret.append('+' + opname)
                else:
                    ret.append('-' + opname)
            if len(ret) > 1 and ret[-1].startswith('-') and ret[-2].startswith('+') and ret[-1][1:] == ret[-2][1:]:
                ret[-2] = ret[-2][1:]
                ret.pop()
        return ' '.join(ret)


    @staticmethod
    def macro_bin_from_text(text):
        """translate text to binary

        Args:
            text (str): macro steps

        Returns:
            list[bytearray]: binary
        """
        ops =  [x.strip() for x in text.lower().split(' ') if x.strip()]
        ret = []
        key_list = []

        for op in ops:
            bytes = bytearray()
            if '(' not in op:
                k = op[1:] if op.startswith(('+', '-')) else op
                assert k in Modifier or k in KeyCode, f'wrong key in macro! {op}'
                key = Modifier[k] if k in Modifier else KeyCode[k]

                if op.startswith(('+', '-')):
                    if op.startswith('+'):
                        opcode = MacroControl.key_down
                        assert key.name not in key_list, f'wrong macro: {key.name} is already down!'
                        key_list.append(key.name)
                    else:
                        opcode = MacroControl.key_up
                        assert key.name in key_list, f'wrong macro: {key.name} is not down before releasing!'
                        key_list.remove(key.name)
                    bytes = struct.pack('>BH', opcode, key.value)
                else:
                    bytes = struct.pack('>BHBH', MacroControl.key_down, key.value, MacroControl.key_up, key.value)
            elif op.startswith(('wheel(', 'wheelh(')):  #scroll wheel 2 bytes
                opcode = MacroControl[op.split('(')[0]]
                val = re.findall(r'-?\d+', op)[0]
                val = int(val)
                bytes = bytearray(struct.pack('Bb', opcode, val))
            elif op.startswith('move('):  #move mouse to relative x,y 5 bytes
                opcode = MacroControl['move']
                p = re.findall(r'-?\d+', op)
                #x y is reversed?? move(y,x)?
                y = int(p[0])
                x = int(p[1])
                bytes = bytearray(struct.pack('>Bhh', MacroControl.move, x, y))
            elif op.startswith('sleep('): #sleep xxms. 3 bytes
                opcode = MacroControl['sleep']
                val = int(re.findall(r'\d+', op)[0])
                bytes = bytearray(struct.pack('>BH', MacroControl.sleep, val))
            elif '()' in op:
                bytes = bytearray([MacroControl[op[:-2]]])
            elif op.startswith(('+btn', '-btn', 'btn')): 
                btns = [int(x) for x in re.findall(r'\d+', op)]
                val = 0
                for btn in btns:
                    if btn <= 5: 
                        val = val | ( 1<< (btn-1))
                if op.startswith('+btn'):
                    opcode = MacroControl.btn_down
                    bytes = bytearray(struct.pack('>BH',MacroControl.btn_down, val))
                elif op.startswith('-btn'):
                    opcode = MacroControl.btn_up
                    bytes = bytearray(struct.pack('>BH',MacroControl.btn_up, val))
                else:
                    bytes = bytearray(struct.pack('>BHBH',MacroControl.btn_down, val, MacroControl.btn_up, val))
            assert len(bytes), f'error! unknow macro {op}'
            ret.append(bytes)
        assert len(key_list) == 0, f'some keys are not released! {' '.join(key_list)}'
        return ret