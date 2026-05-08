"""
Logistics Flow - Pyxel Prototype
==================================
Concept: A logistics deck-building battle about route flow optimization.
Playing the same card type repeatedly compresses cards into one stronger card.
Control congestion spreading across the board and clear stalled inventory.
Score 32.75 idea from Game Idea Factory.
"""

import pyxel
import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional

# Config
W, H = 420, 330
FPS = 30
C_BG = 0
C_DARK = 5
C_LIGHT = 6
C_WHITE = 7
C_RED = 8
C_ORANGE = 9
C_YELLOW = 10
C_GREEN = 11
C_BLUE = 12
C_PURPLE = 13
C_PINK = 14
C_PEACH = 15

GRID_COLS, GRID_ROWS = 4, 4
CELL_SIZE = 28
GRID_X, GRID_Y = 30, 50

# Card Types
class CardType(Enum):
    DELIVERY = ("Delivery", 1, 2, C_GREEN, "Low-cost steady flow")
    EXPRESS = ("Express", 2, 3, C_ORANGE, "Fast route. +1 congestion")
    LOGISTICS = ("Logistics", 1, 1, C_BLUE, "Clear 1 congestion")
    AIR = ("Air", 3, 5, C_PURPLE, "High flow. Ignores congestion")
    RAIL = ("Rail", 2, 2, C_YELLOW, "Adjacency bonus")

    def __init__(self, label, cost, flow, color, desc):
        self.label = label
        self.cost = cost
        self.flow = flow
        self.color = color
        self.desc = desc

@dataclass
class Card:
    type: CardType
    compressed: bool = False
    compress_count: int = 1  # how many cards merged into this

    @property
    def current_flow(self):
        base = self.type.flow * self.compress_count
        if self.compress_count >= 2:
            base = int(base * (1 + (self.compress_count - 1) * 0.5))
        return base

    @property
    def display_name(self):
        if self.compress_count >= 2:
            return f"{self.type.label}x{self.compress_count}"
        return self.type.label

    @property
    def color(self):
        return self.type.color

    @property
    def cost(self):
        return self.type.cost

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    max_life: int
    color: int
    size: int = 2
    text: str = ""

@dataclass
class CardAnimation:
    """Floating card that appears when playing a card"""
    x: float
    y: float
    target_x: float
    target_y: float
    card: Card
    life: int
    max_life: int

class CellType(Enum):
    EMPTY = 0
    ROUTE = 1    # player's logistics route
    CONGESTED = 2  # congestion spreading

class Game:
    def __init__(self):
        pyxel.init(W, H, title="Logistics Flow - Prototype", fps=FPS, display_scale=2)
        pyxel.mouse(True)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self):
        # Board
        self.grid = [[CellType.EMPTY for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]

        # Player
        self.player_hp = 20
        self.player_max_hp = 20
        self.heat = 5
        self.max_heat = 10
        self.congestion_meter = 0  # count of congested cells

        # Enemy
        self.enemy_hp = 35
        self.enemy_max_hp = 35
        self.enemy_name = "Backlog"
        self.turn = 1

        # Deck & Hand
        self.deck = self.make_deck()
        random.shuffle(self.deck)
        self.hand: list[Card] = []
        self.discard: list[Card] = []
        self.hand_size = 5

        # Play state
        self.played_this_turn: list[Card] = []
        self.phase = "player"  # player, resolve, enemy
        self.phase_timer = 0
        self.selected_card_idx = -1
        self.message = ""
        self.message_timer = 0
        self.compress_animation: Optional[CardAnimation] = None

        # Particles
        self.particles: list[Particle] = []

        # Effects
        self.flash_timer = 0
        self.compress_flash = 0
        self.congestion_countdown = 0  # for enemy's next action

        # Draw initial hand
        self.draw_to_hand()

    def make_deck(self):
        """Create a 15-card deck: 3 of each type"""
        deck = []
        for t in CardType:
            for _ in range(3):
                deck.append(Card(type=t))
        return deck

    def draw_to_hand(self):
        while len(self.hand) < self.hand_size and self.deck:
            self.hand.append(self.deck.pop())
        # If deck is empty, shuffle discard back
        if not self.deck and len(self.hand) < self.hand_size:
            self.deck = self.discard
            random.shuffle(self.deck)
            self.discard = []
            self.show_message("Deck reshuffled!")

    def show_message(self, text):
        self.message = text
        self.message_timer = 60

    def add_particles(self, x, y, color, count=8, text=""):
        for _ in range(count):
            self.particles.append(Particle(
                x + random.uniform(-4, 4),
                y + random.uniform(-4, 4),
                random.uniform(-1.5, 1.5),
                random.uniform(-2.5, -0.5),
                random.randint(15, 30),
                30,
                color,
                random.randint(1, 3),
                text,
            ))

    def add_explosion(self, x, y, color, count=20):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 4)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                random.randint(10, 25),
                25,
                color,
                random.randint(2, 4),
            ))

    def play_card(self, idx):
        if idx < 0 or idx >= len(self.hand):
            return
        card = self.hand[idx]
        if card.cost > self.heat:
            self.show_message(f"Not enough HEAT! Need {card.cost}")
            return

        self.heat -= card.cost
        played_card = self.hand.pop(idx)

        # Check compression: look for same type in played_this_turn
        merge_target = None
        for i, pc in enumerate(self.played_this_turn):
            if pc.type == played_card.type:
                merge_target = i
                break

        if merge_target is not None:
            # Compress: merge the cards
            existing = self.played_this_turn[merge_target]
            existing.compress_count += 1
            existing.compressed = True
            flow = existing.current_flow
            self.compress_flash = 15
            self.show_message(f"Compressed! {existing.display_name} FLOW {flow}")
            self.add_explosion(
                GRID_X + GRID_COLS * CELL_SIZE // 2,
                GRID_Y + GRID_ROWS * CELL_SIZE // 2,
                C_YELLOW, 15
            )
        else:
            self.played_this_turn.append(played_card)
            self.show_message(f"{played_card.display_name} route started!")

        # Place a route on the board
        self.place_route(card)

        # Card effects
        if card.type == CardType.EXPRESS:
            self.spread_congestion(1)
        elif card.type == CardType.LOGISTICS:
            self.clear_congestion(1)

        # Add particles
        self.add_particles(
            GRID_X + GRID_COLS * CELL_SIZE // 2,
            GRID_Y - 5,
            card.color, 6
        )

        self.selected_card_idx = -1

    def place_route(self, card):
        """Place a route on the nearest empty cell"""
        # Find the first empty cell (row by row)
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] == CellType.EMPTY:
                    self.grid[r][c] = CellType.ROUTE
                    self.add_explosion(
                        GRID_X + c * CELL_SIZE + CELL_SIZE // 2,
                        GRID_Y + r * CELL_SIZE + CELL_SIZE // 2,
                        C_GREEN, 8
                    )
                    return
        # If board is full, just deal bonus damage
        self.show_message("Board full! Direct damage +3")
        self.enemy_hp -= 3

    def calc_rail_bonus(self):
        """For Rail cards: bonus flow based on adjacent routes"""
        bonus = 0
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] == CellType.ROUTE:
                    # Count adjacent routes
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS:
                            if self.grid[nr][nc] == CellType.ROUTE:
                                bonus += 1
        return bonus // 2  # half adjacent pairs

    def spread_congestion(self, count=1):
        """Add congestion to random empty cells"""
        empty_cells = [(r, c) for r in range(GRID_ROWS) for c in range(GRID_COLS)
                       if self.grid[r][c] == CellType.EMPTY]
        if not empty_cells:
            return
        random.shuffle(empty_cells)
        for _ in range(min(count, len(empty_cells))):
            r, c = empty_cells.pop()
            self.grid[r][c] = CellType.CONGESTED
            self.add_explosion(
                GRID_X + c * CELL_SIZE + CELL_SIZE // 2,
                GRID_Y + r * CELL_SIZE + CELL_SIZE // 2,
                C_RED, 6
            )

    def clear_congestion(self, count=1):
        cleared = 0
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] == CellType.CONGESTED and cleared < count:
                    self.grid[r][c] = CellType.EMPTY
                    cleared += 1
                    self.add_particles(
                        GRID_X + c * CELL_SIZE + CELL_SIZE // 2,
                        GRID_Y + r * CELL_SIZE + CELL_SIZE // 2,
                        C_BLUE, 4
                    )
        if cleared > 0:
            self.show_message(f"Cleared {cleared} congestion!")

    def resolve_player_turn(self):
        """Resolve all played cards' effects"""
        total_flow = 0
        for card in self.played_this_turn:
            flow = card.current_flow
            # Rail bonus
            if card.type == CardType.RAIL:
                bonus = self.calc_rail_bonus()
                flow += bonus
                if bonus > 0:
                    self.show_message(f"Rail adjacency bonus +{bonus}!")
            total_flow += flow
            self.add_explosion(
                W // 2, H // 2 - 30,
                card.color, 10
            )

        if total_flow > 0:
            self.enemy_hp -= total_flow
            self.show_message(f"Total flow {total_flow}! Enemy takes {total_flow} dmg!")
            self.add_explosion(W // 2, 50, C_RED, 20)
        else:
            self.show_message("Play cards to build routes!")

        # Discard played cards
        self.discard.extend(self.played_this_turn)
        self.played_this_turn = []

    def enemy_turn(self):
        """Enemy action: spread congestion and attack"""
        if self.enemy_hp <= 0:
            return

        # Spread congestion via cellular automaton
        new_congested = []
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] == CellType.CONGESTED:
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS:
                            if self.grid[nr][nc] == CellType.EMPTY:
                                if (nr, nc) not in new_congested:
                                    new_congested.append((nr, nc))

        # Add some random congestion too
        empty_cells = [(r, c) for r in range(GRID_ROWS) for c in range(GRID_COLS)
                       if self.grid[r][c] == CellType.EMPTY]
        random.shuffle(empty_cells)
        spread_count = min(1 + self.turn // 3, 4)
        for r, c in empty_cells[:spread_count]:
            if (r, c) not in new_congested:
                new_congested.append((r, c))

        for r, c in new_congested:
            self.grid[r][c] = CellType.CONGESTED
            self.add_explosion(
                GRID_X + c * CELL_SIZE + CELL_SIZE // 2,
                GRID_Y + r * CELL_SIZE + CELL_SIZE // 2,
                C_RED, 4
            )

        congested_count = sum(1 for r in range(GRID_ROWS) for c in range(GRID_COLS)
                             if self.grid[r][c] == CellType.CONGESTED)
        self.congestion_meter = congested_count

        # Attack: base damage + congestion penalty
        congestion_damage = congested_count // 2
        base_damage = 2 + self.turn // 3
        damage = base_damage + congestion_damage
        self.player_hp -= damage
        self.show_message(f"Congestion spreads! {damage} dmg! (+{congestion_damage})")
        self.flash_timer = 10

    def end_player_turn(self):
        if not self.played_this_turn and len(self.hand) == self.hand_size:
            # Pass turn without playing
            self.heat = min(self.max_heat, self.heat + 2)
            self.enemy_turn()
            self.turn += 1
            self.draw_to_hand()
            return

        self.resolve_player_turn()
        self.heat = min(self.max_heat, self.heat + 2)
        self.enemy_turn()
        self.turn += 1
        self.draw_to_hand()

    def check_game_over(self):
        if self.enemy_hp <= 0:
            return "win"
        if self.player_hp <= 0:
            return "lose"
        congested = sum(1 for r in range(GRID_ROWS) for c in range(GRID_COLS)
                       if self.grid[r][c] == CellType.CONGESTED)
        if congested >= GRID_ROWS * GRID_COLS:
            self.show_message("Board filled with congestion!")
            return "lose"
        return None

    # Update
    def update(self):
        if self.message_timer > 0:
            self.message_timer -= 1

        if self.flash_timer > 0:
            self.flash_timer -= 1

        if self.compress_flash > 0:
            self.compress_flash -= 1

        # Update particles
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05  # gravity
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

        # Check game over
        result = self.check_game_over()
        if result == "win":
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return
        if result == "lose":
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        # Player input
        if self.phase == "player":
            mx, my = pyxel.mouse_x, pyxel.mouse_y

            # Card selection
            for i, card in enumerate(self.hand):
                cx, cy, cw, ch = self.card_rect(i)
                if cx <= mx <= cx + cw and cy <= my <= cy + ch:
                    self.selected_card_idx = i
                    if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                        self.play_card(i)
                    break
            else:
                self.selected_card_idx = -1

            # End turn button
            ex, ey, ew, eh = 340, 280, 65, 25
            if ex <= mx <= ex + ew and ey <= my <= ey + eh:
                if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                    self.end_player_turn()
        elif self.phase == "resolve":
            self.phase_timer -= 1
            if self.phase_timer <= 0:
                self.phase = "player"

    def card_rect(self, idx):
        cw, ch = 62, 35
        start_x = 15
        gap = 5
        x = start_x + idx * (cw + gap)
        y = 280
        return x, y, cw, ch

    # Draw
    def draw(self):
        pyxel.cls(C_BG)

        self.draw_enemy_area()
        self.draw_board()
        self.draw_player_info()
        self.draw_hand()
        self.draw_end_turn_button()
        self.draw_particles()
        self.draw_message()
        self.draw_game_over()

        # Title
        pyxel.text(15, 8, "Logistics Flow - Route Optimizer", C_LIGHT)

    def draw_enemy_area(self):
        # Enemy name + HP bar
        pyxel.text(15, 28, f"Enemy: {self.enemy_name}", C_RED)
        bar_x, bar_y, bar_w, bar_h = 100, 28, 200, 12
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, C_DARK)
        hp_pct = max(0, self.enemy_hp / self.enemy_max_hp)
        hp_color = C_GREEN if hp_pct > 0.5 else (C_ORANGE if hp_pct > 0.25 else C_RED)
        pyxel.rect(bar_x, bar_y, int(bar_w * hp_pct), bar_h, hp_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, C_LIGHT)
        pyxel.text(bar_x + 5, bar_y + 2, f"{max(0,self.enemy_hp)}/{self.enemy_max_hp}", C_WHITE)

        # Turn counter
        pyxel.text(320, 28, f"TURN {self.turn}", C_YELLOW)

    def draw_board(self):
        # Draw grid background
        pyxel.rectb(GRID_X - 2, GRID_Y - 2,
                     GRID_COLS * CELL_SIZE + 4, GRID_ROWS * CELL_SIZE + 4, C_LIGHT)

        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                x = GRID_X + c * CELL_SIZE
                y = GRID_Y + r * CELL_SIZE

                cell = self.grid[r][c]
                if cell == CellType.ROUTE:
                    color = C_GREEN
                elif cell == CellType.CONGESTED:
                    color = C_RED
                else:
                    color = C_DARK

                # Draw cell with slight border
                if cell != CellType.EMPTY:
                    pyxel.rect(x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2, color)
                    if cell == CellType.ROUTE:
                        # Draw route lines
                        cx, cy = x + CELL_SIZE // 2, y + CELL_SIZE // 2
                        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS:
                                if self.grid[nr][nc] == CellType.ROUTE:
                                    nx = GRID_X + nc * CELL_SIZE + CELL_SIZE // 2
                                    ny = GRID_Y + nr * CELL_SIZE + CELL_SIZE // 2
                                    pyxel.line(cx, cy, nx, ny, C_LIGHT)
                else:
                    pyxel.rect(x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2, C_BG)
                    pyxel.rectb(x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2, C_DARK)

        # Board label
        pyxel.text(GRID_X, GRID_Y - 14, "Logistics Network", C_LIGHT)

    def draw_player_info(self):
        info_x = 170
        info_y = 90

        # HP
        pyxel.text(info_x, info_y, f"HP: {self.player_hp}/{self.player_max_hp}",
                   C_RED if self.player_hp <= 5 else C_WHITE)

        # Heat (resource)
        heat_y = info_y + 15
        pyxel.text(info_x, heat_y, f"HEAT: {self.heat}/{self.max_heat}", C_ORANGE)
        # Heat bar
        bar_w = 80
        pyxel.rect(info_x, heat_y + 10, bar_w, 6, C_DARK)
        heat_pct = self.heat / self.max_heat
        pyxel.rect(info_x, heat_y + 10, int(bar_w * heat_pct), 6,
                   C_YELLOW if heat_pct > 0.3 else C_RED)
        pyxel.rectb(info_x, heat_y + 10, bar_w, 6, C_LIGHT)

        # Congestion meter
        congested = sum(1 for r in range(GRID_ROWS) for c in range(GRID_COLS)
                       if self.grid[r][c] == CellType.CONGESTED)
        cong_y = heat_y + 25
        pyxel.text(info_x, cong_y, f"Cong: {congested}/{GRID_ROWS*GRID_COLS}",
                   C_RED if congested > 4 else C_WHITE)
        # Congestion bar
        pyxel.rect(info_x, cong_y + 10, bar_w, 6, C_DARK)
        cong_pct = congested / (GRID_ROWS * GRID_COLS)
        pyxel.rect(info_x, cong_y + 10, int(bar_w * cong_pct), 6,
                   C_RED if cong_pct > 0.5 else C_ORANGE)
        pyxel.rectb(info_x, cong_y + 10, bar_w, 6, C_LIGHT)

        # Played cards this turn
        if self.played_this_turn:
            pyxel.text(info_x, cong_y + 25, "Routes this turn:", C_LIGHT)
            y_off = cong_y + 37
            for i, card in enumerate(self.played_this_turn):
                label = card.display_name
                if card.compress_count >= 2:
                    label += " *"
                pyxel.text(info_x + i * 50, y_off, label, card.color)

    def draw_hand(self):
        for i, card in enumerate(self.hand):
            cx, cy, cw, ch = self.card_rect(i)
            selected = (i == self.selected_card_idx)

            # Card background
            pyxel.rect(cx, cy, cw, ch, card.color if not selected else C_WHITE)
            pyxel.rectb(cx, cy, cw, ch, C_WHITE if selected else C_DARK)

            # Card info
            can_afford = card.cost <= self.heat
            if not can_afford:
                pyxel.rect(cx, cy, cw, ch, C_DARK)

            # Name
            name = card.display_name
            if card.compress_count >= 2:
                name += "*"
            pyxel.text(cx + 3, cy + 2, name, C_WHITE if can_afford else C_DARK)

            # Cost
            pyxel.text(cx + 3, cy + 13, f"HEAT:{card.cost}", C_YELLOW if can_afford else C_DARK)

            # Flow value
            flow = card.current_flow
            pyxel.text(cx + 3, cy + 22, f"FLOW:{flow}", C_GREEN if can_afford else C_DARK)

    def draw_end_turn_button(self):
        ex, ey, ew, eh = 340, 280, 65, 25
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        hovered = ex <= mx <= ex + ew and ey <= my <= ey + eh
        color = C_LIGHT if hovered else C_DARK
        pyxel.rect(ex, ey, ew, eh, color)
        pyxel.rectb(ex, ey, ew, eh, C_WHITE)
        pyxel.text(ex + 5, ey + 7, "END TURN", C_WHITE if not hovered else C_BG)

    def draw_particles(self):
        for p in self.particles:
            alpha = max(0, p.life / p.max_life)
            size = int(p.size * alpha)
            if size > 0:
                px, py = int(p.x), int(p.y)
                if p.text:
                    pyxel.text(px, py, p.text, p.color)
                else:
                    pyxel.rect(px - size // 2, py - size // 2, size, size, p.color)

    def draw_message(self):
        if self.message_timer > 0:
            x = W // 2 - len(self.message) * 2
            pyxel.text(x, H - 45, self.message, C_WHITE)

    def draw_game_over(self):
        result = self.check_game_over()
        if result == "win":
            pyxel.rect(0, H // 2 - 30, W, 60, C_DARK)
            pyxel.rectb(0, H // 2 - 30, W, 60, C_YELLOW)
            pyxel.text(W // 2 - 40, H // 2 - 20, "=== FLOW COMPLETE ===", C_GREEN)
            pyxel.text(W // 2 - 50, H // 2, "Backlog cleared", C_WHITE)
            pyxel.text(W // 2 - 50, H // 2 + 15, "[R] Restart", C_LIGHT)
        elif result == "lose":
            pyxel.rect(0, H // 2 - 30, W, 60, C_DARK)
            pyxel.rectb(0, H // 2 - 30, W, 60, C_RED)
            pyxel.text(W // 2 - 50, H // 2 - 20, "=== SYSTEM DOWN ===", C_RED)
            pyxel.text(W // 2 - 50, H // 2, "Network collapsed", C_WHITE)
            pyxel.text(W // 2 - 50, H // 2 + 15, "[R] Restart", C_LIGHT)


if __name__ == "__main__":
    Game()
