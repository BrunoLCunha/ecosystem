import arcade
import arcade.key
import random
import math
from enum import Enum

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

HEALTH_BAR_WIDTH = 50
HEALTH_BAR_HEIGHT = 10
HEALTH_BAR_OFFSET_Y = 25

BALLOON_OFFSET_Y = 40
BALLOON_WIDTH = 40
BALLOON_HEIGHT = 40
ICON_SIZE = 32

SCREEN_TITLE = "Ecosystem Simulator"
GRID_UNIT_X = 25
GRID_UNIT_Y = 15
GRID_OFFSET_X = SCREEN_WIDTH / GRID_UNIT_X
GRID_OFFSET_Y = SCREEN_HEIGHT / GRID_UNIT_Y
IDDLE_TIME = 5
INTERACT_RANGE = 40

FOX_MOVEMENT_SPEED = 20
FOX_RUNNING_SPEED = 60
FOX_HUNGRY_INTERVAL = 15
FOX_REPRODUCTIVE_INTERVAL = 80
FOX_LIFE_EXPECTANCY = 180
FOX_HEALTH = 10

RABBIT_MOVEMENT_SPEED = 22
RABBIT_RUNNING_SPEED = 66
RABBIT_HUNGRY_INTERVAL = 10
RABBIT_REPRODUCTIVE_INTERVAL = 50
RABBIT_LIFE_EXPECTANCY = 100
RABBIT_HEALTH = 1

PLANT_REPRODUCTIVE_INTERVAL = 30
PLANT_LIFE_EXPECTANCY = 300
PLANT_HEALTH = 7

class AnimalRoutine(Enum):
    HUNGRY = 0
    IDDLE_TIME = 1
    REPRODUCTIVE_INTERVAL = 2
    LIFE_EXPECTANCY = 3

class PlantRoutine(Enum):
    REPRODUCTIVE_INTERVAL = 0
    LIFE_EXPECTANCY = 1

class LivingBeingStates(Enum):
    EATING = 3
    REPRODUCING = 4
    DEAD = 5
    STARVING = 6,
    NORMAL = 7

class AnimalStates(Enum):
    WALKING = 1
    RUNNING = 2
    EATING = LivingBeingStates.EATING
    REPRODUCING = LivingBeingStates.REPRODUCING
    DEAD = LivingBeingStates.DEAD,
    STARVING = LivingBeingStates.STARVING

class LivingType(Enum):
    RABBIT = 1
    FOX = 2,
    PLANT = 3,

class HealthBar:
    def __init__(self, max_health):
        self.max_health = max_health
        self.current_health = max_health

    def draw(self, x, y):
        if self.current_health != self.max_health:
            health_width = (self.current_health / self.max_health) * HEALTH_BAR_WIDTH
            
            arcade.draw_rectangle_filled(x, y + HEALTH_BAR_OFFSET_Y, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT, arcade.color.GRAY)
            arcade.draw_rectangle_filled(x - (HEALTH_BAR_WIDTH - health_width) / 2, y + HEALTH_BAR_OFFSET_Y, health_width, HEALTH_BAR_HEIGHT, arcade.color.GREEN)

    def update_health(self, new_health):
        self.current_health = max(0, min(self.max_health, new_health))

class AnimalNeeds:
    def draw(self, x, y, current_target_object, current_state):
        if current_target_object != None:
            balloon_x = x
            balloon_y = y + BALLOON_OFFSET_Y
            
            arcade.draw_rectangle_outline(balloon_x, balloon_y, BALLOON_WIDTH, BALLOON_HEIGHT, arcade.color.BLACK)

            self.draw_need_icons(balloon_x, balloon_y, current_target_object)

    def draw_need_icons(self, balloon_x, balloon_y, current_target_object):
        texture = current_target_object.texture
        arcade.draw_texture_rectangle(balloon_x, balloon_y, ICON_SIZE, ICON_SIZE, texture)

class LivingBeing:
    def __init__(self, health):
        self.health = health
        self.health_bar = HealthBar(self.health)

    def take_hit(self, damage, imobilize_on_hits):
        self.health -= damage
        self.health_bar.update_health(self.health)
        
        if imobilize_on_hits:
            self.movement_speed = 0

        if self.health <= 0.01:
            self.current_state = LivingBeingStates.DEAD

    def on_draw(self):
        self.health_bar.draw(self.center_x, self.center_y)

class Animal(LivingBeing):
    def __init__(self, targets, hungry_level, movement_speed, 
                 running_speed, health, damage, imobilize_on_hits, 
                 reproductive_interval, mates, reproduce_function, 
                 simulation, type, life_expectancy):
        super().__init__(health)
        self.damage = damage
        self.targets = targets
        self.mates = mates
        self.current_target_object = None
        self.current_target_coord = None
        self.reproductive_interval = reproductive_interval
        self.routines_interval = [hungry_level + random.randrange(0, 10), IDDLE_TIME + random.randrange(0, 10), reproductive_interval + random.randrange(0, 10), life_expectancy + random.randrange(0, 10)]
        self.initial_hungry_level = hungry_level
        self.movement_speed = movement_speed
        self.hungry_time_to_fulfill = 1
        self.imobilize_on_hits = imobilize_on_hits
        self.running_speed = running_speed
        self.current_state = AnimalStates.WALKING
        self.animal_needs = AnimalNeeds()
        self.reproduce_function = reproduce_function
        self.simulation = simulation
        self.type = type
        self.life_expectancy = life_expectancy

    def on_hungry(self, delta_time):
        nearest_target_dist = float("inf")

        for target in self.targets:
            current_dist = arcade.get_distance(self.center_x, self.center_y, target.center_x, target.center_y)
            if nearest_target_dist > current_dist and target.current_state != LivingBeingStates.DEAD or self.current_target_object == None or self.current_target_object.current_state == LivingBeingStates.DEAD:
                nearest_target_dist = current_dist
                self.current_target_object = target

        if nearest_target_dist < INTERACT_RANGE:
            self.eat(delta_time, self.current_target_object)
        
        if self.current_target_object != None and self.current_target_object.current_state == LivingBeingStates.DEAD:
            self.clear_state()

    def on_reproducing(self, delta_time):
        nearest_target_dist = float("inf")

        if not self.current_target_object or self.current_target_object.type != self.type:
            self.current_target_object = None
            for target in self.mates:
                current_dist = arcade.get_distance(self.center_x, self.center_y, target.center_x, target.center_y)
                if nearest_target_dist > current_dist and target.current_state != AnimalStates.DEAD and target.current_state != AnimalStates.REPRODUCING:
                    nearest_target_dist = current_dist
                    self.current_target_object = target
                    target.current_state = AnimalStates.REPRODUCING
                    target.current_target_object = self
        
        if self.current_target_object:
            if self.current_target_object.current_state == AnimalStates.DEAD:
                self.routines_interval[AnimalRoutine.REPRODUCTIVE_INTERVAL.value] = self.reproductive_interval
                self.clear_state()

            target = self.current_target_object
            if target:
                distance = arcade.get_distance(self.center_x, self.center_y, target.center_x, target.center_y)
                if distance < INTERACT_RANGE:
                    self.reproduce(self.current_target_object)

    def set_walk_around_target(self):
        walk_x_min = max(int(self.center_x - SCREEN_WIDTH / 4), 1)
        walk_x_max = min(int(self.center_x + SCREEN_WIDTH / 4), SCREEN_WIDTH - 1)

        walk_y_min = max(int(self.center_y - SCREEN_HEIGHT / 4), 1)
        walk_y_max = min(int(self.center_y + SCREEN_HEIGHT / 4), SCREEN_HEIGHT - 1)

        self.current_target_coord = [random.randint(walk_x_min, walk_x_max), random.randint(walk_y_min, walk_y_max)]
        
    def eat(self, delta_time, target):
        target.take_hit(self.damage * delta_time, self.imobilize_on_hits)
        
        self.hungry_time_to_fulfill -= delta_time

        if self.hungry_time_to_fulfill < 0:
            self.hungry_time_to_fulfill = 1
            self.routines_interval[AnimalRoutine.HUNGRY.value] = self.initial_hungry_level
            self.clear_state()
    
    def reproduce(self, target):
        target.routines_interval[AnimalRoutine.REPRODUCTIVE_INTERVAL.value] = target.reproductive_interval
        self.routines_interval[AnimalRoutine.REPRODUCTIVE_INTERVAL.value] = self.reproductive_interval

        target.clear_state()
        self.clear_state()

        self.reproduce_function(self.simulation, (self.center_x + 1, self.center_y + 1))
    
    def normalize(self, x, y):
        magnitude = math.sqrt(x**2 + y**2)
        if magnitude == 0:
            return 0, 0
        return x / magnitude, y / magnitude

    def walk(self, delta_time, target, running):
        moviment_dir = [0, 0]
        moviment_dir[0] = target[0] - self.center_x  
        moviment_dir[1] = target[1] - self.center_y 
        normalized_x, normalized_y = self.normalize(moviment_dir[0], moviment_dir[1])

        distance = arcade.get_distance(self.center_x, self.center_y, target[0], target[1])
        min_distance = 10

        if distance > min_distance:
            movement_speed = self.running_speed if running else self.movement_speed

            self.center_x += normalized_x * movement_speed * delta_time
            self.center_y += normalized_y * movement_speed * delta_time

    def update(self, delta_time):
        self.handle_current_state(delta_time)

        for index, interval in enumerate(self.routines_interval):
            self.routines_interval[index] = interval - delta_time 
        
        if self.current_target_object:
            self.walk(delta_time, [self.current_target_object.center_x, self.current_target_object.center_y], True)

        # food call
        if self.current_state == AnimalStates.STARVING:
            return self.on_hungry(delta_time)

        # reproducing call
        if self.current_state == AnimalStates.REPRODUCING:
            return self.on_reproducing(delta_time)

        # walking call
        if self.current_state == AnimalStates.WALKING:
            iddle_location_expired = self.routines_interval[AnimalRoutine.IDDLE_TIME.value] < 0 
            has_target_location = self.current_target_coord != None

            if iddle_location_expired or not has_target_location:
                self.set_walk_around_target()
                self.routines_interval[AnimalRoutine.IDDLE_TIME.value] = IDDLE_TIME

            self.walk(delta_time, self.current_target_coord, False)
        

    def clear_state(self):
        self.current_state = AnimalStates.WALKING
        self.current_target_object = None
        self.current_target_coord = None

    def handle_current_state(self, delta_time):
        if self.current_state == LivingBeingStates.DEAD:
            self.simulation.entities.remove(self)

        if self.current_state == None:
            self.current_state = AnimalStates.WALKING

        any_alive = len(list(filter(lambda target: target.current_state != AnimalStates.DEAD, self.targets))) > 0
        is_char_hungry = self.routines_interval[AnimalRoutine.HUNGRY.value] < 0
        if is_char_hungry:
            # self.apply_state(AnimalStates.STARVING)
            if any_alive:
                self.apply_state(AnimalStates.STARVING)
            else:
                self.take_hit(delta_time, False)

        if self.routines_interval[AnimalRoutine.REPRODUCTIVE_INTERVAL.value] < 0:
            self.apply_state(AnimalStates.REPRODUCING)

        if self.current_state == AnimalStates.STARVING and not any_alive:
            self.clear_state()
        
        is_target_life_expectancy_reached = self.routines_interval[AnimalRoutine.LIFE_EXPECTANCY.value] < 0
        if is_target_life_expectancy_reached:
            self.current_state = AnimalStates.DEAD

    def apply_state(self, new_state):
        if new_state != self.current_state:
            if self.current_state == AnimalStates.STARVING and new_state != AnimalStates.DEAD:
                return

            self.clear_state()
            self.current_state = new_state

    def on_draw(self): 
        LivingBeing.on_draw(self)
        self.animal_needs.draw(self.center_x, self.center_y, self.current_target_object, self.current_state)

class Plant(LivingBeing):
    def __init__(self, health, reproductive_interval, reproduce_function, 
                 simulation, life_expectancy, type):
        super().__init__(health)
        self.reproductive_interval = reproductive_interval
        self.reproduce_function = reproduce_function
        self.simulation = simulation
        self.life_expectancy = life_expectancy
        self.routines_interval = [reproductive_interval + random.randrange(0, 10), life_expectancy + random.randrange(0, 10)]
        self.current_state = LivingBeingStates.NORMAL
        self.type = type

    def on_draw(self): 
        LivingBeing.on_draw(self)
    
    def clear_state(self):
        self.current_state = LivingBeingStates.NORMAL

    def on_reproducing(self):
        self.reproduce()
    
    def reproduce(self):
        self.routines_interval[PlantRoutine.REPRODUCTIVE_INTERVAL.value] = self.reproductive_interval

        self.clear_state()

        self.reproduce_function()
    
    def apply_state(self, new_state):
        if new_state != self.current_state:
            self.current_state = new_state

    def handle_current_state(self):
        if self.current_state == LivingBeingStates.DEAD:
            self.simulation.entities.remove(self)

        if self.current_state == None:
            self.current_state = LivingBeingStates.NORMAL

        if self.routines_interval[PlantRoutine.REPRODUCTIVE_INTERVAL.value] < 0:
            self.apply_state(LivingBeingStates.REPRODUCING)
        
        is_target_life_expectancy_reached = self.routines_interval[PlantRoutine.LIFE_EXPECTANCY.value] < 0
        if is_target_life_expectancy_reached:
            self.current_state = LivingBeingStates.DEAD
    
    def update(self, delta_time):
        self.handle_current_state()

        for index, interval in enumerate(self.routines_interval):
            self.routines_interval[index] = interval - delta_time 

        # reproducing call
        if self.current_state == LivingBeingStates.REPRODUCING:
            return self.on_reproducing()

class PreySprite(arcade.Sprite, Animal):
    def __init__(self, posX, posY, bushes, simulation):
        super().__init__("images/entities/base-rabbit.png", 2)
        Animal.__init__(self, bushes, RABBIT_HUNGRY_INTERVAL, RABBIT_MOVEMENT_SPEED, 
                        RABBIT_RUNNING_SPEED, RABBIT_HEALTH, 1, False, RABBIT_REPRODUCTIVE_INTERVAL, 
                        simulation.preys, simulation.add_prey, simulation, LivingType.RABBIT, RABBIT_LIFE_EXPECTANCY)
        self.center_x = posX
        self.center_y = posY
        self.bushes = bushes
        self.simulation = simulation

    def on_update(self, delta_time):
        self.update()
        Animal.update(self, delta_time)

    def on_draw(self):
        Animal.on_draw(self)
        super().draw(pixelated=True)

class PredatorSprite(arcade.Sprite, Animal):
    def __init__(self, posX, posY, simulation):
        super().__init__("images/entities/base-fox.png", 2)
        Animal.__init__(self, simulation.preys, FOX_HUNGRY_INTERVAL, FOX_MOVEMENT_SPEED,
                         FOX_RUNNING_SPEED, FOX_HEALTH, 1, True, FOX_REPRODUCTIVE_INTERVAL,
                           simulation.predators, simulation.add_predator, simulation, LivingType.FOX, FOX_LIFE_EXPECTANCY)
        self.center_x = posX
        self.center_y = posY
        self.walls = None
        self.path_list = None

    def on_update(self, delta_time):
        self.update()
        Animal.update(self, delta_time)
    
    def on_draw(self):
        Animal.on_draw(self)
        super().draw(pixelated=True)

class BushSprite(arcade.Sprite, Plant):
    def __init__(self, posX, posY, simulation):
        super().__init__("images/entities/base-bush.png", scale=2)
        Plant.__init__(self, PLANT_HEALTH, PLANT_REPRODUCTIVE_INTERVAL, simulation.add_bush, simulation, PLANT_LIFE_EXPECTANCY, LivingType.PLANT)
        self.center_x = posX
        self.center_y = posY

    def on_update(self, delta_time):
        self.update()
        Plant.update(self, delta_time)
    
    def on_draw(self):
        Plant.on_draw(self)
        super().draw(pixelated=True)

class EcosystemSimulator(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.ARMY_GREEN)

        self.entities = arcade.SpriteList()
        self.bushes = arcade.SpriteList(True)
        self.preys = arcade.SpriteList()
        self.predators = arcade.SpriteList()

        self.initialize_bushes(5)
        self.initialize_preys(10)
        self.initialize_predators(2)

    def initialize_bushes(self, bush_number):
        for _ in range(bush_number):
            self.add_bush()
    
    def initialize_preys(self, preys_number):
        for _ in range(preys_number):
            self.add_prey()

    def initialize_predators(self, predators_number):
        for _ in range(predators_number):
            self.add_predator()

    def add_bush(self):
        posX, posY = randomIntXY([1, SCREEN_WIDTH - 1], [1, SCREEN_HEIGHT - 1])
        bush = BushSprite(posX, posY, self)
        self.bushes.append(bush)
        self.entities.append(bush)
    
    def add_prey(self, child = False, coords = None):
        posX, posY = randomIntXY([1, SCREEN_WIDTH - 1], [1, SCREEN_HEIGHT - 1])

        if coords:
            posX = coords[0]
            posY = coords[1]

        prey = PreySprite(posX, posY, self.bushes, self)
        self.preys.append(prey)
        self.entities.append(prey)
    
    def add_predator(self, child = False, coords = None):
        posX, posY = randomIntXY([1, SCREEN_WIDTH - 1], [1, SCREEN_HEIGHT - 1])

        if coords:
            posX = coords[0]
            posY = coords[1]

        predator = PredatorSprite(posX, posY, self)
        self.entities.append(predator)
        self.predators.append(predator)

    def on_draw(self):
        arcade.start_render()

        sorted_entities = sorted(self.entities, key=lambda entity: entity.center_y, reverse=True)

        for entity in sorted_entities:
            entity.on_draw()
        
    def on_update(self, delta_time):
        self.entities.on_update(delta_time)

def randomIntXY(limitRangeX, limitRangeY):
    lowerLimitRangeX, upperLimitRangeX = limitRangeX
    lowerLimitRangeY, upperLimitRangeY = limitRangeY

    return random.randint(lowerLimitRangeX, upperLimitRangeX), random.randint(lowerLimitRangeY, upperLimitRangeY) 

if __name__ == '__main__':
    app = EcosystemSimulator()
    arcade.run()

