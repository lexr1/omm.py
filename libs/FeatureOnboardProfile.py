import struct
from .HidppConstants import *
from .utils import crc16_ccitt, pretty_list
from .HidppProfile import Profile
from .HidppFeatures import *


#https://github.com/libratbag/libratbag/blob/master/src/hidpp20.c
class FeatureOnboardProfile:
    """interface to feature 0x8100, onboard profile
    """
    def __init__(self, dev):
        self.dev = dev
        assert self.dev.has_feature(Feature.onboard_profile), 'unsupported device: no onboard profiles!'
        data = self.dev.call_feature(Feature.onboard_profile, 0, [0])
        #sample output on G502
        #0x11 0xff 0x0c 0x0f 0x01 0x02 0x01 0x05 0x05 0x0b 0x10 0x01 0x00 0x0a 0x01 0x00 0x00 0x00 0x00 0x00
        memory_layout, self.profile_format, macro_format, self.num_profiles, \
            num_profiles_oob, self.num_buttons, self.num_pages, self.page_size, gshift = \
            struct.unpack('>BBBBBBBHB', data[4:14])
        assert memory_layout == 1, f'unsupported device! {memory_layout}'
        assert self.profile_format <= 5, f'unsupported profile format {self.profile_format}' 
        assert macro_format == 1, f'unsupported macro format {macro_format}'
        assert self.num_buttons <= 16, f'too many buttons! {self.num_buttons}'
        assert self.page_size in [256, 1024], f'unsupported page size, should be 256 or 1024: {self.page_size}'
        self.num_gbuttons = self.num_buttons if gshift & 0x3 == 0x2 else 0
        self.extended_report_rate = self.dev.has_feature(Feature.extended_report_rate)
        self.profile_list = [{}]
        data = self.read_memory_page(0)
        for i in range(self.num_profiles):
            rom, page, vis = struct.unpack('BBB', data[i*4:i*4+3])
            if rom == 0xFF:
                print(f'profile {i+1} is disabled, run "omm.py -p {i+1} --enable"')
                page = -1
            elif rom == 0x01:
                print(f'profile {i+1} is on ROM')
                page = -1
            else:
                assert rom == 0 and page == i + 1 , f'error memory layout at profile {i+1} {hex(page)}'
            self.profile_list.append({'page':page, 'vis': vis == 1})
        self.page_layout = self.calc_page_layout()

    def close(self):
        self.dev.close()
        
    def info_display(self):
        print(self.dev.hidpp20_info())        
        if not self.onboard_mode:
            print('onboard mode disabled! run "omm.py --onboard on" first!')
            return False
        print('number of buttons:  ', self.num_buttons)
        print('number of pages:    ', self.num_pages)
        print('page size:          ', self.page_size)
        print('profile format:     ', self.profile_format)

        current_profile = self.current_profile
        status = []
        for idx, p in enumerate(self.profile_list[1:]):
            status.append(f"{idx+1}{'*' if idx+1 == current_profile else ''}{'x' if p['page'] > 0xFF else ''}{'-' if not p['vis'] else ''}")
            #print(f'profile {idx+1}:', 'enabled' if p['page'] > 0 else 'disabled', 'visible' if p['vis'] else 'hidden')
        print('profile status:     ', '  '.join(status), '\n')
        return True  

    def read_memory_page(self, page, verify = True):
        """read memory page from device. 

        Args:
            page (int): page index
            verify (bool, optional): check checksum for page 0 and all profile pages. don't verify for macro pages.

        Returns:
            bytearray: content out
        """
        ret = bytearray()
        for i in range(0, int(self.page_size/16)):
            ret += self.dev.call_feature(Feature.onboard_profile, 5, list(struct.pack('>HH', page, i*16)))[4:]  #[page >> 8, page & 0xFF, 0,  i*16, 0x10])[4:])
        if verify:
            assert crc16_ccitt(ret[:-2]) == struct.unpack('>H', ret[-2:])[0], f'checksum error while reading memory page: {page}'
        return bytearray(ret)
    
    def write_memory_page(self, page, data, verify = True):
        """write memory page with data

        Args:
            page (int): page index
            data (bytesarray): data to write.
            verify (bool, optional): auto calculate checksum and update last 2 bytes. for page 0 and all profile pages. don't verify for macro pages. 
        """
        assert len(data) == self.page_size, 'wrong data size!'
        if verify:
            checksum = crc16_ccitt(data[:-2])
            data = data[:-2] + struct.pack('>H', checksum)
        #call 06 to start, then 07 writing in loop, 08 to finish
        self.dev.call_feature(Feature.onboard_profile, 6, list(struct.pack('>HHH', page, 0, len(data))))
        for i in range(int(len(data)/16)):
            self.dev.call_feature(Feature.onboard_profile, 7, list(data[i*16:i*16+16]))
        self.dev.call_feature(Feature.onboard_profile, 8)
        return

    def onboard_profile_to_bin(self):
        assert self.profile_list[self.dest]['page'] == self.dest, f'error profile {self.dest} at page {self.profile_list[self.dest]['page']}'
        return self.read_memory_page(self.page_layout[self.dest][0])
        
    def onboard_profile_save(self, data):
        assert self.profile_list[self.dest]['page'] == self.dest, f'error profile {self.dest} at page {self.profile_list[self.dest]['page']}'
        print('save profile', self.dest)
        #write to profile page and macro page
        self.write_memory_page(self.page_layout[self.dest][0], data[0])
        for i, macro in enumerate(data[1:], 1):
            self.write_memory_page(self.page_layout[self.dest][i] , macro, False)

    def profile_bin_from_json(self, j):
        return Profile(self).profile_bytes_from_json(j, self.dest)

    def profile_bin_to_json(self, data):
        p = Profile(self)
        p.load_profile_bin(data)
        return p.profile_to_json()
    
    def calc_page_layout(self):
        # irregular page layout override
        # return [[], [1,6,7],[2,10,11,12,15],[3,10,11],[4,12,13],[5,14,15]]

        # default: 2 pages per profile for macro (16-6)/5
        ret = [[]]
        pages = int((self.num_pages - self.num_profiles - 1) / self.num_profiles)
        for i in range(self.num_profiles):
            arr = [self.profile_list[i+1]['page']]
            arr += list(range(self.num_profiles + i*pages+1, self.num_profiles + i*pages+pages+1))
            ret.append(arr)
        return ret
    
    @property
    def current_profile(self):
        data = self.dev.call_feature(Feature.onboard_profile, 4, [0])
        return data[5]
    
    @current_profile.setter
    def current_profile(self, profile_index):
        assert profile_index in range(1, self.num_profiles+1), f'wrong profile index! {profile_index}'        
        curr = self.current_profile
        if profile_index == curr:
            print(f'alreay on profile {profile_index}')
            return
        #check visibility
        if not self.profile_visibility:
            print(f'enable profile {profile_index} visible')
            self.profile_visibility = True
        self.dev.call_feature(Feature.onboard_profile, 3, [0, profile_index, 0])
        print(f'switch profile: {curr}=>{profile_index}')

    @property
    def onboard_mode(self):
        data = self.dev.call_feature(Feature.onboard_profile, 2)
        return data[4] == 1
    
    @onboard_mode.setter
    def onboard_mode(self, mode = True):
        self.dev.call_feature(Feature.onboard_profile, 1, [1 if mode else 2])

    @property
    def dest_profile(self):
        """return current working profile index

        Returns:
            int: self.dest
        """
        return self.dest

    @dest_profile.setter
    def dest_profile(self, profile_index):
        """set working profile index for all future function

        Args:
            profile_index (int): profile index
        """
        assert profile_index in range(1, self.num_profiles+1), f'error wrong profile index! {profile_index}'     
        #assert self.profile_list[profile_index]['page'] > 0, f'profile {profile_index} is disabled!'
        self.dest = profile_index
        
    @property
    def profile_enabled(self):
        return self.profile_list[self.dest]['page'] > 0

    @profile_enabled.setter
    def profile_enabled(self, enabled):
        """ enable or disable profile
            when enabled, also make it visible
            when disable, set all 4 bytes to 0xFF
            Note: this assumes profile 1 in memory page 1, 2 in page 2, etc..
            
        Args:
            enabled (bool): enable/disable a profile
        """
        data = self.read_memory_page(0, False)
        val = 1 if enabled else 0
        if self.current_profile == self.dest:
            if val:
                print(f'current profile: {self.dest} is already enabled')
            else:
                print(f'error: can\'t disable current profile: {self.dest}')
            return
        
        print(f"{'enable' if val == 1 else 'disable'} profile {self.dest}")    
        if val == 1:
            data[(self.dest-1)*4:self.dest*4] = bytearray([0, self.dest, 1, 0])
            self.profile_list[self.dest]['page'] = self.dest
        else:
            data[(self.dest-1)*4:self.dest*4] = bytearray([0xff, 0xff, 0xff, 0xff])
            self.profile_list[self.dest]['page'] = -1
        self.write_memory_page(0, data)


    @property
    def profile_visibility(self):
        """check profile visible?

        Returns:
            bool: profile visible?
        """
        return self.profile_list[self.dest]['vis']

    @profile_visibility.setter
    def profile_visibility(self, visibility):
        """set profile visibility for self.dest

        Args:
            visibility (bool): visibility
        """
        if not self.profile_enabled:
            print(f'profile: {self.dest} is disabled, enable it first!')
            return
        val = 1 if visibility else 0
        if self.current_profile == self.dest and val == 0:
            print(f'can\'t hide current profile: {self.dest}')
            return
        if self.profile_list[self.dest]['vis'] == visibility:
            print(f'profile {self.dest} is already {'visible' if val == 1 else 'hidden'}, no need to change')
            return
        print(f"set profile {self.dest}: {'visible' if val == 1 else 'hidden'}")
        self.profile_list[self.dest]['vis'] = val
        data = self.read_memory_page(0, False)
        data[(self.dest-1)*4+2] = val
        self.write_memory_page(0, data) 