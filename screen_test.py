#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec 13 14:30:01 2018

Run this program to test your murapix installation. Run it in demo mode
to check if your mapping configuration is correctly interpreted.

@author: hyamanieu
"""

from murapix import Murapix
import pygame
import pygame.locals as pgl
import sys
from random import randint, choice

some_pal = ['#92C6FF', '#97F0AA', '#FF9F9A', '#D0BBFF', '#FFFEA3', '#B0E0E6']
def pick_color(pal):
    i = -1
    while True:
        i+=1
        if i==len(pal):
            i=0
        yield pal[i]
pc = pick_color(some_pal)   

class Screen_Test(Murapix):
    def setup(self):
        self.ticks = 0
        scratch = self.scratch
        mapping = self.mapping
        led_rows = self.led_rows
        font = pygame.font.Font(None, led_rows//4)
        for i, n in enumerate(mapping):#rows
            for j, m in enumerate(n):#columns
                pygame.draw.rect(scratch,pygame.Color(next(pc)),[led_rows*j,led_rows*i,led_rows,led_rows])
                if m is None:
                    text = font.render("X",False,(0,0,0))
                else:
                    text = font.render(str(m),False,(0,0,0))
                
                scratch.blit(text,(led_rows*j,led_rows*i))
        
    
    def logic_loop(self):
        for event in pygame.event.get():
            if ((event.type == pgl.QUIT) 
                or ((event.type == pgl.KEYDOWN) 
                    and (event.key == pgl.K_ESCAPE))):
                pygame.quit()
                sys.exit()
        led_rows = self.led_rows
        if self.ticks % 100 == 0:
          self.current_image = randint(1,self.max_number_of_panels)
          self.current_color = pygame.Color(next(pc))
          self.text_pos = [choice([0,led_rows//4, led_rows//2, 3*led_rows//4]),
                           choice([0,led_rows//4, led_rows//2, 3*led_rows//4])]
          self.ticks=0
        self.ticks += 1
    def graphics_loop(self):   
        scratch = self.scratch
        mapping = self.mapping
        led_rows = self.led_rows
        text_pos = self.text_pos
        font = pygame.font.Font(None, 16)     
        for i, n in enumerate(mapping):#rows
            for j, m in enumerate(n):#columns
                if m != self.current_image:
                    continue
                pygame.draw.rect(scratch,
                                 (0,0,0),
                                 [led_rows*j,led_rows*i,led_rows,led_rows])
                pygame.draw.rect(scratch,
                                 self.current_color,
                                 [led_rows*j,led_rows*i,led_rows,round(led_rows*self.ticks/100)])
                text = font.render(str(m),False,(0,0,0))
                
                scratch.blit(text,(led_rows*j+text_pos[0],led_rows*i+text_pos[1]))


def main():

  Screen_Test().run()

if __name__ == '__main__':
  main()
