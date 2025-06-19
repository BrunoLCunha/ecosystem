import arcade
import arcade.key
import random
import math
import time
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
GRID_UNIT_X = 5
GRID_UNIT_Y = 5
GRID_OFFSET_X = SCREEN_WIDTH / GRID_UNIT_X
GRID_OFFSET_Y = SCREEN_HEIGHT / GRID_UNIT_Y
IDDLE_TIME = 5
INTERACT_RANGE = 40
DETECTION_RANGE = 120

FOX_MOVEMENT_SPEED = 20
FOX_RUNNING_SPEED = 60
FOX_HUNGRY_INTERVAL = 15
FOX_REPRODUCTIVE_INTERVAL = 70
FOX_LIFE_EXPECTANCY = 150
FOX_HEALTH = 10

RABBIT_MOVEMENT_SPEED = 22
RABBIT_RUNNING_SPEED = 66
RABBIT_HUNGRY_INTERVAL = 20
RABBIT_REPRODUCTIVE_INTERVAL = 65
RABBIT_LIFE_EXPECTANCY = 80
RABBIT_HEALTH = 1
RABBIT_PERCEPTION_RADIUS = 80

PLANT_REPRODUCTIVE_INTERVAL = 150
PLANT_LIFE_EXPECTANCY = 300
PLANT_HEALTH = 5
PLANT_NUTRIENT_RADIUS = 80

CARD_IMAGE = "images/entities/base-card.png"
CARD_TYPES = ["create_rabbit", "create_fox", "create_bush", "create_grass", "global_heal", "hungry_rabbit"]
CARD_COST_TYPES = ["rabbit", "fox", "bush", "grass"]

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
    PURSUE_FOOD = LivingBeingStates.STARVING

class LivingType(Enum):
    RABBIT = 1
    FOX = 2,
    PLANT = 3,
    GRASS = 4

class HealthBar:
    def __init__(self, max_health):
        self.max_health = max_health
        self.current_health = max_health

    def draw(self, x, y):
        if self.current_health != self.max_health:
            # Calculate health bar width
            health_width = (self.current_health / self.max_health) * HEALTH_BAR_WIDTH
            
            # Background of the health bar
            center_x = x
            center_y = y + HEALTH_BAR_OFFSET_Y
            
            # Use LRTB version
            left = center_x - HEALTH_BAR_WIDTH / 2
            right = center_x + HEALTH_BAR_WIDTH / 2
            bottom = center_y - HEALTH_BAR_HEIGHT / 2
            top = center_y + HEALTH_BAR_HEIGHT / 2
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, arcade.color.GRAY)

            # The health itself
            health_center_x = x - (HEALTH_BAR_WIDTH - health_width) / 2
            health_left = health_center_x - health_width / 2
            health_right = health_center_x + health_width / 2
            arcade.draw_lrbt_rectangle_filled(health_left, health_right, bottom, top, arcade.color.GREEN)


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
        self.initial_health = health
        self.health_bar = HealthBar(self.health)
        self.last_damage_time = None

    def take_hit(self, damage, imobilize_on_hits=False):
        self.health -= damage
        self.health_bar.update_health(self.health)
        self.last_damage_time = time.time()
        
        if imobilize_on_hits:
            self.movement_speed = 0

        if self.health <= 0.001:
            self.current_state = LivingBeingStates.DEAD
            self.remove_from_sprite_lists()

    def on_draw(self):
        if self.last_damage_time and (time.time() - self.last_damage_time <= 2):
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
        self.initital_movement_speed = movement_speed
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
        self.strategy = None
        self.experience = {}

    def force_hungry(self):
        self.routines_interval[AnimalRoutine.HUNGRY.value] = -1

    def on_hungry(self, delta_time):
        nearest_target_dist = float("inf")

        for target in self.targets:
            current_dist = get_square_distance(self.center_x, self.center_y, target.center_x, target.center_y)
            if nearest_target_dist * nearest_target_dist > current_dist and target.current_state != LivingBeingStates.DEAD or self.current_target_object == None or self.current_target_object.current_state == LivingBeingStates.DEAD:
                nearest_target_dist = math.sqrt(current_dist)
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
                current_dist = get_square_distance(self.center_x, self.center_y, target.center_x, target.center_y)
                if nearest_target_dist * nearest_target_dist > current_dist and target.current_state != AnimalStates.DEAD and target.current_state != AnimalStates.REPRODUCING:
                    nearest_target_dist =  math.sqrt(current_dist)
                    self.current_target_object = target
                    target.current_state = AnimalStates.REPRODUCING
                    target.current_target_object = self
        
        if self.current_target_object:
            if self.current_target_object.current_state == AnimalStates.DEAD:
                self.routines_interval[AnimalRoutine.REPRODUCTIVE_INTERVAL.value] = self.reproductive_interval
                self.clear_state()

            target = self.current_target_object
            if target:
                distance = get_square_distance(self.center_x, self.center_y, target.center_x, target.center_y)
                if distance < INTERACT_RANGE * INTERACT_RANGE:
                    self.reproduce(self.current_target_object)

    def set_walk_around_target(self):
        area = None
        if hasattr(self, 'strategy'):
            if self.strategy == 'forage_open' and self.simulation.open_areas:
                area = random.choice(self.simulation.open_areas)
            elif self.strategy == 'forage_cover' and self.simulation.covered_areas:
                area = random.choice(self.simulation.covered_areas)

        if not area:
            area = random.choice(self.simulation.areas)

        target_x = random.uniform(area.center_x - area.width / 2, area.center_x + area.width / 2)
        target_y = random.uniform(area.center_y - area.height / 2, area.center_y + area.height / 2)
        self.current_target_coord = [target_x, target_y]
        
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

        self.reproduce_function(coords=(self.center_x + 1, self.center_y + 1))
    
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

        distance = get_square_distance(self.center_x, self.center_y, target[0], target[1])
        min_distance = 10

        if distance > min_distance * min_distance:
            movement_speed = self.running_speed if running else self.movement_speed

            self.center_x += normalized_x * movement_speed * delta_time
            self.center_y += normalized_y * movement_speed * delta_time

    def update(self, delta_time):
        self.handle_current_state(delta_time)
        # print(f"location x: {self.center_x} y: {self.center_x}, state: {self.current_state}, routines: {self.routines_interval}, type: {self.type}")

        for index, interval in enumerate(self.routines_interval):
            self.routines_interval[index] = interval - delta_time 
        
        self.life_expectancy = self.routines_interval[AnimalRoutine.LIFE_EXPECTANCY.value]
        
        if self.current_target_object:
            self.walk(delta_time, [self.current_target_object.center_x, self.current_target_object.center_y], True)

        # food call
        if self.current_state == AnimalStates.PURSUE_FOOD:
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
        self.movement_speed = self.initital_movement_speed

    def handle_current_state(self, delta_time):
        if self.current_state == LivingBeingStates.DEAD:
            self.remove_from_sprite_lists()

        if self.current_state == None:
            self.current_state = AnimalStates.WALKING

        any_target_alive = len(list(filter(lambda target: target.current_state != AnimalStates.DEAD, self.targets))) > 0
        is_char_hungry = self.routines_interval[AnimalRoutine.HUNGRY.value] < 0
        if is_char_hungry:
            if any_target_alive:
                self.apply_state(AnimalStates.PURSUE_FOOD)
            else:
                self.take_hit(delta_time, False)

        if self.routines_interval[AnimalRoutine.REPRODUCTIVE_INTERVAL.value] < 0:
            self.apply_state(AnimalStates.REPRODUCING)

        if self.current_state == AnimalStates.PURSUE_FOOD and not any_target_alive:
            self.clear_state()
        
        is_target_life_expectancy_reached = self.routines_interval[AnimalRoutine.LIFE_EXPECTANCY.value] < 0
        if is_target_life_expectancy_reached:
            self.current_state = AnimalStates.DEAD
            self.take_hit(self.health, False)

    def apply_state(self, new_state):
        if new_state != self.current_state:
            if self.current_state == AnimalStates.PURSUE_FOOD and new_state != AnimalStates.DEAD:
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
            self.remove_from_sprite_lists()

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

        if self.current_state == LivingBeingStates.REPRODUCING:
            return self.on_reproducing()

class PreySocialController():
    def __init__(self, simulation):
        self.simulation = simulation
        self.preys = simulation.preys
        self.max_speed = RABBIT_MOVEMENT_SPEED * 1.5
        self.perception_radius = RABBIT_PERCEPTION_RADIUS
        self.separation_radius = RABBIT_PERCEPTION_RADIUS / 2

        self.separation_weight = 30.0
        self.alignment_weight = 0.5
        self.cohesion_weight = 0.1

    def update(self, deltatime):
        for prey in self.preys:
            self.flock(prey, deltatime)
            self.avoid_predators(prey, deltatime)

    def flock(self, current_rabbit, deltatime):
        dir_separation = self.separation(current_rabbit)
        dir_alignment = self.alignment(current_rabbit)
        dir_cohesion = self.cohesion(current_rabbit)

        dir = [
        (dir_separation[0] * self.separation_weight +
         dir_alignment[0] * self.alignment_weight +
         dir_cohesion[0] * self.cohesion_weight),
        (dir_separation[1] * self.separation_weight +
         dir_alignment[1] * self.alignment_weight +
         dir_cohesion[1] * self.cohesion_weight)
        ]

        limit_vector(dir, max_value=0.5)

        current_rabbit.velocity_x += dir[0]
        current_rabbit.velocity_y += dir[1]

        speed = math.hypot(current_rabbit.velocity_x, current_rabbit.velocity_y)
        if speed > self.max_speed:
            current_rabbit.velocity_x = (current_rabbit.velocity_x / speed) * self.max_speed
            current_rabbit.velocity_y = (current_rabbit.velocity_y / speed) * self.max_speed
    
    def separation(self, current_rabbit):
        dir = [0, 0] # direcao do movimento
        total = 0 # total de coelhos com influencia (dentro do raio de percepcao)
        nearby_rabbits = self.simulation.spatial_grid.get_nearby_sprites(current_rabbit.center_x, current_rabbit.center_y)
        for rabbit in nearby_rabbits:
            if rabbit is not current_rabbit:
                distance_square = get_square_distance(current_rabbit.center_x, current_rabbit.center_y,
                                               rabbit.center_x, rabbit.center_y)
                if distance_square < (self.separation_radius * self.separation_radius): # ha influencia da separacao apenas quando a distancia < raio de separacao
                    diff_x = current_rabbit.center_x - rabbit.center_x
                    diff_y = current_rabbit.center_y - rabbit.center_y
                    if distance_square > 0:
                        distance = math.hypot(current_rabbit.center_x - rabbit.center_x, current_rabbit.center_y - rabbit.center_y)
                        diff_x /= distance
                        diff_y /= distance
                    dir[0] += diff_x
                    dir[1] += diff_y
                    total += 1
        if total > 0:
            dir[0] /= total
            dir[1] /= total
        return dir
    
    def alignment(self, current_rabbit):
        avg_velocity = [0, 0]
        total = 0
        nearby_rabbits = self.simulation.spatial_grid.get_nearby_sprites(current_rabbit.center_x, current_rabbit.center_y)
        for rabbit in nearby_rabbits:
            if rabbit is not current_rabbit:
                distance = get_square_distance(current_rabbit.center_x, current_rabbit.center_y,
                                               rabbit.center_x, rabbit.center_y)
                if distance < self.perception_radius * self.perception_radius:
                    avg_velocity[0] += rabbit.velocity_x
                    avg_velocity[1] += rabbit.velocity_y
                    total += 1
        if total > 0:
            avg_velocity[0] /= total
            avg_velocity[1] /= total

            dir = [avg_velocity[0] - current_rabbit.velocity_x,
                        avg_velocity[1] - current_rabbit.velocity_y]
            return dir
        else:
            return [0, 0]
        
    def cohesion(self, current_rabbit):
        center_of_mass = [0, 0]
        total = 0
        nearby_rabbits = self.simulation.spatial_grid.get_nearby_sprites(current_rabbit.center_x, current_rabbit.center_y)
        for rabbit in nearby_rabbits:
            if rabbit is not current_rabbit:
                distance = get_square_distance(current_rabbit.center_x, current_rabbit.center_y,
                                               rabbit.center_x, rabbit.center_y)
                if distance < self.perception_radius * self.perception_radius:
                    center_of_mass[0] += rabbit.center_x
                    center_of_mass[1] += rabbit.center_y
                    total += 1
        if total > 0:
            center_of_mass[0] /= total
            center_of_mass[1] /= total

            direction = [center_of_mass[0] - current_rabbit.center_x,
                        center_of_mass[1] - current_rabbit.center_y]
            return direction
        else:
            return [0, 0]

    def avoid_predators(self, current_rabbit, deltatime):
        predators = self.simulation.predators
        dir = [0, 0]
        total = 0
        for predator in predators:
            square_distance = get_square_distance(current_rabbit.center_x, current_rabbit.center_y,
                                            predator.center_x, predator.center_y)
            if square_distance < self.perception_radius * self.perception_radius:
                diff_x = current_rabbit.center_x - predator.center_x
                diff_y = current_rabbit.center_y - predator.center_y
                distance = math.hypot(current_rabbit.center_x - predator.center_x, current_rabbit.center_y - predator.center_y)
                if square_distance > 0:
                    diff_x /= distance
                    diff_y /= distance
                dir[0] += diff_x
                dir[1] += diff_y
                total += 1
        if total > 0:
            dir[0] /= total
            dir[1] /= total
            current_rabbit.velocity_x += dir[0] * self.separation_weight * deltatime
            current_rabbit.velocity_y += dir[1] * self.separation_weight * deltatime


class PreySprite(arcade.Sprite, Animal):
    def __init__(self, posX, posY, bushes, grass_patches, simulation):
        super().__init__("images/entities/base-rabbit.png", 2)
        targets = arcade.SpriteList()
        targets.extend(bushes)
        targets.extend(grass_patches)
        Animal.__init__(self, targets, RABBIT_HUNGRY_INTERVAL, RABBIT_MOVEMENT_SPEED, 
                        RABBIT_RUNNING_SPEED, RABBIT_HEALTH, 1, False, RABBIT_REPRODUCTIVE_INTERVAL, 
                        simulation.preys, simulation.add_prey, simulation, LivingType.RABBIT, RABBIT_LIFE_EXPECTANCY)
        self.center_x = posX
        self.center_y = posY
        self.targets = targets
        self.simulation = simulation
        self.experience = {'forage_open': 0, 'forage_cover': 0}
        self.strategy = 'forage_open'

        self.velocity_x = 0
        self.velocity_y = 0

        self.highlight = False
        self.color = (255, 255, 255)

    def on_draw(self, highlight=False):
        Animal.on_draw(self)
        if highlight:
            self.draw_perception_circle()
    
    def draw_perception_circle(self):
        if self.simulation.is_debugging:
            arcade.draw_circle_outline(
                self.center_x, self.center_y,
                RABBIT_PERCEPTION_RADIUS,
                color=arcade.color.RED, 
                border_width=2 
            )
    
    def detect_predators(self):
        predators_nearby = [pred for pred in self.simulation.predators
                            if get_square_distance(self.center_x, self.center_y,
                                                   pred.center_x, pred.center_y) < DETECTION_RANGE * DETECTION_RANGE]
        return predators_nearby
    
    def update_strategy(self):
        predators_nearby = self.detect_predators()
        if predators_nearby:
            self.strategy = 'forage_cover'
        else:
            self.strategy = max(self.experience, key=self.experience.get)

    def calculate_payoff(self, delta_time):
        if self.strategy == 'forage_open':
            food_amount = 2
            predation_risk = 1
        else:
            food_amount = 1
            predation_risk = 0.5

        payoff = food_amount - predation_risk
        self.experience[self.strategy] += payoff * delta_time
    
    def update(self, delta_time):
        self.update_strategy()
        self.calculate_payoff(delta_time)

        if self.current_target_object is None:
            self.center_x += self.velocity_x * delta_time
            self.center_y += self.velocity_y * delta_time

        if self.center_x < 0 or self.center_x > SCREEN_WIDTH:
            self.velocity_x *= -1
        
        if self.center_y < 0 or self.center_y > SCREEN_HEIGHT:
            self.velocity_y *= -1
        
        current_life_expectancy_percentage = self.life_expectancy / RABBIT_LIFE_EXPECTANCY

        if current_life_expectancy_percentage < .4:
            current_color = int(max(100, min((current_life_expectancy_percentage + 0.6) * 255, 255)))
        else:
            current_color = 255

        self.color = (current_color, current_color, current_color)

        # self.center_x = max(0, min(self.center_x, SCREEN_WIDTH))
        # self.center_y = max(0, min(self.center_y, SCREEN_HEIGHT))

        Animal.update(self, delta_time)

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
        self.strategy = 'active_hunt'
        self.experience = {'active_hunt': 0, 'ambush': 0}
    
    def on_hungry(self, delta_time):
        self.update_strategy()

        if self.strategy == 'active_hunt':
            self.active_hunt(delta_time)
        elif self.strategy == 'ambush':
            self.ambush(delta_time)
    
    def active_hunt(self, delta_time):
        possible_targets = self.detect_prey()
        if not possible_targets:
            self.clear_state()
            return

        nearest_prey = min(possible_targets, key=lambda prey: get_square_distance(self.center_x, self.center_y, prey.center_x, prey.center_y))
        self.current_target_object = nearest_prey

        distance = get_square_distance(self.center_x, self.center_y, self.current_target_object.center_x, self.current_target_object.center_y)
        if distance < INTERACT_RANGE * INTERACT_RANGE and self.current_target_object.current_state != LivingBeingStates.DEAD:
            self.eat(delta_time, self.current_target_object)
        else:
            self.walk(delta_time, [self.current_target_object.center_x, self.current_target_object.center_y], running=True)

        if not self.current_target_object or self.current_target_object.current_state == LivingBeingStates.DEAD:
            self.clear_state()
    
    def ambush(self, delta_time):
        if not self.current_target_coord:
            self.set_ambush_position()

        distance = get_square_distance(self.center_x, self.center_y, self.current_target_coord[0], self.current_target_coord[1])
        if distance > 25:
            self.walk(delta_time, self.current_target_coord, running=False)
        else:
            possible_targets = self.detect_prey()
            for prey in possible_targets:
                prey_distance = get_square_distance(self.center_x, self.center_y, prey.center_x, prey.center_y)
                if prey_distance < INTERACT_RANGE * INTERACT_RANGE:
                    self.current_target_object = prey
                    self.eat(delta_time, self.current_target_object)
                    break
    
    def set_ambush_position(self):
        if self.simulation.open_areas:
            area = random.choice(self.simulation.open_areas)
            self.current_target_coord = [
                random.uniform(area.center_x - area.width / 2, area.center_x + area.width / 2),
                random.uniform(area.center_y - area.height / 2, area.center_y + area.height / 2)
            ]
        else:
            self.current_target_coord = [self.center_x, self.center_y]

    def detect_prey(self):
        preys_nearby = [prey for prey in self.simulation.preys
                        if get_square_distance(self.center_x, self.center_y,
                                               prey.center_x, prey.center_y) < DETECTION_RANGE * DETECTION_RANGE + 25]
        return preys_nearby

    def update_strategy(self):
        preys_nearby = self.detect_prey()
        if preys_nearby:
            self.strategy = 'active_hunt'
        else:
            self.strategy = max(self.experience, key=self.experience.get)
        
    def calculate_payoff(self, deltatime):
        if self.strategy == 'active_hunt':
            energy_spent = 1.5
            success_rate = 0.7
        else:
            energy_spent = 1
            success_rate = 0.5

        payoff = success_rate * 2 - energy_spent
        self.experience[self.strategy] += payoff * deltatime

    def update(self, delta_time):
        self.update_strategy()
        self.calculate_payoff(delta_time)

        current_life_expectancy_percentage = self.life_expectancy / FOX_LIFE_EXPECTANCY

        if current_life_expectancy_percentage < .4:
            current_color = int(max(100, min((current_life_expectancy_percentage + 0.6) * 255, 255)))
        else:
            current_color = 255

        self.color = (current_color, current_color, current_color)

        Animal.update(self, delta_time)
    
    def on_draw(self):
        Animal.on_draw(self)

class BushSprite(arcade.Sprite, Plant):
    def __init__(self, posX, posY, simulation):
        super().__init__("images/entities/base-bush.png", scale=2)
        Plant.__init__(self, PLANT_HEALTH, PLANT_REPRODUCTIVE_INTERVAL, simulation.add_bush, simulation, PLANT_LIFE_EXPECTANCY, LivingType.PLANT)
        self.center_x = posX
        self.center_y = posY

    def update(self, delta_time):
        Plant.update(self, delta_time)
    
    def on_draw(self):
        Plant.on_draw(self)
    
class GrassPatchSprite(arcade.Sprite, Plant):
    def __init__(self, posX, posY, simulation):
        super().__init__("images/entities/base-grass-half-2.png", scale=1)
        Plant.__init__(self, PLANT_HEALTH, PLANT_REPRODUCTIVE_INTERVAL, simulation.add_grass_patch, simulation, PLANT_LIFE_EXPECTANCY, LivingType.GRASS)
        self.center_x = posX
        self.center_y = posY
    
    def update(self, delta_time):
        Plant.update(self, delta_time)
    
    def on_draw(self):
        Plant.on_draw(self)
    
class CardSprite(arcade.Sprite): 
    def __init__(self, card_type_obj, simulation):
        card_scale = 1.5
        super().__init__(CARD_IMAGE, scale=card_scale, center_x=-1000, center_y=-1000)
        self.card_type_obj = card_type_obj
        self.simulation = simulation
        self.type = "CARD"
        self.fill_card_params()
        self.index = 0
        self.card_scale = card_scale
    
    def fill_card_params(self):
        self.title = self.card_type_obj["title"]
        self.description = self.card_type_obj["description"]
        self.cost = self.card_type_obj["cost"]
        self.usage = self.card_type_obj["usage"]
    
    def set_index(self, index):
        self.index = index
        self.center_x = ((self.index) * (128 + 20) + 20 + 128) * self.card_scale
        self.center_y = 128 * self.card_scale
    
    def have_enough_resource(self, resource):
        if resource in self.cost:
            if self.simulation.resources_collected[resource] < self.cost[resource]:
                return False
            
        return True
    
    def charge_resources(self, resource):
        if resource in self.cost:
            self.simulation.resources_collected[resource] -= self.cost[resource]

    def use(self):
        can_execute = True

        for type in CARD_COST_TYPES:
            can_execute = can_execute and self.have_enough_resource(type)

        if can_execute:
            for type in CARD_COST_TYPES:
                self.charge_resources(type)
            
            self.usage()
            print("using card")

            self.remove_from_sprite_lists()
            current_index = self.index

            for card in self.simulation.cards:
                if card.index > current_index:
                    card.set_index(card.index - 1)
        else:
            print("cannot use card now!")
    
    def cost_to_text(self):
        elements = []

        if "rabbit" in self.cost:
            elements.append(f"r:{self.cost['rabbit']}")
        
        if "fox" in self.cost:
            elements.append(f"f:{self.cost['fox']}")

        if "bush" in self.cost:
            elements.append(f"b:{self.cost['bush']}")
        
        if "grass" in self.cost:
            elements.append(f"g:{self.cost['grass']}")
        
        return " ".join(elements)

    def draw_overlays(self):
        # This method draws the text overlays. The sprite itself is drawn by the SpriteList.
        arcade.draw_text(f"{self.title}", self.center_x - 64 + 16, self.center_y + 40, arcade.color.BLACK, 15, anchor_x="center", width=128 - 32)
        arcade.draw_text(f"{self.description}", self.center_x - 64 + 16, self.center_y - 20, arcade.color.BLACK, 10, anchor_x="center", width=128 - 32)
        arcade.draw_text(f"{self.cost_to_text()}", self.center_x - 64 + 16, self.center_y - 95, arcade.color.BLACK, 10, anchor_x="center", width=128 - 32)

class Area:
    def __init__(self, center_x, center_y, width, height, area_type):
        self.center_x = center_x
        self.center_y = center_y
        self.width = width
        self.height = height
        self.area_type = area_type

    def contains(self, x, y):
        return (
            x >= self.center_x - self.width / 2 and
            x <= self.center_x + self.width / 2 and
            y >= self.center_y - self.height / 2 and
            y <= self.center_y + self.height / 2
        )

class EcosystemSimulator(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.ARMY_GREEN)
        self.spatial_grid = SpatialHashGrid(cell_size=RABBIT_PERCEPTION_RADIUS)
        self.plant_spatial_grid = SpatialHashGrid(cell_size=PLANT_NUTRIENT_RADIUS)

        self.entities = arcade.SpriteList()
        self.bushes = arcade.SpriteList()
        self.preys = arcade.SpriteList()
        self.predators = arcade.SpriteList()
        self.grass_patches = arcade.SpriteList()
        self.cards = arcade.SpriteList()

        self.open_areas = []
        self.covered_areas = []
        self.areas = []

        self.define_areas()

        self.initialize_bushes(50)
        self.initialize_grass_patches(75)
        self.initialize_preys(50)
        self.initialize_predators(4)
        self.initialize_cards()

        self.resources_collected = { "fox": 0, "rabbit": 0, "bush": 0, "grass": 0 }

        self.hide_cards = True
        self.is_debugging = False

        self.prey_social_controller = PreySocialController(self)
    
    def initialize_cards(self):
        card_number = 5
        card_type_obj = self.card_types_func()
        
        for i in range(card_number):
            card = self.get_random_card(card_type_obj)
            card.set_index(i)
            self.cards.append(card)
    
    def card_types_func(self):
        return {
            "create_rabbit": { 
                "title": "Criar coelhos",
                "description": "Cria 5 coelhos aleatoriamente no mapa",
                "cost": {"bush": 3},
                "usage": self.add_prey
            },
            "create_fox": {
                "title": "Criar raposa",
                "description": "Cria 1 raposa aleatoriamente no mapa",
                "cost": {"rabbit": 5},
                "usage": self.add_predator
            },
            "create_bush": {
                "title": "Criar arbusto",
                "description": "Adiciona 3 arbustos no mapa",
                "cost": {"grass": 2},
                "usage": self.add_bush
            },
            "create_grass": {
                "title": "Criar grama",
                "description": "Adiciona 10 porções de grama no mapa",
                "cost": {"bush": 15},
                "usage": self.add_grass_patch
            },
            "global_heal": {
                "title": "Cura global",
                "description": "Cura todos os animais no mapa",
                "cost": {"bush": 5, "grass": 3},
                "usage": self.global_heal
            },
            "hungry_rabbit": {
                "title": "Coelho faminto",
                "description": "Faz com que 3 coelhos se tornem famintos",
                "cost": {"grass": 1},
                "usage": self.make_rabbit_hungry
            }
        }

    def global_heal(self):
        animals = arcade.SpriteList()
        animals.extend(self.preys)
        animals.extend(self.predators)

        for animal in animals:
            if animal.current_state != LivingBeingStates.DEAD:
                animal.health = animal.initial_health

    def make_rabbit_hungry(self):
        animals = arcade.SpriteList()
        animals.extend(self.preys)

        animal_list = list(animals)
        random_rabbits = random.sample(animal_list, min(3, len(animal_list)))

        for rabbit in random_rabbits:
            rabbit.force_hungry()

    def get_random_card(self, card_type_obj):
        card_type = random.sample(CARD_TYPES, 1)[0]
        current_card_type_obj = card_type_obj[card_type]
        card = CardSprite(current_card_type_obj, self)
        return card
    
    def define_areas(self):
        grid_size_x = GRID_UNIT_X
        grid_size_y = GRID_UNIT_Y
        cell_width = SCREEN_WIDTH / grid_size_x
        cell_height = SCREEN_HEIGHT / grid_size_y

        for i in range(grid_size_x):
            for j in range(grid_size_y):
                area_type = random.choice(['open', 'covered'])
                center_x = (i + 0.5) * cell_width
                center_y = (j + 0.5) * cell_height
                area = Area(center_x, center_y, cell_width, cell_height, area_type)
                self.areas.append(area)
                if area_type == 'open':
                    self.open_areas.append(area)
                else:
                    self.covered_areas.append(area)

    def initialize_bushes(self, bush_number):
        num_clusters = bush_number // 5
        for _ in range(num_clusters):
            self.add_bush()
    
    def initialize_preys(self, preys_number):
        for _ in range(preys_number):
            self.add_prey()

    def initialize_predators(self, predators_number):
        for _ in range(predators_number):
            self.add_predator()
    
    def initialize_grass_patches(self, grass_number):
        for _ in range(grass_number):
            self.add_grass_patch()
    
    def add_grass_patch(self):
        if not self.open_areas:
            return
    
        area = random.choice(self.open_areas)
        posX = random.uniform(area.center_x - area.width / 2, area.center_x + area.width / 2)
        posY = random.uniform(area.center_y - area.height / 2, area.center_y + area.height / 2)
        grass_patch = GrassPatchSprite(posX, posY, self)
        self.grass_patches.append(grass_patch)
        self.entities.append(grass_patch)

        self.plant_spatial_grid.add_sprite(grass_patch)

    def add_bush(self):
        # posX, posY = randomIntXY([1, SCREEN_WIDTH - 1], [1, SCREEN_HEIGHT - 1])
        # bush = BushSprite(posX, posY, self)
        # self.bushes.append(bush)
        # self.entities.append(bush)

        area_type_choice = random.choices(['covered', 'open'], weights=[0.9, 0.1])[0]
        if area_type_choice == 'open' and self.open_areas:
            area = random.choice(self.open_areas)
        elif self.covered_areas:
            area = random.choice(self.covered_areas)
        else:
            return
    
        cluster_center_x = random.uniform(area.center_x - area.width / 4, area.center_x + area.width / 4)
        cluster_center_y = random.uniform(area.center_y - area.height / 4, area.center_y + area.height / 4)

        for _ in range(random.randint(3, 7)):
            posX = random.gauss(cluster_center_x, area.width / 7)
            posY = random.gauss(cluster_center_y, area.height / 7)

            can_add_plant = self.can_add_plant(posX, posY)
            if not can_add_plant:
                return

            bush = BushSprite(posX, posY, self)
            self.bushes.append(bush)
            self.entities.append(bush)
            self.plant_spatial_grid.add_sprite(bush)
    
    def can_add_plant(self, pos_x, pos_y):
        plants_nearby = self.plant_spatial_grid.get_nearby_sprites(pos_x, pos_y)
        if len(plants_nearby) > 5:
            return False

        return True
    
    def add_prey(self, coords=None):
        if coords:
            posX, posY = coords
        else:
            posX, posY = random_int_xy([1, SCREEN_WIDTH - 1], [1, SCREEN_HEIGHT - 1])

        prey = PreySprite(posX, posY, self.bushes, self.grass_patches, self)
        self.preys.append(prey)
        self.entities.append(prey)
    
    def add_predator(self, coords=None):
        if coords:
            posX, posY = coords
        else:
            posX, posY = random_int_xy([1, SCREEN_WIDTH - 1], [1, SCREEN_HEIGHT - 1])

        predator = PredatorSprite(posX, posY, self)
        self.entities.append(predator)
        self.predators.append(predator)

    def on_draw(self):
        arcade.get_window().clear()

        # In new Arcade, we draw the whole list at once.
        self.entities.draw(pixelated=True)

        # Now draw the custom overlays on top of the sprites.
        if self.preys:
            first_rabbit = self.preys[0]
            if self.is_debugging:
                first_rabbit.draw_perception_circle()

        # Draw health bars and needs icons for all entities
        for entity in self.entities:
            entity.on_draw()

        # Draw cards and their text overlays
        if not self.hide_cards:
            self.cards.draw()
            for card in self.cards:
                card.draw_overlays() 

        # Draw UI elements
        arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, SCREEN_HEIGHT - 50, SCREEN_HEIGHT, (0, 0, 0, 150))
        arcade.draw_text(f"r (rabbit): {self.resources_collected['rabbit']}, f (fox): {self.resources_collected['fox']}, b (bush): {self.resources_collected['bush']}, g (grass): {self.resources_collected['grass']}",
                        15, SCREEN_HEIGHT - 35, arcade.color.WHITE, 20)
        
        self.draw_key_instructions()
    
    def draw_key_instructions(self):
        instructions = [
            "Controls:",
            "H - Toggle cards and stats visibility",
            "D - Toggle one rabbit perception range",
            "Mouse left click - Collect resource"
        ]
        
        start_x = 10
        start_y = SCREEN_HEIGHT - 80
        line_height = 20
        
        # Draw a background box for the instructions
        arcade.draw_lrbt_rectangle_filled(5, 300, SCREEN_HEIGHT - 175, SCREEN_HEIGHT - 75, (0, 0, 0, 150))

        for i, line in enumerate(instructions):
            arcade.draw_text(
                line,
                start_x,
                start_y - i * line_height,
                arcade.color.WHITE,
                14,
                bold=True
            )
        
        if len(self.entities) == 0:
            start_x = SCREEN_WIDTH / 2
            start_y = SCREEN_HEIGHT / 2

            arcade.draw_text(
                "Game Over",
                start_x,
                start_y,
                arcade.color.WHITE,
                28,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )
        
    def on_update(self, delta_time):
        self.spatial_grid.clear()
        for prey in self.preys:
            self.spatial_grid.add_sprite(prey)
        self.entities.update()
        self.prey_social_controller.update(delta_time)
    
    def on_mouse_press(self, x, y, button, modifiers):
        cards_clicked = arcade.get_sprites_at_point((x, y), self.cards)
        
        if not self.hide_cards:
            for card in cards_clicked:
                card.use()
                return

        sprites_clicked = arcade.get_sprites_at_point((x, y), self.entities)

        if len(sprites_clicked) > 0:
            sprite_clicked = sorted(sprites_clicked, key=lambda entity: entity.bottom, reverse=False)[0]
        else:
            sprite_clicked = None
        
        if sprite_clicked is not None:
            if sprite_clicked.type == LivingType.RABBIT:
                self.resources_collected["rabbit"] += 1
            
            if sprite_clicked.type == LivingType.FOX:
                self.resources_collected["fox"] += 1
            
            if sprite_clicked.type == LivingType.PLANT:
                self.resources_collected["bush"] += 1
            
            if sprite_clicked.type == LivingType.GRASS:
                self.resources_collected["grass"] += 1

            sprite_clicked.remove_from_sprite_lists()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.H:
            self.hide_cards = not self.hide_cards
        
        if key == arcade.key.D:
            self.is_debugging = not self.is_debugging

class SpatialHashGrid:
    def __init__(self, cell_size):
        self.cell_size = cell_size
        self.grid = {}

    def clear(self):
        self.grid.clear()

    def add_sprite(self, sprite):
        key = self._get_cell_key(sprite.center_x, sprite.center_y)
        if key not in self.grid:
            self.grid[key] = []
        self.grid[key].append(sprite)

    def get_nearby_sprites(self, x, y):
        key = self._get_cell_key(x, y)
        nearby_sprites = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                neighbor_key = (key[0] + dx, key[1] + dy)
                if neighbor_key in self.grid:
                    nearby_sprites.extend(self.grid[neighbor_key])
        return nearby_sprites

    def _get_cell_key(self, x, y):
        return (int(x // self.cell_size), int(y // self.cell_size))

# utils functions
def get_square_distance(center_x, center_y, target_center_x, target_center_y):
        dx = center_x - target_center_x
        dy = center_y - target_center_y
        return dx * dx + dy * dy 

def random_int_xy(limitRangeX, limitRangeY):
    lowerLimitRangeX, upperLimitRangeX = limitRangeX
    lowerLimitRangeY, upperLimitRangeY = limitRangeY

    return random.randint(lowerLimitRangeX, upperLimitRangeX), random.randint(lowerLimitRangeY, upperLimitRangeY) 

def limit_vector(vector, max_value):
    magnitude = math.hypot(vector[0], vector[1])
    if magnitude > max_value:
        vector[0] = (vector[0] / magnitude) * max_value
        vector[1] = (vector[1] / magnitude) * max_value

if __name__ == '__main__':
    app = EcosystemSimulator()
    arcade.run()