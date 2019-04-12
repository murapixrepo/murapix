# murapix

The Murapix package is meant to be used as a wrapper to make pygame applications
that will be shown on a murapix hardware. A "murapix hardware" is defined as
, for now, a raspberry pi set-up following [hzeller rpi-rgb-led-matrix][hzeller]
recommandations to output images on a set of LED matrices controlled by 
the pi GPIO.

A demo version is available to make it run on a computer running linux.


## Installing

You need a linux system, or better a raspberry pi, to run it. Although 
the objective is to output a pygame-coded game or animation on a set of
LED panels, there is a demo mode. So you can use it on your laptop or
desktop!

### Cloning

First clone the package recursively

`git clone --recurse-submodules -j4 https://hyamanieu@bitbucket.org/murapix/murapix.git`

The package contains two submodules:
 * hzeller code to control the LED panels
 * a modified node virtual gamepad that produces virtual gamepads
 served on the local network.
 

 
### Build hzeller binding

You need to build the [python3 binding][pythonbinding].


  
First, cd into the right path:

`cd murapix/matrix/bindings/python`

Then follow hzeller instructions, copied here:

```
sudo apt-get update && sudo apt-get install python3-dev python3-pillow -y
make build-python PYTHON=$(which python3)
sudo make install-python PYTHON=$(which python3)
```

We strongly advise you to [read the readme from hzeller][hzeller]!
Notably the note about disabling the sound.

If you intend to use only the demo mode, you may not need to build
the python3 binding, and you should not disable the sound.

### Build the virtual gamepad

The original node-virtual-gamepads can be found [here][jehervygamepad].

The forked version is [there][hyamanieugamepad] (mind the custom-virtual-gamepads branche).

You need to cd into the submodule path as well, then build as explained
in the readme:

```
cd murapix/custom-virtual-gamepads
npm install
```

This is meant only if your end application will need to be interactive by
using a smartphone.


### install the requirements

```
cd murapix
pip3 install  -r requirements.txt
```

Basically, you need pygame, numpy and PIL. In the future, we plan to get
round numpy by implementing ourselves the algorithms.



### Test it!

In the murapix main folder, there is an example config file as well as a
sample script.

If you have a video output, run

`python3 screen_test.py example_murapix_config.ini --demo=3`

You can change the number after `--demo=` to increase or decrease the
size of the window, it indicates the number of pixel per simulated
LED edge.

If you are running on a headless RPi, you cannot run it as demo. 
You then need to make your own .ini file [as instructed here under](#config-file). 
You can then run:

`python3 test_screen.py yourconfig.ini`

your screens should now show their number (as configured in the ini file)
 in black, and the background color of each panel should change one after
 an other.
 
![screen test](screen_test.png?raw=true "Screen test")

## How to use




### config file

The config file is meant to describe your murapix hardware, i.e. how your 
panels are laid out and how many leds they have. IMPORTANT: all panels
 must be the same! Same manufacturer, same number of LEDs.
 
the config file must always contain a 'matrix' section with the following
 variables:
 
 * mapping: several lines of coma separated values. A value must be a '.', 
    indicating an empty place, or an integer. The integers must form a 
    sequence from 1 to the total number of panels. Panel 1 is the first
    panel connected to the RPi hat, 2 the next in the chain, and so on.
 * led-rows: the number of leds per row for each panel
 * led-cols: the number of leds per column for each panel
  
 
Example (see also example_murapix_config.ini):

```
[matrix]
mapping = ., ., 1, .
		  2, 3, 4, .
		  5, 6, 7, 8
led-rows = 64
led-cols = 64
```

### coding a simple example



In general, you need to create a class holding all your game mechanics
which subclasses murapix. There are three methods you need to modify:
`self.setup()`, `self.logic_loop()`, and `self.graphics_loop()`.

`self.setup()` is run once before starting the loop. `logic_loop()` then `graphics_loop()` are run at each loop.
You can modify the fps by setting `self.fps` inside your game class.
If you want to modify how `logic_loop()` and `graphics_loop()` interact,
you can rewrite the `self.run()` method.

The surface on which you need to draw is `self.scratch`, and *nothing 
else*. The murapix package will take care of the rest.

In order to exit the loop, you need to set the variable `self.RUNNING` to
false inside your loop. It will then run the method `self.close()`.


Example 

```python
from murapix import Murapix

class Test(Murapix):
    def setup(self):
		#initialize here your sprites and the scratch surface
        pass
        
    def logic_loop(self):
		#logic code goes here.
        pass
        
        
    def graphics_loop(self):
		#graphic code goes here, modify self.scratch
        pass

```

You then need to instruct python to run the game, you can do it as follows:
```python
def main():
    Test().run()
  
if __name__ == '__main__':
    main()


```

You can now run in your terminal `python3 test.py yourconfig.ini`


`test_screen.py` is also a good basic example of how to use the murapix 
package.

### some more advanced stuff.

There are several helper functions, like `get_largest_rect_add` which  
gives the position of the largest rectangle you can form with your murapix
setup.

Here is the list:
`get_largest_rect`, `get_largest_rect_add`, `get_deadzone_addresses`, `get_panel_adresses`

You can read the doc by calling the function inside `help()`.

If you need to serve a gamepad using the virtual gamepad, you need to set
the variable `self.gamepad` to the path of your SVG by rewritting the
`__init__` method, example:
```
class Subclass(Murapix):
    
    def __init__(self):
        super(Subclass, self).__init__()
        self.gamepad = os.path.join(os.path.dirname(__file__),
                                    'gamepad1js4btn.svg')
```
 
To build the SVG, refer to the library's [readme][hyamanieugamepad].

If you set the gamepad, running the program will also start the gamepad
server on port 5000 in your local network. You can change some key 
behavior by setting [config.json](node-custom-virtual-gamepads/config.json) as specified in the readme.

### Package organization

Rather than installing with setup.py, we decided to enforce a certain
folder organization as follows:

```
/Parent/
|_ murapix/
|_ games/
|   |_ game1/
|   |_ game2/
|_ animation/
    |_ anim1/
    |_ anim2/
```
All you games are placed inside a folder within the same parent folder
as your murapix package.

In your game main python file, you can now import murapix as follows:
```
murapix_path = os.path.join(os.path.dirname(__file__),'..','..')
sys.path.append(murapix_path)
from murapix.murapix import Murapix, get_panel_adresses,get_deadzone_addresses
```

### Example

an example game using the virtual gamepad can be found there: https://github.com/murapixrepo/amiral_8btn


# contributing

Issues and PR are welcome.

To be improved:
  - Make it more efficient (current FPS for 6 64*64 LED matrices hovers below 60 on a RPi 3B+), eventualy avoid the python binding from hzeller.
  - Avoid using numpy to find largest rectangles
  - Use a more interactive gamepad, eventualy changing to epeios-q37 atlas solution: https://github.com/epeios-q37/atlas-python
  - Make it more elegant?

# credits and license

This library relies heavily on hzeller rpi-rgb-led-matrix, submoduled here.
The virtual gamepads is a derivative work from jehervy node-virtual-gamepads library, submoduled here.

This library was, among other things, inspired by [backupify pgmatrix library][pgmatrix].

The license is GPL 3.

  [pythonbinding]: <https://github.com/hzeller/rpi-rgb-led-matrix/tree/master/bindings/python>
  [hzeller]: <https://github.com/hzeller/rpi-rgb-led-matrix>
  [jehervygamepad]: <https://github.com/jehervy/node-virtual-gamepads>
  [hyamanieugamepad]: https://github.com/hyamanieu/node-custom-virtual-gamepads/tree/custom-virtual-gamepads
  [pgmatrix]: <https://github.com/backupify/pgmatrix>
