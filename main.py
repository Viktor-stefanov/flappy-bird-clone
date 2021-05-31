import pygame
import random
import pickle
import neat
import sys
import os
from score_actions import *

pygame.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 600, 800
surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Flappy Bird Clone")

icon = pygame.image.load(os.path.join("img", "icon.png"))
pygame.display.set_icon(icon)

background_img = pygame.transform.scale(pygame.image.load(os.path.join("img", "bg.png")).convert_alpha(), (1000, 800))
base_img = pygame.transform.scale(pygame.image.load(os.path.join("img", "base.png")).convert_alpha(), (1000, 112))
bird_imgs = [pygame.transform.scale(pygame.image.load(fr"img\bird{n}.png").convert_alpha(), (60, 40)) for n in range(1, 4)]
bird_imgs.extend([pygame.transform.scale(pygame.image.load(fr"img\bird{n}.png").convert_alpha(), (60, 40)) for n in range(2, 0, -1)])
pipe_img = pygame.image.load(os.path.join("img", "pipe.png")).convert_alpha()
restart_img = pygame.image.load(os.path.join("img", "restart_button.png")).convert_alpha()
menu_img = pygame.transform.scale(pygame.image.load(os.path.join("img", "menu.png")).convert_alpha(), (300, 400))
menu_img.set_colorkey((255, 255, 255))

score_font = pygame.font.SysFont("ComicSansMS", 40)

class Bird:
    """ bird class represents the player bird """
    imgs = bird_imgs
    def __init__(self, x, y):
        self.velocity = 1
        self.current_animation = 0
        self.animation_delay = 0
        self.fitness = 0
        self.x = x
        self.y = y
        self.tilt = 0
        self.tilt_delay = 0
        self.jump_ticks = -102
        self.jump_direction = 0

    def move(self):
        # if the bird is titled downwards increase the speed - OBVIOUSLY
        if self.tilt < 0:
            self.velocity = 5 + (self.tilt * -0.05)
        self.y += self.velocity

        # if the bird is not jumping and is headed downwards (hence self.velocity > 0 [positive -> down]) tilt it :D
        if self.velocity > 0 and self.tilt > -90 and self.jump_ticks == -16:
            if self.tilt_delay > 12:
                self.tilt -= 6.25
            self.tilt_delay += 1
        # reset the tilt delay on maximally tilting the bird
        if self.tilt == -95:
            self.tilt_delay = 0

        # handle jumping
        if self.jump_ticks >= -15:
            if self.jump_ticks < 0:
                self.velocity = -5 * (self.jump_ticks * 0.1)
            else:
                self.velocity = -5 * (self.jump_ticks * 0.15)
            self.jump_ticks += 1 * self.jump_direction

    def animate(self):
        self.animation_delay += 1
        if self.animation_delay == 10:
            if self.tilt == -95:
                self.current_animation = -1
            self.current_animation = (self.current_animation + 1) % len(self.imgs)
            self.animation_delay = 0

    def jump(self):
        self.tilt_delay = 0
        self.tilt = 30
        self.current_animation = 0
        self.jump_ticks = 15
        self.jump_direction = -1 # -1 = up, 1 = down

    def get_mask(self):
        current_img = self.imgs[self.current_animation]
        tilted_img = pygame.transform.rotate(current_img, self.tilt)
        mask = pygame.mask.from_surface(tilted_img)
        return mask

    def draw(self, win):
        self.fitness += 1
        current_img = self.imgs[self.current_animation]
        # rotate the image and make it's rect's center to the non-rotated image's center so the collision works better
        rotated_image = pygame.transform.rotate(current_img, self.tilt)
        rotated_image_rect = rotated_image.get_rect(center=current_img.get_rect(topleft=(self.x, self.y)).center)
        win.blit(rotated_image, rotated_image_rect)


class Pipes:
    img = pipe_img
    def __init__(self, other_pipe=None):
        self.x = SCREEN_WIDTH
        self.bottom_height = random.randint(50, 400)
        self.bottom_y = SCREEN_HEIGHT - self.bottom_height - base_img.get_height()
        self.bottom_pipe = pygame.transform.scale(self.img, (100, self.bottom_height))
        self.top_y = 0
        self.top_height = self.bottom_y - (bird_imgs[0].get_height() * 4)
        self.top_pipe = pygame.transform.scale(pygame.transform.flip(self.img, False, True), (100, self.top_height))
        self.passed = False

    def move(self):
        self.x -= 5

    def distance_to_poles(self, bird):
        top_distance_coords = (abs(bird.x - self.x), abs(bird.y - self.top_pipe.get_height()))
        bottom_distance_coords = (abs(bird.x - self.x), abs(bird.y - self.bottom_y))

        top_distance = int(sum(top_distance_coords) / len(top_distance_coords))
        bottom_distance = int(sum(bottom_distance_coords) / len(bottom_distance_coords))

        return top_distance, bottom_distance

    def collides_with_bird(self, bird):
        bird_mask = bird.get_mask()
        bottom_mask = pygame.mask.from_surface(self.bottom_pipe)
        top_mask = pygame.mask.from_surface(self.top_pipe)

        top_offset = (self.x - bird.x, self.top_y - round(bird.y) + 5)
        bottom_offset = (self.x - bird.x, self.bottom_y - round(bird.y) + 8)

        top_collision = bird_mask.overlap(top_mask, top_offset)
        bottom_collision = bird_mask.overlap(bottom_mask, bottom_offset)

        if top_collision or bottom_collision:
            return True

    def draw(self, win):
        win.blit(self.top_pipe, (self.x, self.top_y))
        win.blit(self.bottom_pipe, (self.x, self.bottom_y))


class Base:
    """ background class that represents the side scrolling background that never ends.
    This is achieved by blitting 2 backgrounds simultaneously moving left """
    img = base_img
    def __init__(self):
        self.velocity = 5
        self.x = 0
        self.y = 688
        self.x_2 = self.img.get_width()

    def move(self):
        # move the base img to the left and once it is out to the left by the img width move it maximally to the right so it looks like it never ends
        self.x -= self.velocity
        self.x_2 -= self.velocity
        if self.x < self.img.get_width() * -1:
            self.x = self.img.get_width() - self.velocity
        if self.x_2 < self.img.get_width() * -1:
            self.x_2 = self.img.get_width() - self.velocity

    def draw(self, win):
        win.blit(self.img, (self.x, 688))
        win.blit(self.img, (self.x_2, 688))

def respawn_menu(win, scr, hs):
    score_label_position = (SCREEN_WIDTH // 2.4, 160)
    score_label = score_font.render("score:", False, (242, 92, 51))
    score_position = (SCREEN_WIDTH // 2.1, 205)
    score = score_font.render(str(scr), False, (255, 255, 255))
    high_score_label_position = (SCREEN_WIDTH // 2.9, 250)
    high_score_label = score_font.render("high score:", False, (242, 92, 51))
    high_score_position = (SCREEN_WIDTH // 2.1, 295)
    high_score = score_font.render(str(hs), False, (255, 255, 255))
    restart_position = (SCREEN_WIDTH // 2.6, 400)
    menu_label_position = (SCREEN_WIDTH // 4, 120)

    win.blit(menu_img, menu_label_position)
    win.blit(score_label, score_label_position)
    win.blit(score, score_position)
    win.blit(high_score_label, high_score_label_position)
    win.blit(high_score, high_score_position)
    restart_button = win.blit(restart_img, restart_position)
    pygame.display.update()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(), sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit(), sys.exit()
                # use the enter key as a restart button as well
                elif event.key in (pygame.K_RETURN, pygame.K_r):
                    play_game(win)
                elif event.key == pygame.K_m:
                    main_menu(win)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == pygame.BUTTON_LEFT:
                    # check if the user clicked on restart
                    mouse_pos = pygame.mouse.get_pos()
                    click = restart_button.collidepoint(mouse_pos[0], mouse_pos[1])
                    if click != 0:
                        play_game(win)

def redraw_window(win, bird, base, pipes, score=None):
    # redraw all the changes to the screen and update it
    win.blit(background_img, (0, 0))
    for pipe in pipes:
        pipe.draw(win)
    if score is not None:
        win.blit(score, (250, 100))
    base.draw(win)
    bird.draw(win)
    pygame.display.update()

def play_game(win):
    # create a 'clock' object to manipulate how fast/slow the in-game time passes
    clock = pygame.time.Clock()
    # create a sprite group to hold all the images that are on the screen
    # hard code the bird (x, y) pos (I feel like that's justified because the screen size is fixed. Create the player bird object
    bird_x = 150
    bird_y = 380
    bird = Bird(bird_x, bird_y)
    # create the first pipes and a pipes group
    pipes = [Pipes()]
    # create the base
    base = Base()
    game_started = False
    score = 0
    # create the main game loop
    while True:
        # fetch all the events and check for specific keypresses, etc...
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(), sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit(), sys.exit()
                elif event.key == pygame.K_SPACE:
                    bird.jump()
                    game_started = True
                elif event.key == pygame.K_m:
                    main_menu(win)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == pygame.BUTTON_LEFT:
                    bird.jump()
                    game_started = True

        if game_started is True:
            for pipe in pipes:
                pipe.move()
                # check if the bird has passed a pipe
                if pipe.x < bird.x and pipe.passed is False:
                    pipe.passed = True
                    score += 1
                    pipes.append(Pipes())
                # check if a pipe has left the screen
                if pipe.x <= 0 - pipe.top_pipe.get_width():
                    pipes.remove(pipe)
                # check for collisions between the bird and the pipes
                hits = pipe.collides_with_bird(bird)
                fall = bird.y + bird_imgs[0].get_height() >= base.y
                if True in (hits, fall):
                    # get the high score and update it if the current score is higher
                    high_score = get_high_score()
                    if score > high_score:
                        high_score = score
                        update_high_score(str(score))

                    respawn_menu(win, score, high_score)

            bird.animate()
            bird.move()
            base.move()

            score_render = score_font.render(str(score), False, (255, 255, 255))
            redraw_window(win, bird, base, pipes, score_render)
        else:
            if bird.y == 390:
                bird.velocity = -bird.velocity
            elif bird.y == 360:
                bird.velocity = -bird.velocity
            bird.move()

            redraw_window(win, bird, base, pipes)

        clock.tick(60)

def redraw_ai_window(win, birds, pipes, base):
    win.blit(background_img, (0, 0))
    base.draw(win)
    for pipe_pair in pipes:
        pipe_pair.move()
        pipe_pair.draw(win)
    for bird in birds:
        bird.draw(win)
    pygame.display.update()

def eval_genome(genome, config):
    # clear the screen up to this point
    surface.fill((0, 0, 0))
    clock = pygame.time.Clock()

    net = neat.nn.FeedForwardNetwork.create(genome, config)
    birds = [Bird(150, 380) for _ in range(50)]
    pipes = [Pipes()]
    base = Base()
    fitnesses = []

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(), sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit(), sys.exit()

        for bird in birds:
            bird.move()
            bird.animate()
            for pipe_pair in pipes:
                if pipe_pair.passed is False:
                    top_distance, bottom_distance = pipe_pair.distance_to_poles(bird)
                    inputs = [bird.y, top_distance, bottom_distance]
                    action = net.activate(inputs)[0]

                    if action == 1.0:
                        bird.jump()

                if bird.x >= pipe_pair.x:
                    pipe_pair.passed = True

                collision = pipe_pair.collides_with_bird(bird)
                if collision is True:
                    fitnesses.append(bird.fitness)
                    birds.remove(bird)
            fall = bird.y + bird.imgs[0].get_height() >= base.y
            if fall is True:
                fitnesses.append(bird.fitness)
                birds.remove(bird)

        base.move()
        redraw_ai_window(surface, birds, pipes, base)
        clock.tick(60)

def eval_genomes(genomes, config):
    for genome_id, genome in genomes:
        eval_genome(genome, config)

def run():
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, "config")
    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         config_path)

    pop = neat.Population(config)
    stats = neat.StatisticsReporter()
    pop.add_reporter(stats)
    pop.add_reporter(neat.StdOutReporter(True))

    winner = pop.run(eval_genomes, 300)

    # Save the winner.
    with open('winner-feedforward', 'wb') as f:
        pickle.dump(winner, f)

    print(winner)

def main_menu(win):
    menu_pos = (SCREEN_WIDTH // 4, SCREEN_HEIGHT // 5)
    play_game_pos = (SCREEN_WIDTH // 2.8, SCREEN_HEIGHT // 3.5)
    play_game_opt = score_font.render("Play Game", False, (242, 92, 51))
    ai_game_pos = (SCREEN_WIDTH // 3.15, SCREEN_HEIGHT // 2.2)
    ai_game = score_font.render("Let A.I. play", False, (242, 92, 51))

    win.blit(background_img, (0, 0))
    win.blit(menu_img, menu_pos)
    play = win.blit(play_game_opt, play_game_pos)
    ai_play = win.blit(ai_game, ai_game_pos)
    pygame.display.update()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == pygame.BUTTON_LEFT:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    if play.collidepoint(mouse_x, mouse_y):
                        play_game(win)
                    elif ai_play.collidepoint(mouse_x, mouse_y):
                        run()
            elif event.type == pygame.QUIT:
                pygame.quit(), sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit(), sys.exit()


if __name__ == "__main__":
    main_menu(surface)