import pygame
import sys

# 1. Initialize Pygame and Setup Window
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_center = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pygame Following Bot Example")
clock = pygame.time.Clock()

# Color Definitions
WHITE = (255, 255, 255)
BLUE = (50, 150, 255)    # Player
RED = (255, 100, 100)    # Bot

# 2. Position Vector Setup
# Using pygame.math.Vector2 handles tracking and angles automatically
player_pos = pygame.math.Vector2(400, 300)
bot_pos = pygame.math.Vector2(100, 100)

# Movement Speeds
PLAYER_SPEED = 5
BOT_SPEED = 3

# Main Game Loop
while True:
    # Handle Window Closing
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    # 3. Handle Player Movement (WASD / Arrows)
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        player_pos.x -= PLAYER_SPEED
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        player_pos.x += PLAYER_SPEED
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        player_pos.y -= PLAYER_SPEED
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        player_pos.y += PLAYER_SPEED

    # 4. MATH: Make the Bot Follow the Player
    # Create a vector pointing from the bot directly to the player
    direction = player_pos - bot_pos
    
    # Calculate the pixel distance between them
    distance = direction.length()

    if distance > 0:
        # Normalize the vector (shrink its total length down to 1)
        # This keeps the bot's speed constant regardless of how far away it is
        direction.normalize_ip()
        
        # Move the bot along that normalized vector line at its target speed
        bot_pos += direction * BOT_SPEED

    # 5. Render Everything On Screen
    screen.fill(WHITE)
    
    # Draw Player (Blue Circle)
    pygame.draw.circle(screen, BLUE, (int(player_pos.x), int(player_pos.y)), 20)
    
    # Draw Bot (Red Circle)
    pygame.draw.circle(screen, RED, (int(bot_pos.x), int(bot_pos.y)), 15)

    pygame.display.flip()
    clock.tick(60) # Keep game at a smooth 60 frames per second
