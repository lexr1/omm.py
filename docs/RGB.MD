The profile assigns 4 RGB configs for mouse, each for a different LED. A RGB config includes 4 fields:

```
      "mode": "on",
      "color": "0xff0000",
      "duration": 0,
      "brightness": 0
```

Mouse may have less than 4 LEDs, or don't support the feature at all. Unsupported model/zone will show all `FF` 

#### mode

valid values are:

- `off` this turns off LED
- `on` a solid color
- `breathing` a solid color with `brightness` from 0 to set brightness.
- `cycling` change  through all RGB colors.

#### color

RGB in hex format string, `"0xRRGGBB"`

#### duration

in ms(millisecond). For `breathing` and `cycling` mode, it's the duration of each cycle. Larger number means slower changes.

#### brightness

 maximum brightness in `breathing` and `cycling` mode.

 

| mode      | color                   | duration                       | brightness     |
| --------- | ----------------------- | ------------------------------ | -------------- |
| off       | '0x000000'/unused       | 0/unused                       | 0/unused       |
| on        | RGB color in hex format | 0/unused                       | 0/unused       |
| breathing | RGB color in hex format | duration of each cycle. in ms. | max brightness |
| cycling   | '0x000000'/unused       | duration of each cycle. in ms. | max brightness |