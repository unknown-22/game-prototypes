"""
VIRAL CASCADE — Grid-based cellular automaton battler.

Core: Inject viruses into a 6x6 grid. They spread via cellular automata
(2 generations per turn). Harvest connected clusters for damage.
Bigger clusters = more damage, but clusters > 5 cause overflow self-damage.

"The most fun moment": watching infection chains cascade across the grid,
then detonating a massive cluster for huge damage numbers.

Pyxel 2.x  400x300  display_scale=2
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──
SCREEN_W: int = 400
SCREEN_H: int = 300
GRID_X: int = 108
GRID_Y: int = 44
CELL_SIZE: int = 28
GRID_COLS: int = 6
GRID_ROWS: int = 6
GRID_W: int = GRID_COLS * CELL_SIZE
GRID_H: int = GRID_ROWS * CELL_SIZE

# Virus types
EMPTY: int = 0
V_RED: int = 1
V_BLUE: int = 2
V_GREEN: int = 3
V_GOLD: int = 4

VIRUS_TYPES: list[int] = [V_RED, V_BLUE, V_GREEN, V_GOLD]
VIRUS_COLORS: dict[int, int] = {V_RED: 8, V_BLUE: 6, V_GREEN: 11, V_GOLD: 9}
VIRUS_NAMES: dict[int, str] = {V_RED: "RED", V_BLUE: "BLUE", V_GREEN: "GREEN", V_GOLD: "GOLD"}
VIRUS_CHARS: dict[int, str] = {V_RED: "R", V_BLUE: "B", V_GREEN: "G", V_GOLD: "Y"}
VIRUS_DMG_MULT: dict[int, int] = {V_RED: 3, V_BLUE: 1, V_GREEN: 1, V_GOLD: 5}

MAX_CLUSTER: int = 5  # clusters larger than this cause overflow damage
HAND_SIZE: int = 3
MAX_HEAT: int = 15

# Card area
CARD_Y: int = 256
CARD_W: int = 50
CARD_H: int = 20
CARD_GAP: int = 8
CARDS_X: int = (SCREEN_W - (HAND_SIZE * CARD_W + (HAND_SIZE - 1) * CARD_GAP)) // 2


# ── Data ──
@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


class Phase(Enum):
    DRAW = auto()
    INJECT = auto()
    SPREAD = auto()
    HARVEST = auto()
    ENEMY_TURN = auto()
    VICTORY = auto()
    DEFEAT = auto()


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="VIRAL CASCADE", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.grid: list[list[int]] = [[EMPTY] * GRID_COLS for _ in range(GRID_ROWS)]
        self.hand: list[int] = []
        self.player_hp: int = 20
        self.player_max_hp: int = 20
        self.player_shield: int = 0
        self.enemy_hp: int = 100
        self.enemy_max_hp: int = 100
        self.enemy_base_atk: int = 3
        self.turn: int = 1
        self.heat: int = 0
        self.score: int = 0
        self.phase: Phase = Phase.DRAW
        self.phase_timer: int = 0
        self.message: str = ""
        self.message_timer: int = 0
        self.particles: list[Particle] = []
        self.spread_events: list[tuple[int, int, int]] = []
        self.spread_idx: int = 0
        self.spread_timer: int = 0
        self.selected_card: int = -1
        self.hovered_cell: tuple[int, int] | None = None
        self.harvest_result: str = ""
        self.harvest_result_timer: int = 0
        self.feedback_texts: list[tuple[str, float, float, int, int]] = []  # (text, x, y, life, color)
        self._begin_draw()

    # ── Grid utilities ──
    @staticmethod
    def _neighbors(r: int, c: int) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS:
                result.append((nr, nc))
        return result

    def _find_cluster(self, r: int, c: int, vt: int, visited: set[tuple[int, int]]) -> list[tuple[int, int]]:
        if (r, c) in visited or self.grid[r][c] != vt:
            return []
        cluster: list[tuple[int, int]] = []
        stack: list[tuple[int, int]] = [(r, c)]
        visited.add((r, c))
        while stack:
            cr, cc = stack.pop()
            cluster.append((cr, cc))
            for nr, nc in self._neighbors(cr, cc):
                if (nr, nc) not in visited and self.grid[nr][nc] == vt:
                    visited.add((nr, nc))
                    stack.append((nr, nc))
        return cluster

    def _find_all_clusters(self, vt: int) -> list[list[tuple[int, int]]]:
        clusters: list[list[tuple[int, int]]] = []
        visited: set[tuple[int, int]] = set()
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if (r, c) not in visited and self.grid[r][c] == vt:
                    cl = self._find_cluster(r, c, vt, visited)
                    if cl:
                        clusters.append(cl)
        return clusters

    def _spawn_particles(self, r: int, c: int, vt: int, count: int = 4) -> None:
        cx = float(GRID_X + c * CELL_SIZE + CELL_SIZE // 2)
        cy = float(GRID_Y + r * CELL_SIZE + CELL_SIZE // 2)
        color = VIRUS_COLORS[vt]
        for _ in range(count):
            self.particles.append(Particle(
                x=cx, y=cy,
                vx=random.uniform(-1.5, 1.5),
                vy=random.uniform(-1.5, 1.5),
                life=random.randint(8, 20),
                color=color,
            ))

    def _count_viruses(self) -> int:
        return sum(1 for r in range(GRID_ROWS) for c in range(GRID_COLS) if self.grid[r][c] != EMPTY)

    def _cell_center(self, r: int, c: int) -> tuple[float, float]:
        return (float(GRID_X + c * CELL_SIZE + CELL_SIZE // 2),
                float(GRID_Y + r * CELL_SIZE + CELL_SIZE // 2))

    # ── Phase transitions ──
    def _begin_draw(self) -> None:
        self.phase = Phase.DRAW
        self.phase_timer = 15
        self.message = f"TURN {self.turn}"
        self.message_timer = 30
        self.hand = []
        types = [V_RED, V_BLUE, V_GREEN]
        if self.turn >= 3:
            types.append(V_GOLD)
        for _ in range(HAND_SIZE):
            self.hand.append(random.choice(types))
        self.selected_card = 0 if self.hand else -1

    def _begin_spread(self) -> None:
        self.phase = Phase.SPREAD
        self.spread_events = self._do_spread()
        self.spread_idx = 0
        self.spread_timer = 0
        self.hand = []

    def _do_spread(self) -> list[tuple[int, int, int]]:
        events: list[tuple[int, int, int]] = []
        for _gen in range(2):
            new_grid = [row[:] for row in self.grid]
            for r in range(GRID_ROWS):
                for c in range(GRID_COLS):
                    vt = self.grid[r][c]
                    if vt != EMPTY:
                        for nr, nc in self._neighbors(r, c):
                            if new_grid[nr][nc] == EMPTY and random.random() < 0.55:
                                new_grid[nr][nc] = vt
                                events.append((nr, nc, vt))
            self.grid = new_grid
        return events

    def _begin_harvest(self) -> None:
        self.phase = Phase.HARVEST
        virus_count = self._count_viruses()
        self.heat = virus_count
        if self.heat > MAX_HEAT:
            overflow = self.heat - MAX_HEAT
            self.player_hp -= overflow
            self.message = f"OVERHEAT! -{overflow} HP"
            self.message_timer = 40

    def _do_harvest(self, vt: int) -> None:
        clusters = self._find_all_clusters(vt)
        if not clusters:
            self.message = f"No {VIRUS_NAMES[vt]} to harvest"
            self.message_timer = 30
            return

        total_dmg: int = 0
        overflow_dmg: int = 0
        total_cells: int = 0

        for cluster in clusters:
            size = len(cluster)
            mult = VIRUS_DMG_MULT[vt]
            dmg = size * mult
            total_dmg += dmg
            total_cells += size

            if size > MAX_CLUSTER:
                overflow_dmg += (size - MAX_CLUSTER)

            for r, c in cluster:
                self.grid[r][c] = EMPTY
                self._spawn_particles(r, c, vt, 4)

        self.enemy_hp -= total_dmg
        self.score += total_dmg

        # Type-specific effects
        if vt == V_BLUE:
            self.player_shield += total_cells
        elif vt == V_GREEN:
            self.player_hp = min(self.player_hp + total_cells, self.player_max_hp)
        elif vt == V_GOLD:
            cost = total_cells
            self.player_hp -= cost
            self.message = f"GOLD cost: -{cost} HP"
            self.message_timer = 30

        if overflow_dmg > 0:
            self.player_hp -= overflow_dmg
            self.heat += overflow_dmg
            self.message = f"OVERFLOW! -{overflow_dmg} HP"
            self.message_timer = 40

        result = f"{VIRUS_NAMES[vt]}: {total_cells}c x{VIRUS_DMG_MULT[vt]} = {total_dmg}"
        self.harvest_result = result
        self.harvest_result_timer = 50

        # Floating feedback
        cx, cy = self._cell_center(2, 3)
        self.feedback_texts.append((str(total_dmg), cx, cy - 20, 30, VIRUS_COLORS[vt]))

    def _begin_enemy_turn(self) -> None:
        self.phase = Phase.ENEMY_TURN
        self.phase_timer = 25

    def _end_enemy_turn(self) -> None:
        atk = self.enemy_base_atk + self.turn // 3
        if self.heat > MAX_HEAT:
            atk += (self.heat - MAX_HEAT) // 2

        if self.player_shield > 0:
            blocked = min(self.player_shield, atk)
            self.player_shield -= blocked
            atk -= blocked

        if atk > 0:
            self.player_hp -= atk
            self.message = f"Enemy: -{atk} HP"
            self.message_timer = 30
            # Damage particles near player area
            for _ in range(6):
                self.particles.append(Particle(
                    x=50.0, y=10.0,
                    vx=random.uniform(-2, 2),
                    vy=random.uniform(-2, 2),
                    life=random.randint(10, 18),
                    color=8,
                ))

        if self.player_hp <= 0:
            self.player_hp = 0
            self.phase = Phase.DEFEAT
            return
        if self.enemy_hp <= 0:
            self.enemy_hp = 0
            self.phase = Phase.VICTORY
            return

        self.turn += 1
        self._begin_draw()

    # ── Update ──
    def update(self) -> None:
        self._update_particles()
        self._update_timers()
        self._update_feedback()

        if self.phase == Phase.DRAW:
            self.phase_timer -= 1
            if self.phase_timer <= 0:
                self.phase = Phase.INJECT

        elif self.phase == Phase.INJECT:
            self._update_inject()

        elif self.phase == Phase.SPREAD:
            self._update_spread()

        elif self.phase == Phase.HARVEST:
            self._update_harvest()

        elif self.phase == Phase.ENEMY_TURN:
            self.phase_timer -= 1
            if self.phase_timer <= 0:
                self._end_enemy_turn()

        elif self.phase in (Phase.VICTORY, Phase.DEFEAT):
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_timers(self) -> None:
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""
        if self.harvest_result_timer > 0:
            self.harvest_result_timer -= 1

    def _update_feedback(self) -> None:
        for fb in self.feedback_texts[:]:
            _txt, x, y, life, _color = fb
            new_life = life - 1
            if new_life <= 0:
                self.feedback_texts.remove(fb)
            else:
                idx = self.feedback_texts.index(fb)
                self.feedback_texts[idx] = (_txt, x, y - 0.8, new_life, _color)

    def _update_inject(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        self.hovered_cell = None
        if GRID_X <= mx < GRID_X + GRID_W and GRID_Y <= my < GRID_Y + GRID_H:
            col = (mx - GRID_X) // CELL_SIZE
            row = (my - GRID_Y) // CELL_SIZE
            if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
                self.hovered_cell = (row, col)

        # Keyboard card selection
        for idx, key in enumerate([
            pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3,
        ]):
            if pyxel.btnp(key) and idx < len(self.hand):
                self.selected_card = idx

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            # Click card
            for i in range(len(self.hand)):
                cx = CARDS_X + i * (CARD_W + CARD_GAP)
                if cx <= mx < cx + CARD_W and CARD_Y <= my < CARD_Y + CARD_H:
                    self.selected_card = i
                    return

            # Click grid cell
            if self.hovered_cell is not None and 0 <= self.selected_card < len(self.hand):
                r, c = self.hovered_cell
                if self.grid[r][c] == EMPTY:
                    vt = self.hand.pop(self.selected_card)
                    self.grid[r][c] = vt
                    self._spawn_particles(r, c, vt, 3)
                    if self.hand:
                        self.selected_card = min(self.selected_card, len(self.hand) - 1)
                    else:
                        self.selected_card = -1
                        self._begin_spread()

        # SPACE to spread early with remaining cards
        if pyxel.btnp(pyxel.KEY_SPACE) and self.hand:
            self._begin_spread()

    def _update_spread(self) -> None:
        self.spread_timer -= 1
        if self.spread_timer <= 0 and self.spread_idx < len(self.spread_events):
            r, c, vt = self.spread_events[self.spread_idx]
            self._spawn_particles(r, c, vt, 2)
            self.spread_idx += 1
            self.spread_timer = 2

        if self.spread_idx >= len(self.spread_events):
            self._begin_harvest()

    def _update_harvest(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            btn_w = 58
            btn_h = 18
            btns_x = (SCREEN_W - (4 * btn_w + 3 * 8)) // 2
            btn_y = CARD_Y + CARD_H + 10
            for i, vt in enumerate(VIRUS_TYPES):
                bx = btns_x + i * (btn_w + 8)
                if bx <= mx < bx + btn_w and btn_y <= my < btn_y + btn_h:
                    self._do_harvest(vt)
                    self._begin_enemy_turn()
                    return

            # Skip button
            skip_w = 60
            skip_h = 14
            skip_x = SCREEN_W // 2 - skip_w // 2
            skip_y = btn_y + btn_h + 4
            if skip_x <= mx < skip_x + skip_w and skip_y <= my < skip_y + skip_h:
                self._begin_enemy_turn()

        # Keyboard harvest
        for key, vt in [
            (pyxel.KEY_1, V_RED),
            (pyxel.KEY_2, V_BLUE),
            (pyxel.KEY_3, V_GREEN),
            (pyxel.KEY_4, V_GOLD),
        ]:
            if pyxel.btnp(key):
                self._do_harvest(vt)
                self._begin_enemy_turn()
                return

        if pyxel.btnp(pyxel.KEY_SPACE):
            self._begin_enemy_turn()

    # ── Draw ──
    def draw(self) -> None:
        pyxel.cls(0)
        self._draw_borders()
        self._draw_grid()
        self._draw_stats()
        self._draw_cards()
        self._draw_harvest_buttons()
        self._draw_particles()
        self._draw_feedback_texts()
        self._draw_messages()
        self._draw_end_screen()
        self._draw_help()

    def _draw_borders(self) -> None:
        pyxel.rect(GRID_X - 2, GRID_Y - 2, GRID_W + 4, GRID_H + 4, 5)
        pyxel.rect(GRID_X, GRID_Y, GRID_W, GRID_H, 1)

    def _draw_grid(self) -> None:
        # Grid lines
        for r in range(GRID_ROWS + 1):
            y = GRID_Y + r * CELL_SIZE
            pyxel.line(GRID_X, y, GRID_X + GRID_W, y, 13)
        for c in range(GRID_COLS + 1):
            x = GRID_X + c * CELL_SIZE
            pyxel.line(x, GRID_Y, x, GRID_Y + GRID_H, 13)

        # Cells
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                vt = self.grid[r][c]
                if vt != EMPTY:
                    cx = GRID_X + c * CELL_SIZE + 1
                    cy = GRID_Y + r * CELL_SIZE + 1
                    color = VIRUS_COLORS[vt]
                    pyxel.rect(cx, cy, CELL_SIZE - 2, CELL_SIZE - 2, color)
                    ch = VIRUS_CHARS[vt]
                    tx = cx + (CELL_SIZE - 2 - len(ch) * 4) // 2 + 1
                    ty = cy + (CELL_SIZE - 2 - 6) // 2 + 1
                    pyxel.text(tx, ty, ch, 0)

        # Hover highlight
        if self.phase == Phase.INJECT and self.hovered_cell is not None:
            r, c = self.hovered_cell
            if self.grid[r][c] == EMPTY and self.selected_card >= 0:
                hx = GRID_X + c * CELL_SIZE
                hy = GRID_Y + r * CELL_SIZE
                pyxel.rectb(hx, hy, CELL_SIZE, CELL_SIZE, 7)

    def _draw_stats(self) -> None:
        # Player
        pyxel.text(4, 4, f"HP:{self.player_hp}/{self.player_max_hp}", 8)
        shield_y = 12
        if self.player_shield > 0:
            pyxel.text(4, shield_y, f"SHIELD:{self.player_shield}", 6)

        # Enemy
        ex = SCREEN_W - 110
        pyxel.text(ex, 4, f"BOSS HP:{self.enemy_hp}", 8)

        # Heat
        heat_color = 8 if self.heat <= MAX_HEAT else 9
        pyxel.text(4, 22, f"HEAT:{self.heat}/{MAX_HEAT}", heat_color)

        # Score & Turn
        pyxel.text(SCREEN_W - 65, 16, f"SC:{self.score}", 7)
        pyxel.text(SCREEN_W - 65, 26, f"T:{self.turn}", 5)

        # Enemy intent
        atk = self.enemy_base_atk + self.turn // 3
        if self.heat > MAX_HEAT:
            atk += (self.heat - MAX_HEAT) // 2
        pyxel.text(ex, 14, f"NEXT ATK:{atk}", 8)

    def _draw_cards(self) -> None:
        if self.phase != Phase.INJECT or not self.hand:
            return
        for i, vt in enumerate(self.hand):
            cx = CARDS_X + i * (CARD_W + CARD_GAP)
            color = VIRUS_COLORS[vt]
            border = 7 if i == self.selected_card else 5
            pyxel.rect(cx, CARD_Y, CARD_W, CARD_H, color)
            pyxel.rectb(cx, CARD_Y, CARD_W, CARD_H, border)
            name = VIRUS_NAMES[vt]
            tx = cx + (CARD_W - len(name) * 4) // 2
            ty = CARD_Y + (CARD_H - 6) // 2
            pyxel.text(tx, ty, name, 0)

    def _draw_harvest_buttons(self) -> None:
        if self.phase != Phase.HARVEST:
            return
        btn_w = 58
        btn_h = 18
        btns_x = (SCREEN_W - (4 * btn_w + 3 * 8)) // 2
        btn_y = CARD_Y + CARD_H + 10
        for i, vt in enumerate(VIRUS_TYPES):
            bx = btns_x + i * (btn_w + 8)
            color = VIRUS_COLORS[vt]
            pyxel.rect(bx, btn_y, btn_w, btn_h, color)
            name = VIRUS_NAMES[vt]
            tx = bx + (btn_w - len(name) * 4) // 2
            ty = btn_y + (btn_h - 6) // 2
            pyxel.text(tx, ty, name, 0)
            mult_label = f"x{VIRUS_DMG_MULT[vt]}"
            pyxel.text(bx + 2, btn_y + btn_h + 2, mult_label, 5)

        # Skip
        skip_w = 60
        skip_h = 14
        skip_x = SCREEN_W // 2 - skip_w // 2
        skip_y = btn_y + btn_h + 16
        pyxel.rect(skip_x, skip_y, skip_w, skip_h, 5)
        pyxel.text(skip_x + 14, skip_y + 4, "SKIP", 0)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 20.0
            if alpha > 0:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_feedback_texts(self) -> None:
        for txt, x, y, life, color in self.feedback_texts:
            alpha = life / 30.0
            if alpha > 0:
                draw_color = color if alpha > 0.5 else 5
                pyxel.text(int(x) - len(txt) * 2, int(y), txt, draw_color)

    def _draw_messages(self) -> None:
        y = GRID_Y + GRID_H + 2
        if self.harvest_result and self.harvest_result_timer > 0:
            pyxel.text(GRID_X, y, self.harvest_result, 7)
        elif self.message:
            pyxel.text(SCREEN_W // 2 - len(self.message) * 2, y, self.message, 9)

    def _draw_end_screen(self) -> None:
        if self.phase == Phase.VICTORY:
            pyxel.rect(SCREEN_W // 2 - 60, SCREEN_H // 2 - 20, 120, 52, 0)
            pyxel.rectb(SCREEN_W // 2 - 60, SCREEN_H // 2 - 20, 120, 52, 11)
            pyxel.text(SCREEN_W // 2 - 28, SCREEN_H // 2 - 12, "VICTORY!", 11)
            pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 + 2, f"Score: {self.score}", 7)
            pyxel.text(SCREEN_W // 2 - 48, SCREEN_H // 2 + 14, "R = Retry", 5)
        elif self.phase == Phase.DEFEAT:
            pyxel.rect(SCREEN_W // 2 - 60, SCREEN_H // 2 - 20, 120, 52, 0)
            pyxel.rectb(SCREEN_W // 2 - 60, SCREEN_H // 2 - 20, 120, 52, 8)
            pyxel.text(SCREEN_W // 2 - 32, SCREEN_H // 2 - 12, "DEFEAT", 8)
            pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 + 2, f"Score: {self.score}", 7)
            pyxel.text(SCREEN_W // 2 - 48, SCREEN_H // 2 + 14, "R = Retry", 5)

    def _draw_help(self) -> None:
        help_y = SCREEN_H - 8
        if self.phase == Phase.INJECT:
            pyxel.text(2, help_y, "1-3:card  Click:inject  SPACE:spread", 13)
        elif self.phase == Phase.HARVEST:
            pyxel.text(2, help_y, "1-4:harvest  SPACE:skip  CLICK:btn", 13)
        elif self.phase == Phase.SPREAD:
            pyxel.text(SCREEN_W // 2 - 30, help_y, "SPREADING...", 9)


if __name__ == "__main__":
    Game()
