import pygame
import sys
import random

pygame.init()

# ============================================================
# 1. SETTINGS
# ============================================================

TILE = 36
HUD_WIDTH = 230
MARGIN = 20
FPS = 60

BACKGROUND = (19, 28, 43)
PANEL = (28, 40, 58)
WALL = (65, 78, 96)
WALL_EDGE = (115, 130, 150)
PATH = (226, 211, 174)
PLAYER_COLOR = (30, 135, 245)
PLAYER_SKIN = (173, 112, 74)
ENEMY_COLOR = (210, 55, 65)
GOAL = (62, 190, 104)
WHITE = (240, 244, 250)
MUTED = (178, 191, 208)
GOLD = (255, 215, 110)
BULLET_COLOR = (255, 225, 80)

# Health settings
MAX_HEALTH = 4
HIT_COOLDOWN_MS = 1000  # Brief protection after taking damage.

font = pygame.font.SysFont("arial", 22)
small_font = pygame.font.SysFont("arial", 17)
large_font = pygame.font.SysFont("arial", 32, bold=True)

# ============================================================
# 2. MAZE DEFINITIONS
# ============================================================

# # = wall, . = path, S = start, E = exit

MAZES = {
    "Easy": [
        "############",
        "#S.........#",
        "#.####.###.#",
        "#......#...#",
        "######.#.###",
        "#......#...#",
        "#.########.#",
        "#........#E#",
        "############",
    ],

    "Medium": [
        "################",
        "#S....#........#",
        "#.##..#.######.#",
        "#.#...#......#.#",
        "#.#.###.###..#.#",
        "#.#.....#....#.#",
        "#.#######.####.#",
        "#......#.#....##",
        "#####..#...##..#",
        "#....#.#.#.....#",
        "#.###..#.#.###.#",
        "#.#....#...#...#",
        "#.#.##.#####.#.#",
        "#...#........#E#",
        "################",
    ],

    "Hard": [
        "####################",
        "#S.....#...........#",
        "#####..#.#########.#",
        "#......#.....#.....#",
        "#.#########..#.###.#",
        "#.........#..#...#.#",
        "#.#######.####.#.#.#",
        "#.#.....#......#.#.#",
        "#.#.###.########.#.#",
        "#...#...#........#.#",
        "###.#.###.########.#",
        "#...#.....#........#",
        "#.#########.######.#",
        "#.........#......#.#",
        "#.#######.######.#.#",
        "#.......#........#E#",
        "####################",
    ],
}

ENEMY_COUNTS = {
    "Easy": 2,
    "Medium": 4,
    "Hard": 7,
}

ENEMY_MOVE_DELAY = 650

# ============================================================
# 3. WINDOW AND GAME STATE
# ============================================================

MAX_COLS = max(
    len(row)
    for maze in MAZES.values()
    for row in maze
)
MAX_ROWS = max(len(maze) for maze in MAZES.values())

WIDTH = 2 * MARGIN + MAX_COLS * TILE + HUD_WIDTH
HEIGHT = 2 * MARGIN + MAX_ROWS * TILE

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Maze Runner: Enemy Challenge")
clock = pygame.time.Clock()

game_state = "menu"
difficulty = None
MAZE = None
ROWS = 0
COLS = 0

start = None
exit_cell = None

player_r = 0
player_c = 0
facing = (0, 1)

enemies = []

won = False
lost = False

# Player health state
player_health = MAX_HEALTH
last_hit_time = -HIT_COOLDOWN_MS

# Shooting animation
shot_start = None
shot_end = None
shot_time = 0
SHOT_DURATION = 120

# ============================================================
# 4. HELPER FUNCTIONS
# ============================================================

def draw_text(text, font_type, color, x, y):
    image = font_type.render(text, True, color)
    screen.blit(image, (x, y))


def tile_rect(r, c):
    """Convert maze coordinates into screen coordinates."""
    x = MARGIN + c * TILE
    y = MARGIN + r * TILE
    return pygame.Rect(x, y, TILE, TILE)


def find_special_cells():
    """Find the start and exit positions."""
    global start, exit_cell

    start = None
    exit_cell = None

    for r, row in enumerate(MAZE):
        for c, cell in enumerate(row):
            if cell == "S":
                start = (r, c)
            elif cell == "E":
                exit_cell = (r, c)

    if start is None or exit_cell is None:
        raise ValueError("Every maze needs an S and an E.")


# ============================================================
# 5. LOAD A DIFFICULTY LEVEL
# ============================================================

def select_maze(level):
    global difficulty, MAZE, ROWS, COLS
    global player_r, player_c, facing
    global enemies, won, lost, game_state
    global shot_start, shot_end
    global player_health, last_hit_time

    difficulty = level
    MAZE = MAZES[level]

    ROWS = len(MAZE)
    COLS = len(MAZE[0])

    if any(len(row) != COLS for row in MAZE):
        raise ValueError("All maze rows must have equal length.")

    find_special_cells()

    # Reset player position and direction.
    player_r, player_c = start
    facing = (0, 1)

    # Reset game state and restore all four hearts.
    won = False
    lost = False
    player_health = MAX_HEALTH
    last_hit_time = -HIT_COOLDOWN_MS

    shot_start = None
    shot_end = None

    # Find possible enemy positions.
    available_cells = []

    for r, row in enumerate(MAZE):
        for c, cell in enumerate(row):
            if cell == ".":
                distance_from_start = (
                    abs(r - start[0]) + abs(c - start[1])
                )
                distance_from_exit = (
                    abs(r - exit_cell[0]) + abs(c - exit_cell[1])
                )

                if distance_from_start >= 4 and distance_from_exit >= 2:
                    available_cells.append((r, c))

    enemy_count = min(ENEMY_COUNTS[level], len(available_cells))
    enemies = random.sample(available_cells, enemy_count)

    game_state = "playing"


# ============================================================
# 6. DRAW THE DIFFICULTY MENU
# ============================================================

def menu_button_rect(level):
    levels = ["Easy", "Medium", "Hard"]
    index = levels.index(level)

    button_width = 240
    button_height = 55
    gap = 20

    total_height = 3 * button_height + 2 * gap
    first_y = (HEIGHT - total_height) // 2

    return pygame.Rect(
        WIDTH // 2 - button_width // 2,
        first_y + index * (button_height + gap),
        button_width,
        button_height
    )


def draw_menu():
    screen.fill(BACKGROUND)

    title = large_font.render("MAZE RUNNER", True, WHITE)
    screen.blit(
        title,
        (WIDTH // 2 - title.get_width() // 2, 100)
    )

    subtitle = font.render(
        "Choose your difficulty", True, MUTED
    )
    screen.blit(
        subtitle,
        (WIDTH // 2 - subtitle.get_width() // 2, 155)
    )

    descriptions = {
        "Easy": "2 enemies",
        "Medium": "4 enemies",
        "Hard": "7 enemies",
    }

    for level in ["Easy", "Medium", "Hard"]:
        rect = menu_button_rect(level)

        mouse_over = rect.collidepoint(pygame.mouse.get_pos())
        color = GOAL if mouse_over else PANEL

        pygame.draw.rect(
            screen, color, rect, border_radius=10
        )
        pygame.draw.rect(
            screen, WALL_EDGE, rect,
            width=2, border_radius=10
        )

        label = font.render(level, True, WHITE)
        screen.blit(label, (rect.x + 20, rect.y + 5))

        description = small_font.render(
            descriptions[level], True, MUTED
        )
        screen.blit(
            description,
            (rect.x + 20, rect.y + 31)
        )

    draw_text(
        "Move: arrows / WASD",
        small_font, WHITE,
        WIDTH // 2 - 95, HEIGHT - 85
    )

    draw_text(
        "Shoot: ENTER",
        small_font, GOLD,
        WIDTH // 2 - 65, HEIGHT - 55
    )


# ============================================================
# 7. DRAW THE MAZE
# ============================================================

def draw_maze():
    for r, row in enumerate(MAZE):
        for c, cell in enumerate(row):
            rect = tile_rect(r, c)

            if cell == "#":
                pygame.draw.rect(
                    screen, WALL, rect, border_radius=4
                )
                pygame.draw.rect(
                    screen, WALL_EDGE, rect,
                    width=2, border_radius=4
                )
                pygame.draw.line(
                    screen,
                    (135, 148, 165),
                    (rect.x + 5, rect.y + 5),
                    (rect.right - 5, rect.y + 5),
                    2
                )

            else:
                pygame.draw.rect(screen, PATH, rect)

                if cell == "E":
                    pygame.draw.rect(
                        screen, GOAL,
                        rect.inflate(-6, -6),
                        border_radius=5
                    )

                    fx = rect.centerx

                    pygame.draw.line(
                        screen, WHITE,
                        (fx - 4, rect.centery + 8),
                        (fx - 4, rect.centery - 8),
                        3
                    )

                    pygame.draw.polygon(
                        screen, WHITE,
                        [
                            (fx - 3, rect.centery - 8),
                            (fx + 8, rect.centery - 5),
                            (fx - 3, rect.centery),
                        ]
                    )


# ============================================================
# 8. DRAW THE PLAYER
# ============================================================

def draw_player():
    rect = tile_rect(player_r, player_c)
    cx, cy = rect.center

    # Flash the player while protected after a hit.
    protected = (
        pygame.time.get_ticks() - last_hit_time
        < HIT_COOLDOWN_MS
    )

    if protected and (pygame.time.get_ticks() // 100) % 2 == 0:
        return

    pygame.draw.ellipse(
        screen, (45, 48, 52),
        (cx - 10, cy + 7, 20, 7)
    )

    pygame.draw.rect(
        screen, PLAYER_COLOR,
        (cx - 8, cy - 2, 16, 14),
        border_radius=4
    )

    pygame.draw.circle(
        screen, PLAYER_SKIN,
        (cx, cy - 9), 8
    )

    pygame.draw.arc(
        screen, (45, 29, 25),
        (cx - 8, cy - 17, 16, 13),
        0, 3.14, 4
    )

    pygame.draw.circle(
        screen, (25, 30, 40),
        (cx - 3, cy - 9), 1
    )
    pygame.draw.circle(
        screen, (25, 30, 40),
        (cx + 3, cy - 9), 1
    )

    # Weapon points in the direction the player faces.
    dr, dc = facing
    start_pos = (cx + dc * 7, cy + dr * 7)
    end_pos = (cx + dc * 16, cy + dr * 16)

    pygame.draw.line(
        screen, (45, 50, 60),
        start_pos, end_pos, 5
    )


# ============================================================
# 9. DRAW ENEMIES
# ============================================================

def draw_enemies():
    for r, c in enemies:
        rect = tile_rect(r, c)
        cx, cy = rect.center

        pygame.draw.ellipse(
            screen, (45, 35, 35),
            (cx - 11, cy + 7, 22, 7)
        )

        pygame.draw.rect(
            screen, ENEMY_COLOR,
            (cx - 10, cy - 3, 20, 17),
            border_radius=5
        )

        pygame.draw.circle(
            screen, (155, 40, 50),
            (cx, cy - 8), 9
        )

        pygame.draw.circle(
            screen, WHITE, (cx - 3, cy - 9), 2
        )
        pygame.draw.circle(
            screen, WHITE, (cx + 3, cy - 9), 2
        )


# ============================================================
# 10. PLAYER HEALTH AND ENEMY MOVEMENT
# ============================================================

def handle_player_hit():
    """Remove one heart and respawn the player if possible."""
    global player_health, last_hit_time, lost
    global player_r, player_c

    now = pygame.time.get_ticks()

    # Prevent multiple hearts being lost from one continuous collision.
    if now - last_hit_time < HIT_COOLDOWN_MS:
        return

    player_health -= 1
    last_hit_time = now

    if player_health <= 0:
        player_health = 0
        lost = True
    else:
        # Respawn at the start after taking damage.
        player_r, player_c = start


def move_enemies():
    """
    Enemies patrol into neighboring floor cells.
    They cannot move through walls or overlap one another.
    """
    occupied = set(enemies)

    for i, (r, c) in enumerate(enemies):
        occupied.discard((r, c))

        directions = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
        ]
        random.shuffle(directions)

        for dr, dc in directions:
            nr = r + dr
            nc = c + dc

            if not (0 <= nr < ROWS and 0 <= nc < COLS):
                continue

            if MAZE[nr][nc] == "#":
                continue

            if (nr, nc) in occupied:
                continue

            enemies[i] = (nr, nc)
            break

        occupied.add(enemies[i])

    # Check if an enemy reached the player's tile.
    if (player_r, player_c) in enemies:
        handle_player_hit()


# ============================================================
# 11. SHOOTING MECHANIC
# ============================================================

def shoot():
    """Fire down the corridor until a wall or enemy is hit."""
    global shot_start, shot_end, shot_time

    if won or lost:
        return

    dr, dc = facing

    r = player_r
    c = player_c

    shot_start = tile_rect(r, c).center
    shot_end = shot_start
    shot_time = pygame.time.get_ticks()

    while True:
        r += dr
        c += dc

        if not (0 <= r < ROWS and 0 <= c < COLS):
            break

        if MAZE[r][c] == "#":
            break

        if (r, c) in enemies:
            enemies.remove((r, c))
            shot_end = tile_rect(r, c).center
            break

        shot_end = tile_rect(r, c).center


def draw_shot():
    if shot_start is None:
        return

    elapsed = pygame.time.get_ticks() - shot_time

    if elapsed <= SHOT_DURATION:
        pygame.draw.line(
            screen, BULLET_COLOR,
            shot_start, shot_end, 4
        )
        pygame.draw.circle(
            screen, WHITE, shot_end, 4
        )


# ============================================================
# 12. PLAYER MOVEMENT AND COLLISIONS
# ============================================================

def try_move(dr, dc):
    global player_r, player_c, facing
    global won, lost

    if won or lost:
        return

    facing = (dr, dc)

    nr = player_r + dr
    nc = player_c + dc

    if not (0 <= nr < ROWS and 0 <= nc < COLS):
        return

    if MAZE[nr][nc] == "#":
        return

    player_r = nr
    player_c = nc

    # Touching an enemy costs one heart.
    if (player_r, player_c) in enemies:
        handle_player_hit()
        return

    # The exit only works after all enemies are defeated.
    if (player_r, player_c) == exit_cell:
        if len(enemies) == 0:
            won = True


# ============================================================
# 13. RESTART AND RETURN TO MENU
# ============================================================

def reset_game():
    """Restart the selected level with four hearts."""
    if difficulty is not None:
        select_maze(difficulty)


def return_to_menu():
    global game_state
    game_state = "menu"


# ============================================================
# 14. HEALTH BAR
# ============================================================

def draw_heart(x, y, size, color):
    """Draw a solid heart shape using Pygame."""
    radius = size // 4

    # Two round bumps at the top of the heart
    pygame.draw.circle(
        screen, color,
        (x - radius, y - radius),
        radius
    )
    pygame.draw.circle(
        screen, color,
        (x + radius, y - radius),
        radius
    )

    # Pointed bottom half of the heart
    pygame.draw.polygon(
        screen, color,
        [
            (x - size // 2, y - radius),
            (x + size // 2, y - radius),
            (x, y + size // 2),
        ]
    )


def draw_health_bar(x, y):
    """Display four actual heart icons."""
    draw_text("HEALTH", small_font, GOLD, x, y - 20)

    for i in range(MAX_HEALTH):
        heart_x = x + 18 + i * 35

        if i < player_health:
            # Full heart
            color = (255, 45, 70)
        else:
            # Empty heart
            color = (75, 75, 85)

        draw_heart(heart_x, y + 15, 26, color)


# ============================================================
# 15. INFORMATION PANEL
# ============================================================

def draw_hud():
    x = MARGIN * 2 + COLS * TILE + 12

    panel = pygame.Rect(
        x, MARGIN,
        HUD_WIDTH - 24,
        HEIGHT - 2 * MARGIN
    )

    pygame.draw.rect(
        screen, PANEL, panel, border_radius=12
    )

    draw_text(
        "MAZE RUNNER", font, WHITE,
        x + 12, MARGIN + 15
    )

    draw_text(
        "Level: " + difficulty,
        small_font, GOLD,
        x + 12, MARGIN + 50
    )

    # Display the four-heart health bar.
    draw_health_bar(x + 12, MARGIN + 110)

    y = MARGIN + 165
    draw_text("CONTROLS", font, GOLD, x + 12, y)
    y += 35

    controls = [
        "Arrows / WASD: Move",
        "ENTER: Shoot",
        "R: Restart",
        "ESC: Main menu",
    ]

    for line in controls:
        draw_text(line, small_font, WHITE, x + 12, y)
        y += 29

    y += 18
    draw_text("ENEMIES LEFT", font, GOLD, x + 12, y)
    y += 35

    draw_text(
        str(len(enemies)),
        large_font, ENEMY_COLOR,
        x + 12, y
    )

    y += 65
    draw_text("OBJECTIVE", font, GOLD, x + 12, y)
    y += 35

    draw_text(
        "Defeat all enemies",
        small_font, WHITE, x + 12, y
    )
    draw_text(
        "and reach the exit.",
        small_font, WHITE, x + 12, y + 23
    )

    if won:
        y += 85
        draw_text("YOU WON!", font, GOAL, x + 12, y)
        draw_text(
            "Press R to replay",
            small_font, WHITE, x + 12, y + 35
        )

    elif lost:
        y += 85
        draw_text("GAME OVER", font, ENEMY_COLOR, x + 12, y)
        draw_text(
            "Press R to retry",
            small_font, WHITE, x + 12, y + 35
        )


# ============================================================
# 16. MAIN GAME LOOP
# ============================================================

running = True
last_enemy_move = pygame.time.get_ticks()

while running:
    clock.tick(FPS)
    current_time = pygame.time.get_ticks()

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        # ---------------- MENU INPUT ----------------
        elif game_state == "menu":

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for level in ["Easy", "Medium", "Hard"]:
                        if menu_button_rect(level).collidepoint(event.pos):
                            select_maze(level)
                            last_enemy_move = current_time
                            break

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    select_maze("Easy")
                    last_enemy_move = current_time

                elif event.key == pygame.K_2:
                    select_maze("Medium")
                    last_enemy_move = current_time

                elif event.key == pygame.K_3:
                    select_maze("Hard")
                    last_enemy_move = current_time

                elif event.key == pygame.K_ESCAPE:
                    running = False

        # ---------------- GAME INPUT ----------------
        elif game_state == "playing":

            if event.type == pygame.KEYDOWN:

                if event.key in (pygame.K_UP, pygame.K_w):
                    try_move(-1, 0)

                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    try_move(1, 0)

                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    try_move(0, -1)

                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    try_move(0, 1)

                elif event.key == pygame.K_RETURN:
                    shoot()

                elif event.key == pygame.K_r:
                    reset_game()
                    last_enemy_move = current_time

                elif event.key == pygame.K_ESCAPE:
                    return_to_menu()

    # ========================================================
    # UPDATE ENEMIES
    # ========================================================

    if (
        game_state == "playing"
        and not won
        and not lost
        and current_time - last_enemy_move >= ENEMY_MOVE_DELAY
    ):
        move_enemies()
        last_enemy_move = current_time

    # ========================================================
    # DRAW CURRENT SCREEN
    # ========================================================

    if game_state == "menu":
        draw_menu()

    elif game_state == "playing":
        screen.fill(BACKGROUND)

        draw_maze()
        draw_enemies()
        draw_player()
        draw_shot()
        draw_hud()

    pygame.display.flip()


# ============================================================
# 17. SHUT DOWN
# ============================================================

pygame.quit()
sys.exit()