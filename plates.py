from tkinter import Tk, Canvas, LEFT, Toplevel
from numpy import array, dot, float64
from numpy.linalg import norm
from random import random
from math import *
from pygame import mixer
from PIL import ImageTk, Image

platefile = "plate.png"
img_scale = 2.11 # the image's sidelength/radius ratio

def main(wind, s = 1000, n = 46):
    # inits
    mixer.init()
    wind.title("Clinamen")
    
    can = Canvas(wind, width = s, height = s)
    
    wind.protocol("WM_DELETE_WINDOW", wind.destroy)
    
    # geometry
    can.pack(side = LEFT)
    can.focus_set()
    
    # load sounds
    soundobj = mixer.Sound("glass_clink.mp3")
    can.sound = soundobj
    
    # parameters
    can.centre = array((s*0.5, s*0.5), dtype=float64)
    can.rad = s*0.4
    can.bott = array((can.centre[0], can.centre[1]+can.rad), dtype=float64)
    max_body_radius = can.rad*0.6
    
    # populate
    can.create_oval(can.centre[0]-can.rad, can.centre[1]-can.rad, can.centre[0]+can.rad, can.centre[1]+can.rad, fill="light blue", outline="gray75")
    
    can.plates = []
    
    im0 = Image.open(platefile)
    
    for i in range(0, n, 2):
        pos = can.centre + max_body_radius*array((cos(2*pi*i/n), sin(2*pi*i/n)), dtype=float64)
        body_radius = 0.5*(random()+1)*max_body_radius*sin(2*pi/n)
        #b = Body(can.create_oval(pos[0]-body_radius, pos[1]-body_radius, pos[0]+body_radius, pos[1]+body_radius, fill="white", outline="black")
        img_side = int(img_scale*body_radius)
        
        im_new = im0.resize((img_side, img_side), Image.LANCZOS)
        plate_image = ImageTk.PhotoImage(im_new)
        
        b = Body(can.create_image(round(pos[0]), round(pos[1]), image=plate_image, anchor="center"), array((0.0, 0.0), dtype=float64), pos, body_radius, plate_image)
        can.plates.append(b)
    
    # queue refresh
    can.after(1, refresh, can)
    
    if isinstance(wind, Tk): # we are the root level
        wind.mainloop()

def refresh(can):
    plates = can.plates
    centre = can.centre
    rad = can.rad
    bott = can.bott
    density = 3.0
    
    N = len(plates)
    
    for i in range(N):
        p1 = plates[i]
        save_vel = p1.v # initial velocity
        
        # plate collisions
        for j in range(i):
            p2 = plates[j]
            
            m1, m2 = density*p1.r, density*p2.r
            R = p1.r + p2.r
            connect_vec = p1.pos-p2.pos
            conn_R = norm(connect_vec)
            alignment = dot(p1.v-p2.v, connect_vec)
            
            if conn_R < R + 0.01 and conn_R > 0.1 and alignment < 0:
                bump_term = (2*alignment/((m1+m2)*conn_R*conn_R))*connect_vec
                p1.v = p1.v - m2*bump_term
                p2.v = p2.v + m1*bump_term
                
                # sound
                # never queues sounds (so late sounds are never played)
                # sounds only play when bump is large enough
                # volume proportional to kinetic energy/imparting mass
                mu = 2*m1*m2/(m1+m2)
                kinetic_term = mu*abs(dot(bump_term, m1*p1.v + m2*p2.v))
                if mixer.find_channel() != None and kinetic_term > 0:
                    can.sound.set_volume(min(1.0, exp(kinetic_term/70)-1))
                    can.sound.play()
                    #can.itemconfigure(p1.tid, fill = "black")
                    #can.after(5, lambda x : can.itemconfigure(x, fill="white"), p1.tid)
        
        # brownian motion noise
        funnel_vect = p1.pos-centre
        p1.v += current_flow(funnel_vect)
        
        # water drag
        jerk = p1.v-save_vel
        p1.v += drag(p1.v, jerk, p1.r)
        
        # boundary collision
        # jerkless/dragless
        boundary_dist = rad-norm(p1.pos-centre)-p1.r
        p1.v = boundary(boundary_dist, p1.v, p1.pos-centre)
        
        # integration
        p1.pos += p1.v
        
        # screen update
        can.moveto(p1.tid, round(p1.pos[0]-p1.r), round(p1.pos[1]-p1.r))
    can.after(2, refresh, can)

def drag(velo, jerk, len_factor):
    area_factor = len_factor*len_factor
    coeff = 0.000005
    return -norm(velo)*velo*area_factor*coeff# - jerk*0.1

def current_flow(vect):
    x, y = vect/norm(vect)
    scale = array((random()-0.51, random()-0.51))
    r, p = scale/norm(scale)
    current = r*array((x, y)) + p*array((-y, x))
    return current*0.005

def boundary(r, v, radvec):
    if dot(v, radvec) > 0 and r < 0.1:
        return v - (2*dot(v, radvec)/dot(radvec, radvec))*radvec
    #elif dot(v, radvec) > 0 and r < 10:
    #    return v - 0.01*(2*dot(v, radvec)/dot(radvec, radvec))*radvec
    else:
        return v

class Body:
    def __init__(self, t_id, v, pos, r, image=None):
        self.r = r
        self.pos = pos
        self.v = v
        self.tid = t_id
        self.uid = t_id # permanent record of first tid
        self.image = image

if __name__ == "__main__":
    main(Tk())

