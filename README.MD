## Unofficial Logitech Onboard Memory Profile Tool

A Python script to manage Logitech's onboard memory profiles. For hid++ 2.0 mice.

### Features

- Manage onboard profiles

- Import/Export profiles in json format

- Assign mouse button to click, key or macro

- Set RGB color effect

- Toggle onboard memory mode for easy start

  

### Quick start

1. Only tested on 64bit Windows 10 and Python 3.12. For other OS compatibility see below.

2. Download the source and install requirements
   ```
   pip install -r requirements.txt
   ```
   
3. List Logitech devices
   ```
   omm.py -l
   ```
   
4. Get the necessary PID and test run
   ```
   omm.py --pid PID -p 1 --dump
   ```

   This will get the device info and display the first profile. If it goes through, most likely the mouse is supported.
   
5. Save the settings to a json file

   ```
   omm.py --pid PID -p 1 --export profile1.json
   ```

6. Edit the json file, make changes and load it back to profile 1:
   ```
   omm.py --pid PID -p 1 --import profile1.json
   ```
   
   

run `omm.py --help` for more command line options.



### json profile options

Most fields are self-explanatory. `buttons` and `buttons_gshift` are used to assign mouse buttons and documented in [docs/BUTTON_MAPS.MD](docs/BUTTON_MAPS.MD). For `rgb`, check [docs/RGB.MD](docs/RGB.MD).



### Known issue

1. The profile and macro formats are limited to what's in the G502, but should be compatible with many other models.
2. Wireless support:
   
   Logitech's wireless receiver works slightly different and will appear as a different PID than in wired mode. This project is based on unifying receiver as I have no wireless gaming mouse. Try `--receiver` option, or program under wired mode. 
   Bluetooth is also only partially tested on an office mouse.
3. Lightsync mice have more color options. I don't have any so it's limited to G502's, and may not work with Lightsync.
4. Untested for polling rate over 1000.



### Linux and macOS Support

Untested. 

The code uses [hidapi](https://github.com/libusb/hidapi) to communicate with the mouse. As hidapi is cross-platform, it *should* work once hidapi(>= 0.14.0) is installed.



### Tested models

| PID  | Model             |Note|
| ---- | ----------------- |------|
| C07D | G502 Proteus Core ||
| C08B | G502 Hero         ||



### Disclaimer

This is a personal project and no guarantee to work. Use it at your own risk especially on untested models.



### Credit

- [hidapi](https://github.com/libusb/hidapi)
- [libratbag](https://github.com/libratbag/libratbag)
- [Solaar](https://github.com/pwr-Solaar/Solaar)
- [G403 HID](https://github.com/clovervidia/G403HID)
- [hidpp](https://github.com/cvuchener/hidpp)
- [Linux Kernel](https://github.com/torvalds/linux/blob/master/drivers/hid/hid-logitech-hidpp.c)

