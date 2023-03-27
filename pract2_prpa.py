"""
Solution to the one-way tunnel  /////   Cecilia Sánchez Plaza

"""
import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value

SOUTH = 1
NORTH = 0

NCARS = 15
NPED = 5
TIME_CARS_NORTH = 0.5  # a new car enters each 0.5s
TIME_CARS_SOUTH = 0.5  # a new car enters each 0.5s
TIME_PED = 5 # a new pedestrian enters each 5s
TIME_IN_BRIDGE_CARS = (1, 0.5) # normal 1s, 0.5s
TIME_IN_BRIDGE_PEDESTRIAN = (3, 0.5) # normal 3s, 0.5s

class Monitor():
    def __init__(self):
        self.mutex = Lock()
        self.patata = Value('i', 0)

        #Número de coches del norte, sur y peatones pasando por el puente
        self.ncoches_N = Value('i', 0) 
        self.ncoches_S = Value('i', 0) # 
        self.npeatones = Value('i', 0) # 
   
        #Variables para ver cuántos de cada grupo están esperando
        self.esperando_coches_N = Value('i', 0)
        self.esperando_coches_S = Value('i', 0)
        self.esperando_peatones = Value('i', 0)
        
        #Definimos las condiciones que se tienen que cumplir para que puedan entrar al puente:
        self.pasan_coches_N = Condition(self.mutex)
        self.pasan_coches_S = Condition(self.mutex)
        self.pasan_peatones = Condition(self.mutex)
 

        #Los valores para saber a quién le toca el turno son: 0->peatones, 1-> coches sur, 2->coches norte, -1 ->no hay nadie esperando.
        self.turn = Value('i', -1) 

    #Esto es lo que se tiene que cumplir para que puedan entrar en el puente:
        #(incluyendo las condiciones de seguridad obligatorias, y otras para evitar inanición y deadlocks)
    def car_N_can_pass(self):
        return (self.ncoches_S.value==0 and self.npeatones.value==0) and (self.turn==2  or (self.esperando_coches_S.value <= 5 and self.esperando_peatones.value<=3) or self.turn==-1)
    
    def car_S_can_pass(self):
        return (self.ncoches_N.value==0 and self.npeatones.value==0) and (self.turn==1 or (self.esperando_coches_N.value <= 5  and self.esperando_peatones.value<=3) or self.turn==-1)
    
    def pedestrian_can_pass(self):
        return (self.ncoches_N.value==0 and self.ncoches_S.value==0) and (self.turn==0 or (self.esperando_coches_N.value <= 5 or self.esperando_coches_S.value <= 5) or self.turn==-1)
    
    
    def wants_enter_car(self, direction: int) -> None:
        self.mutex.acquire()
        self.patata.value += 1
        
        if direction == NORTH:
            self.esperando_coches_N.value +=1  #si un coche quiere entrar se suma 1 a los que están esperando
            self.pasan_coches_N.wait_for(self.car_N_can_pass)  #si cumple las condiciones y entra en el puente
            self.esperando_coches_N.value -=1                  #entonces restamos uno al nº de coches que están esperando
        
            if self.turn.value == -1:    #si no hay nadie esperando le cedemos
                self.turn.value = 2      #el turno a los del norte
            self.ncoches_N.value += 1  #añadimos uno al nº de coches del norte en el puente
        
        else:  #comentarios análogos pero para el sur
            self.esperando_coches_S.value +=1
            self.pasan_coches_S.wait_for(self.car_S_can_pass)
            self.esperando_coches_S.value -=1
        
            if self.turn.value == -1:
                self.turn.value = 1
            self.ncoches_S.value += 1
        
        
        self.mutex.release()
    
    def leaves_car(self, direction: int) -> None:
        self.mutex.acquire() 
        self.patata.value += 1
       
        
        if direction == NORTH:
            self.ncoches_N.value -= 1  #restamos un coche del norte por salir del puente
            
            if self.turn.value == 2:
                
                #si sale un coche del norte le cedo el turno a los peatones
                if self.esperando_peatones.value != 0:
                    self.turn.value = 0
                elif self.esperando_coches_S.value != 0:
                    self.turn.value = 1
                else:
                    self.turn.value = -1
                    
            
           
            if self.ncoches_N.value == 0:
                self.pasan_coches_S.notify_all()
                self.pasan_peatones.notify_all()                    
       
        else:
            self.ncoches_S.value -= 1
            
            if self.turn.value == 1:
                #si sale un coche del sur le cedo el turno al norte
                if self.esperando_coches_N.value != 0:
                    self.turn.value = 2
                elif self.esperando_peatones.value != 0:
                    self.turn.value = 0
                else:
                    self.turn.value = -1
            
            if self.ncoches_S.value == 0:
                self.pasan_coches_N.notify_all()
                self.pasan_peatones.notify_all()  
                
                
        self.mutex.release()
    
    #las siguientes funciones son análogas al caso de los coches(en peatones sin distinguir norte y sur)
    def wants_enter_pedestrian(self) -> None:
        self.mutex.acquire()
        self.patata.value += 1
        
        self.esperando_peatones.value += 1
        self.pasan_peatones.wait_for(self.pedestrian_can_pass)
        self.esperando_peatones.value -= 1
        
        if self.turn.value == -1:
            self.turn.value = 0
        self.npeatones.value += 1
        
        
        self.mutex.release()
    
    def leaves_pedestrian(self) -> None:
        self.mutex.acquire()
        self.patata.value += 1
        
        
        self.npeatones.value -= 1
        
        if self.turn.value == 0:
            #si sale un peaton le cedo el turno al sur
            if self.esperando_coches_S.value != 0:
                self.turn.value = 1
            elif self.esperando_coches_N.value != 0:
                self.turn.value = 2
            else:
                self.turn.value = -1
        
        if self.npeatones.value == 0:
            self.pasan_coches_S.notify_all()
            self.pasan_coches_N.notify_all() 
        
        
        self.mutex.release()

    def __repr__(self) -> str:
        return f'Monitor: {self.patata.value}'


#los valores del tiempo que tardan son aleatorios dentro de que sigue una distribución normal:
def delay_car_north() -> None:
    valor=random.normalvariate(TIME_IN_BRIDGE_CARS[0], TIME_IN_BRIDGE_CARS[1])
    if valor<0:
        valor=0
    time.sleep(valor)

def delay_car_south() -> None:
    valor=random.normalvariate(TIME_IN_BRIDGE_CARS[0], TIME_IN_BRIDGE_CARS[1])
    if valor<0:
        valor=0
    time.sleep(valor)

def delay_pedestrian() -> None:
    valor=random.normalvariate(TIME_IN_BRIDGE_PEDESTRIAN[0], TIME_IN_BRIDGE_PEDESTRIAN[1])
    if valor<0:
        valor=0
    time.sleep(valor)




def car(cid: int, direction: int, monitor: Monitor)  -> None:
    print(f"car {cid} heading {direction} wants to enter. {monitor}")
    monitor.wants_enter_car(direction)
    print(f"car {cid} heading {direction} enters the bridge. {monitor}")
    if direction==NORTH :
        delay_car_north()
    else:
        delay_car_south()
    print(f"car {cid} heading {direction} leaving the bridge. {monitor}")
    monitor.leaves_car(direction)
    print(f"car {cid} heading {direction} out of the bridge. {monitor}")

def pedestrian(pid: int, monitor: Monitor) -> None:
    print(f"pedestrian {pid} wants to enter. {monitor}")
    monitor.wants_enter_pedestrian()
    print(f"pedestrian {pid} enters the bridge. {monitor}")
    delay_pedestrian()
    print(f"pedestrian {pid} leaving the bridge. {monitor}")
    monitor.leaves_pedestrian()
    print(f"pedestrian {pid} out of the bridge. {monitor}")



def gen_pedestrian(monitor: Monitor) -> None:
    pid = 0
    plst = []
    for _ in range(NPED):
        pid += 1
        p = Process(target=pedestrian, args=(pid, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/TIME_PED))

    for p in plst:
        p.join()

def gen_cars(direction: int, time_cars, monitor: Monitor) -> None:
    cid = 0
    plst = []
    for _ in range(NCARS):
        cid += 1
        p = Process(target=car, args=(cid, direction, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/time_cars))

    for p in plst:
        p.join()

def main():
    monitor = Monitor()
    gcars_north = Process(target=gen_cars, args=(NORTH, TIME_CARS_NORTH, monitor))
    gcars_south = Process(target=gen_cars, args=(SOUTH, TIME_CARS_SOUTH, monitor))
    gped = Process(target=gen_pedestrian, args=(monitor,))
    gcars_north.start()
    gcars_south.start()
    gped.start()
    gcars_north.join()
    gcars_south.join()
    gped.join()


if __name__ == '__main__':
    main()
