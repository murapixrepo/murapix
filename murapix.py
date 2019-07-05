#!/usr/bin/env python3
# -*- coding: utf-8 -*-


#    murapix is a python wrapper to make pygame applications to be shown on LED using hzeller library
#    Copyright (C) 2019 hy@hyamani.eu
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.


"""
Created on Thu Nov 22 17:37:36 2018

The Murapix package is meant to be used as a wrapper to make pygame applications
that will be shown on LED using hzeller library

How to use:
    python main.py config.ini
    python main.py config.ini [--demo]
    python main.py config.ini [--demo=3]
    
The config file is meant to describe your murapix hardware, i.e. how your 
panels are laid out and how many leds they have. IMPORTANT: all panel must
be the same!
 
the config file must always contain a 'matrix' section with the following
 variables:
    mapping: several lines of coma separated values. A value must be a '.', 
    indicating an empty place, or an integer. The integers must form a sequence
    from 1 to the total number of panels.
    led-rows: the number of leds per row for each panel
    led-cols: the number of leds per column for each panel
    example:
        [matrix]
        mapping = ., ., 1, .
                  2, 3, 4, .
                  5, 6, 7, 8
        led-rows = 64
        led-cols = 64

@author: hyamanieu
"""
from configparser import ConfigParser
import os
import sys
import pygame
import pygame.locals as pgl
from PIL import Image
from collections import deque
from threading import Thread
try:
    from .custom_virtual_gamepads import set_up_gamepad
except (ImportError, SystemError) as e:#if doing screen test
    from custom_virtual_gamepads import set_up_gamepad
import signal


CURRDIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(CURRDIR, 'matrix','bindings','python'))
#from rgbmatrix import RGBMatrix, RGBMatrixOptions


def init_pygame_display(width, height):
  os.putenv('SDL_VIDEODRIVER', 'fbcon')
  os.environ["SDL_VIDEODRIVER"] = "dummy"
  pygame.init()
  #pygame.display.set_mode((width, height), 0, 24)
  #return pygame.display.get_surface()
  return pygame.Surface((width, height))


def process_input_arg(argv):
    """
    Returns a tuple of len 2.
    The first object is a string to a config file.
    The second argument is an integer for the demo. If set to 0, then the 
    pygame surface will be sent to the matrix leds. Else, it will be outputed
    on the normal screen with a scaling factor.
    """
    assert (len(argv)<4),"maximum 2 arguments"
    assert (len(argv)>1),"needs at least one argument to the config file"
    
    demo = 0
    configfile = ''
    for arg in argv:
        if "--demo" in arg:
            demo = arg.split('=')
            if len(demo) == 1:
                demo = 1
            elif len(demo) == 2:
                demo = int(demo[1])
        else:            
            configfile = arg
    assert (os.path.isfile(configfile)), configfile+" should be a path to the config file"
    return configfile, demo
            


def get_config(configfile):
    """
    configfile: path to a .ini file with the murapix configuration
    
    returns mapping, width, height, max_number_of_panels, led_rows
    """
    config = ConfigParser()
    config.read(configfile)
    mapping = config.get('matrix','mapping')
    #first get number of holes
    number_of_holes = mapping.count('.')
    #then change mapping to a list of list
    mapping = mapping.split('\n')
    mapping = [m.split(',') for m in mapping]
    #check if mapping is correctly configured
    good_size_col = all(len(mapping[m]) == len(mapping[m+1]) 
                        for m in range(len(mapping)-1))
    assert good_size_col, "There should be the same number of panels per row"
    number_of_rows = len(mapping)
    number_of_cols = len(mapping[0])
    max_number_of_panels = number_of_cols * number_of_rows - number_of_holes
    panel_numbering = list(range(1,max_number_of_panels+1))
    for i in range(number_of_rows):
        for j in range(number_of_cols):
            if '.' in mapping[i][j]:
                mapping[i][j] = None
            else:
                try:
                    p_n = int(mapping[i][j])
                except:         
                    err_mess = 'mapping must contain either "." or integers'
                    raise ValueError(err_mess)
                err_mess = "Integers in mapping should form a sequence from 1 to "+str(max_number_of_panels)
                assert (p_n in panel_numbering), err_mess
                mapping[i][j] = p_n
                panel_numbering.remove(p_n)
    err_mess = "Missing integers in mapping: "+str(panel_numbering)
    assert (len(panel_numbering)<1), err_mess
    
    led_rows = config.getint('matrix','led-rows')
    led_cols = config.getint('matrix','led-cols')
    assert (led_rows==led_cols), "For now, murapix can only control square led panels"
    #TODO: check if non-square pannels work
    width = number_of_cols * led_cols
    height = number_of_rows * led_rows
    
    if config.has_option('matrix','parallel'):
        parallel = config.getint('matrix','parallel')
        err_msg = ("Each channel must have the same number of pannels:\n"
                   "{} total number of pannels for {} channels".format(max_number_of_panels, 
                                                                       parallel))
        assert max_number_of_panels%parallel == 0, err_msg
    else:
        parallel = 1
    
    return mapping, width, height, max_number_of_panels, led_rows, led_cols, parallel
    
    
def get_largest_rect(mapping, key='surface'):
    """
    get the largest rectangle from the mapping of LED matrices.
    
    "Largest" maybe calculated by two methods:
        "surface": the rectangle with the largest surface
        "diag": the rectangle with the largest diagonal
    """
    
    #https://stackoverflow.com/questions/19414673/in-numpy-how-to-efficiently-list-all-fixed-size-submatrices    
    from numpy.lib.stride_tricks import as_strided
    from itertools import product    
    import numpy as np
    m = np.array(mapping)
    l = product(range(m.shape[0],0,-1),range(m.shape[1],0,-1))
    if key=='surface':
        all_shapes = sorted(l, key=lambda row: row[0]*row[1],reverse=True)
    elif key=='diag':
        all_shapes = sorted(l, key=lambda row: row[0]**2+row[1]**2,reverse=True)
    else:
        raise ValueError('Key must be "surface" or "diag". {} was entered'.format(key))
        
    for sub_shape in all_shapes:
        view_shape = tuple(np.subtract(m.shape, sub_shape) + 1) + sub_shape
        arr_view = as_strided(m, view_shape, m.strides * 2)
        arr_view = arr_view.reshape((-1,) + sub_shape)
        for i in arr_view:
            if i.all():
                return i
    
def get_largest_rect_add(led_rows, m,n=None,key='surface'):
    """
    Returns the pixel/led address of the largest rectangle using pygame standard:
        ((left, top), (width, height))
        
    ____
    usage
    ____
    
    If get_largest_rect was not called before, just insert the mapping. You
    may indicate the calculation method
    >>> (left, top), (width, height) = get_largest_rect_add(led_rows,mapping)
    >>> (left, top), (width, height) = get_largest_rect_add(led_rows,mapping,key='diag')
    In case the largest rectangle is already known, insert both
    >>> (left, top), (width, height) = get_largest_rect_add(led_rows,mapping,rec)
    
    """
    import numpy as np
    if n is None:
        n = get_largest_rect(m,key=key)
    if type(m) is not np.ndarray:
        m = np.array(m)
    
    top, left = (np.argwhere(m==n[0][0])*led_rows).flatten().tolist()
    _t, _l = ((1+np.argwhere(m==n[-1][-1]))*led_rows).flatten().tolist()
    width, height = _l-left, _t-top
    
    
    return ((left, top),(width, height))
    
def get_deadzone_addresses(mapping, led_rows):
    """
    Yields a list of ((left, top), (width, height)) for each square where
    there is a dead zone in the mapping, i.e. no LED in the matrix.
    """
    for i, n in enumerate(mapping):#x, rows
            for j, m in enumerate(n):#y, panel number
                if m is not None:
                    continue
                #rectangle to extract from the width*height scratch surface
                yield ((led_rows*j,led_rows*i),(led_rows,led_rows))


def get_panel_adresses(mapping, led_rows):
    """
    Yields a list of ((left, top), (width, height)) for each square where
    there is a panel in the mapping.
    """
    for i, n in enumerate(mapping):#x, rows
            for j, m in enumerate(n):#y, panel number
                if m is None:
                    continue
                #rectangle to extract from the width*height scratch surface
                yield ((led_rows*j,led_rows*i),(led_rows,led_rows))



class Murapix:
    """
    Create a subclass to use Murapix
    
    The screen surface on which you need to blit the sprites is self.scratch.
    
    Murapix has the following properties:
        self.mapping: how the different LED panels are put in place
        self.demo: 0 if going to the LED panels, a positive int if it is going to the standart screen
        self.width: the total width of the rectangle enclosing all panels in pixel        
        self.height: the total height of the rectangle enclosing all panels in pixel
        self.max_number_of_panels: the number of panels
        self.led_rows: the number of pixel for both height and width of the panels
        self.scratch: the total pygame surface which is going to be processed by the murapix draw methods to either go the LED panels or, in demo mode, to the standart screen.
        self.gamepad: None by default. If set to a path string pointing to an SVG, will start the virtual gamepad
    """
    def __init__(self):
        configfile, demo = process_input_arg(sys.argv)
        (mapping, width, height, max_number_of_panels, 
         led_rows, led_cols, parallel) = get_config(configfile)
        self.RUNNING = True
        self.mapping = mapping
        self.demo = demo
        self.width = width
        self.height = height
        self.max_number_of_panels = max_number_of_panels
        self.led_rows = led_rows
        self.led_cols = led_cols
        self.parallel = parallel
        self.scratch = pygame.Surface((width, height))
        self.gamepad = None
        
        
        #signal handlers to quite gracefully
        signal.signal(signal.SIGINT, self.quit_gracefully)
        signal.signal(signal.SIGTERM,self.quit_gracefully)
        print("""    murapix  Copyright (C) 2019  hy@amani.eu
    This program comes with ABSOLUTELY NO WARRANTY.
    This is free software, and you are welcome to redistribute it
    under certain conditions.""")#LICENSE
        
        if not demo:
            #must be a raspberry pi configured for murapix, hence nodename
            #must be "rpi-murapix"
            if os.uname().nodename not in ("rpi-murapix","raspberrypi"):
                raise EnvironmentError("Not a murapix, please select demo mode with --demo=X")
            
            print('Going on the Murapix!')
            print('{0} channel(s) of [{1}*{2}={3} LED] X [{4} LED]'.format(parallel,
                                                     max_number_of_panels//parallel,
                                                     led_rows,
                                                     max_number_of_panels*led_rows//parallel,
                                                     led_cols))
            #the screen is just a single line of panels
            
            options = RGBMatrixOptions()
            options.rows = options.cols = led_rows
            options.parallel = parallel
            options.chain_length = max_number_of_panels//parallel
            options.hardware_mapping = 'regular'
            options.drop_privileges = 0
            self.matrix = RGBMatrix(options = options)
            
            self.double_buffer = self.matrix.CreateFrameCanvas()
            self._screen = init_pygame_display((max_number_of_panels//parallel)*led_rows, 
                                              led_cols*parallel)
        else:      
            print('Going on the standart screen...')      
            pygame.init()
            self._screen = pygame.display.set_mode((width*demo,height*demo),0, 32)
            
            
        self.clock = pygame.time.Clock()
        self.fps = 15  
        
    
    def setup(self):
        pass

    def logic_loop(self):
        pass
    
    def graphics_loop(self):
        pass
    
    def run(self):
        if self.gamepad:
            try:
                self.start_gamepad()
            except Exception as e:
                print("Error starting gamepad") 
                print(e)         
                self.close()
                raise e
        self.setup()
        
        if self.demo:
            draw = self.draw_demo
        else:
            draw = self.draw_murapix
        while self.RUNNING:
            self.logic_loop()
            self.graphics_loop()
            draw()
            self.clock.tick(self.fps)
        
        self.close()
      
    def draw_demo(self):
        demo = self.demo
        width = self.width
        height = self.height
        pygame.transform.scale(self.scratch,
                               (width*demo,height*demo),
                               self._screen)
        pygame.display.flip()
     
    def draw_murapix(self):
        scratch = self.scratch
        screen = self._screen
        mapping = self.mapping
        led_rows = self.led_rows
        led_cols = self.led_cols
        parallel = self.parallel
        curr_chain_row = 0
        NoP_per_chain = int(self.max_number_of_panels/parallel)
        
        #now blit each simulated panel in a row onto screen in the order 
        #indicated by the mapping in the config file.   
        #TODO: may be more efficient by vectorizing & using blits() instead of blit()
        for i, n in enumerate(mapping):#x, rows
            for j, m in enumerate(n):#y, panel number
                if m is None:
                    continue
                #find in which chain "m" is
                curr_chain_row = int((m-1)/NoP_per_chain)
                
                #print into a square that fits hzeller doc led addressing
                #see https://github.com/hzeller/rpi-rgb-led-matrix/blob/master/wiring.md#chains                
                screen.blit(scratch,#surface to take from
                            #LED (row,col) on the lined up panels
                            (led_rows*((m-(NoP_per_chain*curr_chain_row))-1),
                             curr_chain_row*led_cols),
                            #rectangle to extract from the width*height scratch surface
                            area=pygame.Rect((led_rows*j,led_rows*i),
                                             (led_rows,led_rows)))
                
                
        
        py_im = pygame.image.tostring(screen, "RGB",False)
        pil_im = Image.frombytes("RGB",screen.get_size(),py_im)
        self.double_buffer.SetImage(pil_im)
        self.matrix.SwapOnVSync(self.double_buffer)
        
    def start_gamepad(self):
        assert os.path.isfile(self.gamepad), "self.gamepad must be a path to an SVG file"
        self.p = set_up_gamepad(self.gamepad)
        self.draw_select_gamepads()
        pygame.joystick.quit()
        pygame.joystick.init()
        
        
    def draw_select_gamepads(self):
        #TODO : check if close_fds in custom virtual gamepad allowed for thread to stop when Popen subprocess is killed.
        #TODO : finish animation to wait for gamepad to run
        #functions to read last output lines from virtual gamepad
        #needed to check status
        def start_thread(func, *args):
            t = Thread(target=func, args=args, name="node_gamepad_output_reader")
            t.daemon = True
            t.start()
            return t
        
        def consume(infile, output):
            for line in iter(infile.readline, ''):
                output(line)
            infile.close()
            
        N = 30
        queue = deque(maxlen=N)
        thread = start_thread(consume, self.p.stdout, queue.append)
        
        rect_area = get_largest_rect_add(self.led_rows,self.mapping)
        ((left, top),(width, height)) = rect_area
        fontsize = 3*width//18-1
        font = pygame.font.Font(None, fontsize)
        
        if self.demo:
            draw = self.draw_demo
        else:
            draw = self.draw_murapix
        
        #init wait screen
        still_loading = True
        c = "Loading..."
        texts = [font.render(c[0:i+1],
                           False,
                           (255,255,255),
                           (0,0,0)) for i in range(len(c))]
    
        tw , th = font.size(c)
        pick = -1
        current_im = -1
        #show loading screen until listening
        while still_loading:
            current_im += 1
            if current_im > self.fps//6:
				
                print('\r  {0}:  {1}'.format(current_im, texts[pick]), end='')
                current_im = 0
                pick = (pick + 1) % len(c)
            self.clock.tick(self.fps)           
            
            
            text = texts[pick]
            self.scratch.fill((0,0,0))
            self.scratch.blit(text,(left+(width-tw)//2,top+fontsize))
            draw()
            #print('\r  {0}'.format(queue), end='')
            for q in queue:
                if b"info: Listening on 5000" in q:
                    still_loading = False
            
            
        
        current_im = -1
        text = font.render("Connect to",
                           False,
                           (255,255,255),
                           (0,0,0))
        text_end0 = font.render("murapix:5000",
                                     False,
                                     (255,255,255),
                                     (0,0,0))
        while current_im < 3*self.fps:#show what to do for 3 sec
            self.clock.tick(self.fps)
            current_im += 1
            self.scratch.fill((0,0,0))
            tw , th = font.size("Connect to")
            self.scratch.blit(text,(left+(width-tw)//2,top+fontsize))
            tw , th = font.size("murapix:5000")
            self.scratch.blit(text_end0,(left+(width-tw)//2,top+2*fontsize))
            draw()
            print("\r {0}".format(current_im), end='')
            
        print("hello!")
        not_selected = True
        no_gamepad = True
        active_joystick = False
        top = top + (height-fontsize*4)//2
        text = font.render("Players connected:",
                           False,
                           (255,255,255),
                           (0,0,0))
        text_end0 = font.render("Press any key",
                                     False,
                                     (255,255,255),
                                     (0,0,0))
        text_end1 = font.render(" to start",
                                     False,
                                     (255,255,255),
                                     (0,0,0))
        
        
        while not_selected:
            self.clock.tick(self.fps)
            NoJS = [x.startswith('js') for x in os.listdir("/dev/input")].count(True)
            
            text_NoP = font.render(str(NoJS),
                                         False,
                                         (255,255,255),
                                         (0,0,0))
            if NoJS>0 and no_gamepad:
                no_gamepad = False
                pygame.joystick.quit()
                pygame.joystick.init()
                active_joystick = pygame.joystick.Joystick(0)
                active_joystick.init()
            
            
            for event in pygame.event.get():
                if (active_joystick and event.type == pgl.JOYBUTTONDOWN):
                    not_selected = False
                    print('{} players selected'.format(NoJS))
            
            
            self.scratch.fill((0,0,0))
            tw , th = font.size("Players connected:")
            self.scratch.blit(text,(left+(width-tw)//2,top))
            self.scratch.blit(text_NoP,(left+width//2,top+1*fontsize))
            tw , th = font.size("Press any key")
            self.scratch.blit(text_end0,(left+(width-tw)//2,top+2*fontsize))
            tw , th = font.size(" to start")
            self.scratch.blit(text_end1,(left+(width-tw)//2,top+3*fontsize))
            draw()
    
    def close(self):
        #https://stackoverflow.com/questions/2638909/killing-a-subprocess-including-its-children-from-python
        
        if self.gamepad:
            try:
                os.killpg(os.getpgid(self.p.pid), signal.SIGTERM)
            except Exception as e:
                print("Error trying to kill gamepad node and its children")
                print(e)
                
            
        pygame.quit()
        sys.exit()

    def quit_gracefully(self,sig,frame):
        print('\n### {} was catched, terminating ###'.format(signal.Signals(sig).name))
        self.RUNNING = False
        self.close()
