**All configurations are case-sensitive and in lower case.** 

**For modifiers(Ctrl, Alt, Shift, Win) use `lctrl`, `lalt`, `lshift` `lgui` or `rctrl`, `ralt`, `rshift` `rgui`**   



### Set `action` to `button` 

assign button to standard features -- click, change dpi, media control etc..

```
      "action": "button",
      "value": "cycle_dpi"
```

all available values are in `MouseButton` section in [libs/HidppConstants.py](../libs/HidppConstants.py)



### `key` for key press

Press `F12` 

```
      "action": "key",
      "modifier": "",
      "value": "f12"
```

`Ctrl + Alt + Tab`

```
      "action": "key",
      "modifier": "lctrl+lalt",
      "value": "tab"
```

bind modifier key(s) to mouse button

```
      "action": "key",
      "modifier": "lctrl+lalt",
      "value": ""
```



### Set `action` to `macro`. 

**Each step is separated by space, make sure no space inside these commands!**

- Simple Keystrokes
  
   A leading `+` means key down, `-` for key up, and no `+-` for a single click(key down then key up).
   
   Send `Ctrl + A` (`bytes` field is for debugging and can be ignored)
   
   ```
         "action": "macro",
         "bytes": "00060000",
         "value": "+lctrl a -lctrl"
   ```
   
   or 
   
   ```
         "action": "macro",
         "value": "+lctrl -a +a -lctrl"
   ```

  

   all available values are in `Modifier` and `KeyCode` section in [libs/HidppConstants.py](../libs/HidppConstants.py)

   

### Advance Macro Control

- `sleep(x)` 
  
     Add delay between steps. x is in millisecond(ms)
     
     - Add 100ms delay:
     
     ```
     sleep(100)
     ```
     
- `btn(x)` 
  Send a mouse click.  x is in 1 to 5 for each mouse button, use `+-btn()` or `btn()`. 

  - Right click:

   ```
         "action": "macro",
         "value": "+btn(2) -btn(2)"
   or
         "action": "macro",
         "value": "btn(2)"
   ```

- `move(x,y)`
  
  Move mouse pointer to a relative position.  Unknown unit. 
  
  - Move mouse upper right
  
   ```
   move(100,100)
   ```
  
  - To set a absolute position, move the mouse to corner first:
  
   ```
   move(-2000,-2000) move(200,400)
   ```
  
- `wheel(x)` and  `wheelh(x)` 
  
  - Vertical and horizontal mouse wheel scroll. x in range -127 to +127.
  
   ```
   wheel(3)
   ```
  
- `pause()`
  
  Pause macro execution until button is release. 
  
  Usually macro is fired immediately when key is pressed. With `pause()`, any command after `pause()` runs when key is released.
  
  - "abc" will be sent immediately when button down, and "xyz" once released.
  
   ```
   a b c pause() x y z
   ```
  
  - Simulate left control key:
  
   ```
   +lctrl pause() -lctrl
   ```
  
- `repeat()`
  
  Keep looping macro from start when mouse button is pressed, and stops when released.
  
  - Send "abcabcabcabc..."  while pressing the button down. Anything after `repeat()` is ignored. 
  
   ```
   a b c repeat() x y z
   ```
  
- `loop()`
  
     Like `repeat()` but this one will create an endless loop once button down. Switching to another profile to stop.
