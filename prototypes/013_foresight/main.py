"""FORESIGHT — Spend future knowledge to attack. Grid survival game.

Core hook: "Cost is future hand instead of HP" — attacking consumes your
vision of upcoming enemy spawns. The more you attack, the less you can
predict. Pure dodge mode when future runs out.

Reinterpreted from game_idea_factory Idea #4 (Score 31.45):
  "Calamity sealing dice/bag roguelite: cost is future hand, not HP"
  → Top-down grid survival (new genre for the collection).

Controls: WASD move, SPACE attack (costs 1 future), E end turn, R restart.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import NamedTuple

import pyxel

# ── Config ──
SCREEN_W = 320
SCREEN_H = 256
GRID_COLS = 8
GRID_ROWS = 8
CELL_SIZE = 28
GRID_X = (SCREEN_W - GRID_COLS * CELL_SIZE) // 2  # 48
GRID_Y = 16
MAX_HP = 10
INITIAL_FUTURE = 5
MAX_FUTURE = 8
SPAWN_HORIZON = 4  # how far ahead spawns are revealed (turns)
BASE_SPAWNS_PER_TURN = 2
KILL_FUTURE_CHANCE = 0.5  # chance to regain future on kill


class Phase(Enum):
    PLAYER_TURN = auto()
    ENEMY_TURN = auto()
    GAME_OVER = auto()


class Pos(NamedTuple):
    x: int
    y: int


@dataclass
class FutureCard:
    pos: Pos
    turns_until_spawn: int  # 0 = spawns this enemy-turn phase


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    """FORESIGHT — top-down grid survival."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="FORESIGHT", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.PLAYER_TURN
        self.player_pos: Pos = Pos(GRID_COLS // 2, GRID_ROWS - 1)
        self.enemies: list[Pos] = []
        self.future_cards: list[FutureCard] = []
        self.hp: int = MAX_HP
        self.score: int = 0
        self.turn: int = 0
        self.future_count: int = INITIAL_FUTURE
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.attack_flash: int = 0
        self.damage_flash: int = 0
        self.message: str = ""
        self.message_timer: int = 0
        self.kills_this_turn: int = 0
        # Seed initial future cards
        for _ in range(INITIAL_FUTURE):
            self._add_future_card()

    # ── helpers ──

    @staticmethod
    def _rand_edge_pos() -> Pos:
        """Random position on the grid edge."""
        edge = random.randint(0, 3)
        if edge == 0:  # top
            return Pos(random.randint(0, GRID_COLS - 1), 0)
        if edge == 1:  # bottom
            return Pos(random.randint(0, GRID_COLS - 1), GRID_ROWS - 1)
        if edge == 2:  # left
            return Pos(0, random.randint(0, GRID_ROWS - 1))
        # right
        return Pos(GRID_COLS - 1, random.randint(0, GRID_ROWS - 1))

    def _add_future_card(self) -> None:
        turns = random.randint(1, SPAWN_HORIZON)
        pos = self._rand_edge_pos()
        self.future_cards.append(FutureCard(pos, turns))

    @staticmethod
    def _grid_to_screen(pos: Pos) -> tuple[int, int]:
        return (
            GRID_X + pos.x * CELL_SIZE + CELL_SIZE // 2,
            GRID_Y + pos.y * CELL_SIZE + CELL_SIZE // 2,
        )

    @staticmethod
    def _is_adjacent(a: Pos, b: Pos) -> bool:
        return abs(a.x - b.x) + abs(a.y - b.y) == 1

    def _spawn_particles(
        self, sx: int, sy: int, color: int, count: int = 8
    ) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.5, 2.0)
            self.particles.append(
                Particle(
                    float(sx),
                    float(sy),
                    speed * math.cos(angle),
                    speed * math.sin(angle),
                    random.randint(8, 16),
                    color,
                )
            )

    def _spawn_floating_text(
        self, sx: int, sy: int, text: str, color: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(float(sx), float(sy), text, 20, color)
        )

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 30

    @property
    def _spawns_per_turn(self) -> int:
        """Escalate spawns as turns increase."""
        return BASE_SPAWNS_PER_TURN + self.turn // 8

    # ── update ──

    def update(self) -> None:
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        if self.phase == Phase.PLAYER_TURN:
            self._update_player_turn()
        elif self.phase == Phase.ENEMY_TURN:
            self._update_enemy_turn()

        # Update visual effects
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

        for ft in self.floating_texts[:]:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

        if self.attack_flash > 0:
            self.attack_flash -= 1
        if self.damage_flash > 0:
            self.damage_flash -= 1
        if self.message_timer > 0:
            self.message_timer -= 1

    def _update_player_turn(self) -> None:
        # ── Movement (one step per keypress) ──
        dx, dy = 0, 0
        if pyxel.btnp(pyxel.KEY_W) or pyxel.btnp(pyxel.KEY_UP):
            dy = -1
        elif pyxel.btnp(pyxel.KEY_S) or pyxel.btnp(pyxel.KEY_DOWN):
            dy = 1
        elif pyxel.btnp(pyxel.KEY_A) or pyxel.btnp(pyxel.KEY_LEFT):
            dx = -1
        elif pyxel.btnp(pyxel.KEY_D) or pyxel.btnp(pyxel.KEY_RIGHT):
            dx = 1

        if dx != 0 or dy != 0:
            new_pos = Pos(self.player_pos.x + dx, self.player_pos.y + dy)
            if 0 <= new_pos.x < GRID_COLS and 0 <= new_pos.y < GRID_ROWS:
                if new_pos not in self.enemies:
                    self.player_pos = new_pos

        # ── Attack (costs 1 future card) ──
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._do_attack()

        # ── End turn ──
        if pyxel.btnp(pyxel.KEY_E):
            self.phase = Phase.ENEMY_TURN
            self.turn += 1
            self.score += 1  # survival bonus
            self.kills_this_turn = 0

    def _do_attack(self) -> None:
        if self.future_count <= 0:
            self._show_message("NO FUTURE LEFT!")
            return

        # Attack all adjacent enemies
        attacked_positions: list[Pos] = []
        for enemy in self.enemies[:]:
            if self._is_adjacent(self.player_pos, enemy):
                attacked_positions.append(enemy)

        if not attacked_positions:
            self._show_message("NO TARGET")
            return

        for enemy in attacked_positions:
            self.enemies.remove(enemy)
            self.score += 5
            self.kills_this_turn += 1
            sx, sy = self._grid_to_screen(enemy)
            self._spawn_particles(sx, sy, pyxel.COLOR_RED, 8)
            self._spawn_floating_text(sx, sy - 8, "+5", pyxel.COLOR_YELLOW)

        self.future_count -= 1
        self.attack_flash = 8
        killed = len(attacked_positions)
        self._show_message(f"HIT x{killed}! -1 FUT")

        # Chance to regain future on kill (reward for aggressive play)
        for _ in range(killed):
            if random.random() < KILL_FUTURE_CHANCE:
                self.future_count = min(self.future_count + 1, MAX_FUTURE)
                self._show_message("FUTURE REGAINED!")

    def _update_enemy_turn(self) -> None:
        # ── 1. Move enemies toward player ──
        for enemy in self.enemies[:]:
            dx, dy = self._enemy_step(enemy)
            new_pos = Pos(enemy.x + dx, enemy.y + dy)

            if new_pos == self.player_pos:
                # Enemy reaches player → deal damage
                self.hp -= 1
                self.damage_flash = 10
                sx, sy = self._grid_to_screen(self.player_pos)
                self._spawn_particles(sx, sy, pyxel.COLOR_ORANGE, 6)
                self._spawn_floating_text(sx, sy - 8, "-1 HP", pyxel.COLOR_RED)
                self._show_message("DAMAGE!")
                if self.hp <= 0:
                    self.phase = Phase.GAME_OVER
                    self._show_message("GAME OVER")
                    return
                continue  # enemy stays in place (attacks, doesn't move)

            # Check bounds and collisions
            if not (0 <= new_pos.x < GRID_COLS and 0 <= new_pos.y < GRID_ROWS):
                continue  # blocked by wall
            if new_pos in self.enemies:
                continue  # blocked by other enemy

            # Move enemy
            idx = self.enemies.index(enemy)
            self.enemies[idx] = new_pos

        # ── 2. Spawn enemies from future cards with timer=0 ──
        spawned_count = 0
        for card in self.future_cards[:]:
            if card.turns_until_spawn <= 0:
                if card.pos != self.player_pos and card.pos not in self.enemies:
                    self.enemies.append(card.pos)
                    sx, sy = self._grid_to_screen(card.pos)
                    self._spawn_particles(sx, sy, pyxel.COLOR_CYAN, 4)
                    spawned_count += 1
                self.future_cards.remove(card)

        if spawned_count > 0:
            self._show_message(f"SPAWNED x{spawned_count}!")

        # ── 3. Decrement all future card timers ──
        for card in self.future_cards:
            card.turns_until_spawn -= 1

        # ── 4. Add new future cards for upcoming turns ──
        for _ in range(self._spawns_per_turn):
            self._add_future_card()

        # ── 5. Trim excess ──
        # Remove cards that are too far in the future (oldest first)
        while len(self.future_cards) > MAX_FUTURE:
            self.future_cards.pop(0)

        # ── 6. Back to player turn ──
        self.phase = Phase.PLAYER_TURN

    def _enemy_step(self, enemy: Pos) -> tuple[int, int]:
        """Compute enemy move direction toward player with randomized axis priority."""
        dx = 0
        dy = 0
        if enemy.x < self.player_pos.x:
            dx = 1
        elif enemy.x > self.player_pos.x:
            dx = -1
        if enemy.y < self.player_pos.y:
            dy = 1
        elif enemy.y > self.player_pos.y:
            dy = -1

        # Randomize: sometimes move x first, sometimes y first
        if dx != 0 and dy != 0:
            if random.random() < 0.5:
                dy = 0  # move only x this turn
            else:
                dx = 0  # move only y this turn
        return (dx, dy)

    # ── draw ──

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        self._draw_grid()
        self._draw_future_previews()
        self._draw_enemies()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_ui()
        self._draw_message()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_grid(self) -> None:
        for col in range(GRID_COLS + 1):
            px = GRID_X + col * CELL_SIZE
            pyxel.line(
                px, GRID_Y, px, GRID_Y + GRID_ROWS * CELL_SIZE, pyxel.COLOR_DARK_BLUE
            )
        for row in range(GRID_ROWS + 1):
            py = GRID_Y + row * CELL_SIZE
            pyxel.line(
                GRID_X, py, GRID_X + GRID_COLS * CELL_SIZE, py, pyxel.COLOR_DARK_BLUE
            )

    def _draw_future_previews(self) -> None:
        for card in self.future_cards:
            sx, sy = self._grid_to_screen(card.pos)
            r = CELL_SIZE // 2 - 3
            if card.turns_until_spawn <= 1:
                color = pyxel.COLOR_YELLOW  # imminent!
            else:
                color = pyxel.COLOR_CYAN
            pyxel.circb(sx, sy, r, color)
            # Show countdown number
            timer_str = str(max(0, card.turns_until_spawn))
            pyxel.text(sx - 2, sy - 3, timer_str, color)

    def _draw_enemies(self) -> None:
        for enemy in self.enemies:
            sx, sy = self._grid_to_screen(enemy)
            r = CELL_SIZE // 2 - 3
            # Enemy body
            pyxel.circ(sx, sy, r, pyxel.COLOR_RED)
            pyxel.circb(sx, sy, r, pyxel.COLOR_BROWN)
            # Eyes
            pyxel.pset(sx - 3, sy - 2, pyxel.COLOR_WHITE)
            pyxel.pset(sx + 3, sy - 2, pyxel.COLOR_WHITE)

    def _draw_player(self) -> None:
        px, py = self._grid_to_screen(self.player_pos)
        r = CELL_SIZE // 2 - 3

        # Flash on damage / attack
        if self.damage_flash > 0 and self.damage_flash % 4 < 2:
            body_color = pyxel.COLOR_ORANGE
        elif self.attack_flash > 0:
            body_color = pyxel.COLOR_YELLOW
        else:
            body_color = pyxel.COLOR_GREEN

        pyxel.circ(px, py, r, body_color)
        pyxel.circb(px, py, r, pyxel.COLOR_WHITE)
        # Player symbol
        pyxel.text(px - 2, py - 3, "@", pyxel.COLOR_BLACK)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha_color = p.color if p.life > 4 else pyxel.COLOR_GRAY
            pyxel.pset(int(p.x), int(p.y), alpha_color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 20
            color = ft.color if alpha > 0.3 else pyxel.COLOR_GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, color)

    def _draw_ui(self) -> None:
        # Title
        pyxel.text(2, 2, "FORESIGHT", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W - 65, 2, f"SCR:{self.score}", pyxel.COLOR_YELLOW)

        # HP bar
        hp_label = "HP:"
        pyxel.text(2, SCREEN_H - 20, hp_label, pyxel.COLOR_WHITE)
        bar_x, bar_y = 24, SCREEN_H - 18
        bar_w, bar_h = 80, 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, pyxel.COLOR_DARK_BLUE)
        hp_w = int(bar_w * self.hp / MAX_HP)
        hp_color = pyxel.COLOR_GREEN if self.hp > 3 else pyxel.COLOR_RED
        if hp_w > 0:
            pyxel.rect(bar_x, bar_y, hp_w, bar_h, hp_color)

        # Future cards indicator
        pyxel.text(120, SCREEN_H - 20, "FUTURE:", pyxel.COLOR_CYAN)
        for i in range(self.future_count):
            dot_color = pyxel.COLOR_CYAN if i < self.future_count else pyxel.COLOR_GRAY
            pyxel.circ(168 + i * 7, SCREEN_H - 16, 2, dot_color)

        # Turn counter
        pyxel.text(SCREEN_W - 50, SCREEN_H - 20, f"T:{self.turn}", pyxel.COLOR_WHITE)

        # Controls
        pyxel.text(
            2, SCREEN_H - 8, "WASD:Move SPACE:Atk E:End", pyxel.COLOR_GRAY
        )

    def _draw_message(self) -> None:
        if self.message_timer <= 0:
            return
        msg_w = len(self.message) * 4
        msg_x = (SCREEN_W - msg_w) // 2
        msg_y = GRID_Y + GRID_ROWS * CELL_SIZE + 4
        pyxel.text(msg_x, msg_y, self.message, pyxel.COLOR_WHITE)

    def _draw_game_over(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, pyxel.COLOR_BLACK)
        pyxel.text(
            SCREEN_W // 2 - 24, SCREEN_H // 2 - 20, "GAME OVER", pyxel.COLOR_RED
        )
        pyxel.text(
            SCREEN_W // 2 - 40, SCREEN_H // 2, f"SCORE: {self.score}",
            pyxel.COLOR_YELLOW,
        )
        pyxel.text(
            SCREEN_W // 2 - 50, SCREEN_H // 2 + 12, f"TURNS: {self.turn}",
            pyxel.COLOR_WHITE,
        )
        pyxel.text(
            SCREEN_W // 2 - 40, SCREEN_H // 2 + 24, "KILL BONUS: +5ea",
            pyxel.COLOR_GRAY,
        )
        pyxel.text(
            SCREEN_W // 2 - 30, SCREEN_H // 2 + 40, "R: RESTART",
            pyxel.COLOR_GREEN,
        )


if __name__ == "__main__":
    Game()
