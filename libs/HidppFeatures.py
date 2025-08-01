from enum import IntEnum

            
class Feature(IntEnum):
    root = 0
    device_name = 0x0005
    switch_host = 0x1814
    host_info = 0x1815
    hires_wheel = 0x2121
    adjustable_dpi = 0x2201
    pointer_speed = 0x2205
    report_rate = 0x8060
    extended_report_rate = 0x8061    
    color_led_control = 0x8070
    onboard_profile = 0x8100
