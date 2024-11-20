### PRE-SETUP ###
import pygame, sys, random, math
pygame.mixer.pre_init(44100, -16, 2, 512)
clock = pygame.time.Clock()

from pygame.locals import *;
pygame.init() #initiates pygame
pygame.mixer.set_num_channels(64)

### PYGAME ###
pygame.display.set_caption("Kav's 2D Platformer")

WINDOW_SIZE = (600,400)

screen  = pygame.display.set_mode(WINDOW_SIZE,0,32) #initiate window

display = pygame.Surface((300, 200))

background_color = (146, 244, 255)  # Original background color

moving_right = False
moving_left = False

player_y_momentum = 0
air_timer = 0
player_altitude = 0

true_scroll = [0, 0] # camera

CHUNK_SIZE = 8

#Chunk generation
def generate_chunk(x, y):
    chunk_data = []
    #8x8 chunk
    for y_pos in range(CHUNK_SIZE):
        for x_pos in range(CHUNK_SIZE):
            target_x = x * CHUNK_SIZE  + x_pos
            target_y = y * CHUNK_SIZE  + y_pos
            tile_type = 0 # air (staring from (0,0) top left)
            
            if random.randint(1, 20) == 1 and target_y < 10:  # Adjust the probability and height range as needed
                platform_width = random.randint(3, 6)  # Random width of the platform
                for platform_x in range(platform_width):
                    chunk_data.append([[target_x + platform_x, target_y], 1])  # 1 represents the grass tile type

            if target_y > 10: 
                tile_type = 2 #dirt
            elif target_y == 10:
                tile_type = 1 #grass
            elif target_y == 9:
                if random.randint(1, 5) == 1: 
                    tile_type = 3 # grass
            if tile_type != 0:
                chunk_data.append([[target_x, target_y],tile_type])
    return chunk_data


global animation_frames
animation_frames = {}

#loading animation sprites
def load_animation(path, frame_durations):
    global animation_frames
    animation_name = path.split('/')[-1]
    animation_frame_data = []
    n = 0
    for frame in frame_durations:
        #sprite swaps
        animation_frame_id = animation_name + '_' +str(n) # iterate between sprites
        img_loc = path + '/' +animation_frame_id +'.png'
        animation_image = pygame.image.load(img_loc).convert()
        animation_image.set_colorkey((255,255,255))
        animation_frames[animation_frame_id] = animation_image.copy()
        for i in range(frame):
            animation_frame_data.append(animation_frame_id)
        n += 1
    return animation_frame_data

#sprite changes between idle and run
def change_action(action_var,frame,new_value):
    if action_var != new_value:
        action_var = new_value
        frame = 0
    return action_var,frame

animation_database = {}

# LOADING #
animation_database['run'] = load_animation('player_animations/run', [7,7]) 
animation_database['idle'] = load_animation('player_animations/idle', [7,7,40]) 

game_map = {}

player_image = pygame.image.load('images/player.png').convert()
player_image.set_colorkey((255, 255, 255))
grass_image = pygame.image.load('images/grass.png')
dirt_image = pygame.image.load('images/dirt.png')
plant_image = pygame.image.load('images/plant.png').convert()
plant_image.set_colorkey((255, 255, 255))

tile_index = {1: grass_image, 
              2:dirt_image, 
              3: plant_image}

jump_sound = pygame.mixer.Sound('audio\jump.wav')
jump_sound.set_volume(0.35)
grass_sounds = [pygame.mixer.Sound('audio\grass_0.wav'), pygame.mixer.Sound('audio\grass_1.wav')]
grass_sounds[0].set_volume(0.22)
grass_sounds[1].set_volume(0.22)

pygame.mixer.music.load('audio\music.wav')
pygame.mixer.music.set_volume(0.7)
pygame.mixer.music.play(-1) # repeat infinite

#sprite control
player_action = 'idle'
player_frame = 0
player_flip = False

#sound control
grass_sound_timer = 0
#player
player_rect = pygame.Rect(50, 50,
                          player_image.get_width(),player_image.get_height())

TILE_SIZE = grass_image.get_width()

background_objects = [[0.25,[120,10,70,400]],[0.25,[280,30,40,400]],[0.5,[30,40,40,400]],[0.5,[130,90,100,400]],[0.5,[300,80,120,400]]]

def collision_test(rect, tiles): #collision checker
    hit_list = []
    for tile in tiles:
        if rect.colliderect(tile):
            hit_list.append(tile)
    return hit_list

def move(rect, movement, tiles):
    collision_types = {'top': False, 'bottom': False, 'right': False, 'left': False}
    rect.x += movement[0]
    hit_list = collision_test(rect, tiles)
    for tile in hit_list:
        if movement[0] > 0: #moving right
            rect.right = tile.left
            collision_types['right'] = True
        elif movement[0] < 0: #moving left
            rect.left = tile.right
            collision_types['left'] = True
    rect.y +=movement[1]
    hit_list = collision_test(rect, tiles)
    for tile in hit_list:
        if movement[1] > 0: # moving down
            rect.bottom = tile.top
            collision_types['bottom'] = True
        elif movement[1] < 0: # moving up
            rect.top = tile.bottom
            collision_types['top'] = True
    return rect, collision_types

max_height = player_rect.y 
score = 0

background_color = (146, 244, 255)  # Original background color

while True: #game loop

    display.fill(background_color) # screen colour  
     
    if grass_sound_timer > 0:
        grass_sound_timer -= 1

    #camera pan - follow player
    true_scroll[0] += (player_rect.x-true_scroll[0]-152)/20 #screen is 300 pixels, middle is 150, player 5px (so middle of player 2.5)
    true_scroll[1] += (player_rect.y-true_scroll[1]-106)/20
    scroll = true_scroll.copy()
    scroll[0] = int(scroll[0])
    scroll[1] = int(scroll[1])

    #background layers
    pygame.draw.rect(display,(7,80,75),pygame.Rect(0,120,300,80))
    sun_radius = 30
    sun_distance = 60
    sun_color = (255, 255, 0)  # Yellow color for the sun
    sun_position = (250, 33)
    pygame.draw.circle(display, sun_color, sun_position, sun_radius)

    #score
    score = max(0, max_height - player_rect.y)  
    score_color = (255, 255, 255)  # White color for score text

    #fill map
    tile_rects = []

    #TILE RENDERING #
    for y in range(3):
        for x in range(4):
            #calculate chuk id's visible on screen
            target_x = x - 1 + int(round(scroll[0]/(CHUNK_SIZE*16)))
            target_y = y - 1 + int(round(scroll[1]/(CHUNK_SIZE*16)))
            target_chunk = str(target_x) + ';' + str(target_y) #"num;num"

            if target_chunk not in game_map: # generate chunk if it doesnt exist yet
                game_map[target_chunk] = generate_chunk(target_x, target_y)

            for tile in game_map[target_chunk]:
                display.blit(tile_index[tile[1]], (tile[0][0]*16-scroll[0], tile[0][1]*16-scroll[1]))
                if tile[1]  in [1, 2]:  #if grass or dirt
                    tile_rects.append(pygame.Rect(tile[0][0]*16, tile[0][1]*16, 16, 16))

    # player movement and gravity acccounting
    player_movement = [0, 0]
    if moving_right:
        player_movement[0] += 2
    if moving_left:
        player_movement[0] -= 2
    player_movement[1] += player_y_momentum
    player_y_momentum += 0.2
    if player_y_momentum > 3: #max free-fall amount 
        player_y_momentum = 3

    #sprite changes
    if player_movement[0] == 0:
        player_action,player_frame = change_action(player_action,player_frame,'idle')
    if player_movement[0] > 0:
        player_flip = False
        player_action,player_frame = change_action(player_action,player_frame,'run')
    if player_movement[0] < 0:
        player_flip = True
        player_action,player_frame = change_action(player_action,player_frame,'run')

    player_rect, collisions = move(player_rect, player_movement, tile_rects)

    #landing-jump fix
    if collisions['bottom']:
        player_y_momentum = 0
        air_timer = 0
        if player_movement[0] != 0: #if moving
            if grass_sound_timer == 0:
                grass_sound_timer = 30
                random.choice(grass_sounds).play()
    else:
        air_timer += 1
    
    #headglitch fix
    if collisions['top']:
        player_y_momentum = 0.5 

    #flip between sprites
    player_frame += 1
    if player_frame >= len(animation_database[player_action]):
        player_frame = 0
    player_img_id = animation_database[player_action][player_frame]
    player_img = animation_frames[player_img_id]
    #render player, changes based on action and frame
    display.blit(pygame.transform.flip(player_img,player_flip,False),(player_rect.x-scroll[0],player_rect.y-scroll[1]))
    
    player_altitude = max(player_altitude, int(-player_rect.y))  # Update player altitude
    font = pygame.font.Font(None, 36)  # Choose a font and size
    score_text = font.render(str(score), True, (score_color))  # Render score text
    display.blit(score_text, (10, 10))  # Display score text on the screen

    for event in pygame.event.get():
        if event.type == QUIT: # upon window-close
            pygame.quit()
            sys.exit()
        # Key inputs
        if event.type == KEYDOWN: # key press-down
            if event.key == K_RIGHT:
                moving_right = True
            if event.key == K_LEFT:
                moving_left = True
            if event.key == K_UP:
                if air_timer < 6:
                    player_y_momentum = -5
                    jump_sound.play()
                    
        if event.type == KEYUP:
            if event.key == K_RIGHT:
                moving_right = False
            if event.key == K_LEFT:
                moving_left = False

    surf = pygame.transform.scale(display, WINDOW_SIZE)
    screen.blit(surf, (0, 0))
    pygame.display.update()
    clock.tick(60) # framerate 

