from libs.LogiHPP import LogiHPP 
from libs.Hidpp8100 import Hidpp8100
from libs.HidppConstants import USBReceiver
from libs.utils import *
import argparse, os


if __name__ == "__main__":
    dev_pid = '0xc08b' #G502 Hero

    parser = argparse.ArgumentParser(description='Logitech Onboard Memory Manager Python')
    parser.add_argument('-l', '--list', help='list all Logitech devices',  action='store_true', required = False, default=False)    
    parser.add_argument('-p', '--profile', help='profile index, starting from 1', type=int, required=False, default=1)
    parser.add_argument('--pid', help='usb mouse pid', type=str, required=False, default=dev_pid)
    parser.add_argument('--receiver', help='mouse is connected through usb receiver', action='store_true', required = False, default=False)
    parser.add_argument('--page', help='for debugout option, set dest. page', type=int, required = False, default=255)
    parser.add_argument('--switch', help='switch to profile',  action='store_true', required = False, default=False)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--onboard', help='set onboard mode', type=str2int, required = False, default='')
    group.add_argument('--dump', help='print profile info', action='store_true', required = False, default = False)
    group.add_argument('--export', help='export profile settings to json file', type=str, required = False, default='')
    group.add_argument('--import', help='import profile settings from json file', type=str, required = False, default='')
    group.add_argument('--decode', help='convert saved binary to json', type=str, required = False, default='')
    group.add_argument('--debugout', help='save raw memory page(s) to "debug" folder', type=str, required = False, default='')
    group.add_argument('--debugin', help='load raw memory page', type=str, required = False, default='')
    group.add_argument('--visible', help='set profile visibility', type=str2int, required = False, default='')
    group.add_argument('--enable', help='enable profile',  action='store_true', required = False, default=False)

    args = vars(parser.parse_args())
    profile_index = args['profile']
    dump_mode = args['dump']
    list_mode = args['list']
    pid = int(args['pid'], 16)
    do_switch = args['switch']
    toggle_onboard = args['onboard']
    toggle_vis = args['visible']
    enable_mode = args['enable']
    export_json = args['export']
    import_json = args['import']
    decode_bin = args['decode']
    debugout = args['debugout']
    debugin = args['debugin']
    page = args['page']

    is_receiver = args['receiver']
    
    if list_mode:
        LogiHPP.list_devices()
        exit()
        
    if LogiHPP.is_receiver(pid) or is_receiver:
        #receiver "sub-index", 1-6 for each paired devices
        #untested on lightspeed!!
        print('Wireless usb receiver\n')
        dev = LogiHPP(pid, [1,2,3,4,5,6])
    else:
        #0x00 for bluetooth, 0xff for wired.
        dev = LogiHPP(pid, [255, 0]) 
    
    omm = Hidpp8100(dev)

    early_exit = toggle_onboard >=0 or enable_mode or toggle_vis >= 0
    if toggle_onboard >= 0:
        omm.onboard_mode = True if toggle_onboard == 1 else False
    omm.dest_profile = profile_index
    if enable_mode:
        omm.profile_enabled = True
    elif toggle_vis >= 0:
        omm.profile_visibility = toggle_vis == 1
    if not omm.info_display():
        early_exit = True
    if early_exit:
        omm.close()
        exit()    

    assert omm.profile_enabled, f'profile {omm.dest_profile} is disabled!, run "omm.py -p {omm.dest_profile} --enable on" first!'
    if export_json:
        data = omm.onboard_profile_to_bin()
        if export_json:
            j = omm.profile_bin_to_json(data)
            print('Export settings to:', export_json)
            save_file(export_json, pretty_json(j))

    elif import_json:
        if import_json and os.path.isfile(import_json):
            j = load_from_file(import_json, 'json')
            data = omm.profile_bin_from_json(j)
            #data is an array, data[0]: profile, data[1] data[2]: macro
            omm.onboard_profile_save(data)
        if do_switch:
            omm.current_profile = omm.dest_profile
     
    elif dump_mode:
        data = omm.onboard_profile_to_bin()
        j = omm.profile_bin_to_json(data)
        print(f'Profile {omm.dest_profile}:')
        print(pretty_json(j))

    elif decode_bin:
        data = load_bin_from_file(decode_bin)
        j = omm.profile_bin_to_json(data)
        print(pretty_json(j))

    elif debugout:
        pagelist = debugout.split(',')
        for x in pagelist:
            data = omm.read_memory_page(int(x), False)
            debug_path = f'{os.path.dirname(os.path.abspath(__file__))}/debug'
            os.makedirs(debug_path, exist_ok=True)
            save_file(f'{debug_path}/page-{x}.bin', data)

    elif debugin:
        assert page < omm.num_pages, f'memory page out of bounds! use "--page" to set dest page index'
        data = load_from_file(debugin, 'bin')
        assert len(data) in [256, 1024], 'error, wrong data file!'
        r = input("Warning: write data to device without checking, continue? Y/N* ") or 'N'
        if r.lower() == 'y':
            omm.write_memory_page(page, data, False)

    elif do_switch:
        omm.current_profile = omm.dest_profile

    omm.close()
    