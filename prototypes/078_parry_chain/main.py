"""078_parry_chain — 色合わせパリィ・フェンシングゲーム。

Core fun moment: 敵の攻撃色を見極め、同色ガードを連続成功させてCOMBOを積み、
SUPER RIPOSTEで画面の敵を一掃する瞬間
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
CENTER_X = 160
CENTER_Y = 120
PARRY_WINDOW = 40
CENTER_HIT_DIST = 10
SUPER_RIPOSTE_COMBO = 5
STARTING_HP = 5
GAME_DURATION = 90 * 30  # 90s at 30fps
SPAWN_INTERVAL_START = 60
SPAWN_INTERVAL_END = 20
ENEMY_SPEED_MIN = 2.0
ENEMY_SPEED_MAX = 4.0
FPS = 30

BLACK = 0
NAVY = 1
PURPLE = 2
GREEN = 3
BROWN = 4
DARK_BLUE = 5
LIGHT_BLUE = 6
WHITE = 7
RED = 8
ORANGE = 9
YELLOW = 10
LIME = 11
CYAN = 12
GRAY = 13
PINK = 14
PEACH = 15

DIR_COLORS: tuple[int, int, int, int] = (RED, LIGHT_BLUE, GREEN, YELLOW)
DIR_NAMES: tuple[str, str, str, str] = ("LEFT", "RIGHT", "UP", "DOWN")
DIR_KEYS: tuple[int, int, int, int] = (
    pyxel.KEY_LEFT,
    pyxel.KEY_RIGHT,
    pyxel.KEY_UP,
    pyxel.KEY_DOWN,
)


class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Enemy:
    x: float
    y: float
    color: int
    direction: int
    speed: float
    active: bool = True


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


# ── Game Class ──────────────────────────────────────────────────────────

class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="PARRY CHAIN", fps=FPS, display_scale=2)
        font_path = str(Path(__file__).with_name("k8x12.bdf"))
        if Path(font_path).exists():
            pyxel.load(
                font_path,
                exclude_images=True,
                exclude_sounds=True,
                exclude_musics=True,
            )
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.hp: int = STARTING_HP
        self.enemies: list[Enemy] = []
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.spawn_timer: int = SPAWN_INTERVAL_START
        self.ghost_direction: int = -1
        self._next_ghost_direction: int = -1
        self.game_timer: int = GAME_DURATION
        self._shake_frames: int = 0
        self._flash_frames: int = 0
        self._rng: random.Random = getattr(self, "_rng", random.Random())

    # ── Testable Logic ─────────────────────────────────────────────────

    def _spawn_enemy(self, direction: int | None = None) -> Enemy:
        if direction is None:
            direction = self._rng.randint(0, 3)
        color = DIR_COLORS[direction]
        speed = self._rng.uniform(ENEMY_SPEED_MIN, ENEMY_SPEED_MAX)

        if direction == 0:  # LEFT
            x = -10.0
            y = CENTER_Y + self._rng.uniform(-60, 60)
        elif direction == 1:  # RIGHT
            x = float(SCREEN_W + 10)
            y = CENTER_Y + self._rng.uniform(-60, 60)
        elif direction == 2:  # UP
            x = CENTER_X + self._rng.uniform(-80, 80)
            y = -10.0
        else:  # DOWN
            x = CENTER_X + self._rng.uniform(-80, 80)
            y = float(SCREEN_H + 10)

        return Enemy(x=x, y=y, color=color, direction=direction, speed=speed)

    def _update_enemies(self) -> int:
        hit_count = 0
        for e in self.enemies:
            if not e.active:
                continue
            dx = CENTER_X - e.x
            dy = CENTER_Y - e.y
            dist = math.hypot(dx, dy)
            if dist < 0.5:
                e.x, e.y = CENTER_X, CENTER_Y
            else:
                e.x += dx / dist * e.speed
                e.y += dy / dist * e.speed
            if self._enemy_at_center(e):
                e.active = False
                hit_count += 1
        return hit_count

    @staticmethod
    def _enemy_at_center(enemy: Enemy) -> bool:
        return math.hypot(enemy.x - CENTER_X, enemy.y - CENTER_Y) <= CENTER_HIT_DIST

    @staticmethod
    def _enemy_in_parry_window(enemy: Enemy) -> bool:
        return (
            enemy.active
            and abs(enemy.x - CENTER_X) <= PARRY_WINDOW
            and abs(enemy.y - CENTER_Y) <= PARRY_WINDOW
        )

    def _try_parry(self, direction: int) -> tuple[bool, int]:
        color = DIR_COLORS[direction]
        destroyed = 0
        for e in self.enemies:
            if e.active and e.color == color and self._enemy_in_parry_window(e):
                e.active = False
                destroyed += 1
                self._spawn_parry_particles(e.x, e.y, color)
                gained = 100 * max(1, self.combo + destroyed)
                self._spawn_float_text(e.x, e.y - 8, f"+{gained}", WHITE)

        if destroyed > 0:
            self.combo += destroyed
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self.score += 100 * self.combo * destroyed

            if self.combo >= SUPER_RIPOSTE_COMBO:
                riposte_count = self._trigger_riposte()
                if riposte_count > 0:
                    pass
            return True, destroyed
        else:
            self.combo = 0
            return False, 0

    def _trigger_riposte(self) -> int:
        count = 0
        for e in self.enemies:
            if e.active:
                e.active = False
                count += 1
                self._spawn_riposte_particles(e.x, e.y, e.color)
        if count > 0:
            bonus = 500 * count
            self.score += bonus
            self._shake_frames = 15
            self._flash_frames = 10
            self._spawn_float_text(
                CENTER_X, CENTER_Y - 30, f"SUPER RIPOSTE! +{bonus}", PINK
            )
        return count

    def _get_next_spawn_interval(self) -> int:
        elapsed = GAME_DURATION - self.game_timer
        progress = min(1.0, elapsed / float(GAME_DURATION))
        interval = (
            SPAWN_INTERVAL_START
            - (SPAWN_INTERVAL_START - SPAWN_INTERVAL_END) * progress
        )
        return max(SPAWN_INTERVAL_END, int(interval))

    def _cleanup_enemies(self) -> None:
        self.enemies = [e for e in self.enemies if e.active]

    # ── Particles & Floating Text ──────────────────────────────────────

    def _spawn_parry_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(10):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=20,
                    color=color,
                )
            )

    def _spawn_hit_particles(self, x: float, y: float) -> None:
        for _ in range(6):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(0.5, 1.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=12,
                    color=RED,
                )
            )

    def _spawn_riposte_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(25):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(1.0, 3.5)
            mix_color = self._rng.choice([color, WHITE, PINK])
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=30,
                    color=mix_color,
                )
            )

    def _spawn_float_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floats.append(FloatingText(x=x, y=y, text=text, life=30, color=color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floats(self) -> None:
        for ft in self.floats:
            ft.y -= 0.6
            ft.life -= 1
        self.floats = [ft for ft in self.floats if ft.life > 0]

    # ── Update ─────────────────────────────────────────────────────────

    def update(self) -> None:
        if self._shake_frames > 0:
            self._shake_frames -= 1
        if self._flash_frames > 0:
            self._flash_frames -= 1

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self._start_game()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self._start_game()
            return

        if self.phase == Phase.PLAYING:
            self._update_playing()

    def _update_playing(self) -> None:
        self._update_particles()
        self._update_floats()

        self.game_timer -= 1
        if self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            # Use ghost direction (pre-rolled) for this spawn
            direction = self._next_ghost_direction
            if direction < 0:
                direction = self._rng.randint(0, 3)
            self.enemies.append(self._spawn_enemy(direction))
            self.ghost_direction = direction
            # Pre-roll next ghost
            self._next_ghost_direction = self._rng.randint(0, 3)
            self.spawn_timer = self._get_next_spawn_interval()

        hits = self._update_enemies()
        for _ in range(hits):
            self.hp -= 1
            self.combo = 0
            self._spawn_hit_particles(CENTER_X, CENTER_Y)
            self._spawn_float_text(CENTER_X, CENTER_Y - 20, "-1 HP", RED)
            if self.hp <= 0:
                self.phase = Phase.GAME_OVER
                return

        for d in range(4):
            if pyxel.btnp(DIR_KEYS[d]):
                self._try_parry(d)
                break

        self._cleanup_enemies()

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.hp = STARTING_HP
        self.enemies.clear()
        self.particles.clear()
        self.floats.clear()
        self.spawn_timer = SPAWN_INTERVAL_START // 2
        self.ghost_direction = -1
        self._next_ghost_direction = self._rng.randint(0, 3)
        self.game_timer = GAME_DURATION
        self._shake_frames = 0
        self._flash_frames = 0

    # ── Draw ───────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self._shake_frames > 0:
            ox = self._rng.randint(-3, 3)
            oy = self._rng.randint(-3, 3)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_playing()
            self._draw_game_over_overlay()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()

        pyxel.camera(0, 0)

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)

        title = "PARRY CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * 4 // 2, 30, title, WHITE)

        lines = [
            ("MATCH ENEMY COLOR >", WHITE),
            ("PRESS MATCHING ARROW KEY", WHITE),
            ("", WHITE),
            ("RED    = LEFT", RED),
            ("CYAN   = RIGHT", LIGHT_BLUE),
            ("GREEN  = UP", GREEN),
            ("YELLOW = DOWN", YELLOW),
            ("", WHITE),
            ("Parry near center for COMBO", GRAY),
            ("5x COMBO = SUPER RIPOSTE!", GRAY),
            ("", WHITE),
            ("Survive 90 sec / HP=5", GRAY),
            ("", WHITE),
            ("PRESS SPACE TO START", WHITE),
        ]
        y = 62
        for text, color in lines:
            pyxel.text(SCREEN_W // 2 - len(text) * 4 // 2, y, text, color)
            y += 10

    def _draw_playing(self) -> None:
        if self.phase != Phase.GAME_OVER:
            self._draw_bg()

        # Ghost echo
        if self.ghost_direction >= 0:
            self._draw_ghost()

        # Enemies
        for e in self.enemies:
            if e.active:
                self._draw_enemy(e)

        # Player
        self._draw_player()

        # Particles (always visible)
        self._draw_particles()

        # Floating texts
        self._draw_floats()

        # HUD
        self._draw_hud()

        # Flash overlay
        if self._flash_frames > 0 and self.phase != Phase.GAME_OVER:
            alpha = self._flash_frames / 10.0
            c = PINK if alpha > 0.5 else WHITE
            pyxel.cls(c)

    def _draw_bg(self) -> None:
        pyxel.cls(BLACK)
        for x in range(0, SCREEN_W, 40):
            pyxel.line(x, 0, x, SCREEN_H, NAVY)
        for y in range(0, SCREEN_H, 40):
            pyxel.line(0, y, SCREEN_W, y, NAVY)

        # Parry window zone indicator
        pyxel.rectb(
            CENTER_X - PARRY_WINDOW,
            CENTER_Y - PARRY_WINDOW,
            PARRY_WINDOW * 2,
            PARRY_WINDOW * 2,
            NAVY,
        )

    def _draw_ghost(self) -> None:
        d = self.ghost_direction
        if d == 0:
            gx, gy = 20, CENTER_Y
        elif d == 1:
            gx, gy = SCREEN_W - 20, CENTER_Y
        elif d == 2:
            gx, gy = CENTER_X, 20
        else:
            gx, gy = CENTER_X, SCREEN_H - 20

        pulse = 6 + int(3 * math.sin(pyxel.frame_count * 0.08))
        pyxel.circb(int(gx), int(gy), pulse, CYAN)
        pyxel.circb(int(gx), int(gy), pulse + 4, CYAN)

    def _draw_enemy(self, e: Enemy) -> None:
        ex, ey = int(e.x), int(e.y)
        color = e.color

        # Body circle
        pyxel.circ(ex, ey, 8, color)
        pyxel.circb(ex, ey, 8, WHITE)
        pyxel.circb(ex, ey, 5, WHITE)

        # Direction arrow
        if e.direction == 0:
            pyxel.tri(ex - 16, ey - 4, ex - 16, ey + 4, ex - 8, ey, color)
        elif e.direction == 1:
            pyxel.tri(ex + 16, ey - 4, ex + 16, ey + 4, ex + 8, ey, color)
        elif e.direction == 2:
            pyxel.tri(ex - 4, ey - 16, ex + 4, ey - 16, ex, ey - 8, color)
        else:
            pyxel.tri(ex - 4, ey + 16, ex + 4, ey + 16, ex, ey + 8, color)

    def _draw_player(self) -> None:
        px, py = CENTER_X, CENTER_Y

        # Head
        pyxel.circ(px, py - 6, 4, WHITE)
        # Body
        pyxel.line(px, py - 2, px, py + 10, WHITE)
        # Arms
        pyxel.line(px, py + 2, px - 8, py - 6, WHITE)
        pyxel.line(px, py + 2, px + 8, py - 6, WHITE)
        # Legs
        pyxel.line(px, py + 10, px - 5, py + 18, WHITE)
        pyxel.line(px, py + 10, px + 5, py + 18, WHITE)

        # Guard ring
        guard_color = PINK if self.combo >= SUPER_RIPOSTE_COMBO else WHITE
        if self.combo >= SUPER_RIPOSTE_COMBO:
            glow = 1 + int(3 * math.sin(pyxel.frame_count * 0.2))
            pyxel.circb(px, py, 16 + glow, guard_color)
        else:
            pyxel.circb(px, py, 16, guard_color)

        # 4 direction color indicators around player
        dir_positions = [
            (px - 22, py),
            (px + 22, py),
            (px, py - 22),
            (px, py + 22),
        ]
        for i, (ax, ay) in enumerate(dir_positions):
            col = DIR_COLORS[i]
            pyxel.circb(ax, ay, 6, col)
            if i == 0:
                pyxel.tri(ax - 8, ay - 3, ax - 8, ay + 3, ax - 3, ay, col)
            elif i == 1:
                pyxel.tri(ax + 8, ay - 3, ax + 8, ay + 3, ax + 3, ay, col)
            elif i == 2:
                pyxel.tri(ax - 3, ay - 8, ax + 3, ay - 8, ax, ay - 3, col)
            else:
                pyxel.tri(ax - 3, ay + 8, ax + 3, ay + 8, ax, ay + 3, col)

    def _draw_particles(self) -> None:
        for p in self.particles:
            px, py = int(p.x), int(p.y)
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                size = max(1, p.life // 6)
                pyxel.rect(px, py, size, size, p.color)

    def _draw_floats(self) -> None:
        for ft in self.floats:
            x = int(ft.x - len(ft.text) * 2)
            y = int(ft.y)
            pyxel.text(x, y, ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 2, f"SCORE: {self.score}", WHITE)

        if self.combo >= 2:
            combo_text = f"COMBO x{self.combo}"
            combo_color = PINK if self.combo >= SUPER_RIPOSTE_COMBO else ORANGE
            pyxel.text(
                SCREEN_W // 2 - len(combo_text) * 2, 2, combo_text, combo_color
            )

        hp_text = "HP: " + "I" * self.hp
        pyxel.text(SCREEN_W - 60, 2, hp_text, RED if self.hp <= 2 else WHITE)

        seconds = max(0, self.game_timer // FPS)
        timer_text = f"TIME: {seconds}s"
        timer_color = RED if seconds <= 15 else LIME
        pyxel.text(
            SCREEN_W // 2 - len(timer_text) * 2,
            SCREEN_H - 10,
            timer_text,
            timer_color,
        )

        if self.max_combo > 0:
            mc_text = f"MAX COMBO: {self.max_combo}"
            pyxel.text(4, 12, mc_text, GRAY)

    def _draw_game_over_overlay(self) -> None:
        bx = SCREEN_W // 2 - 90
        by = SCREEN_H // 2 - 70
        bw = 180
        bh = 130
        pyxel.rect(bx, by, bw, bh, BLACK)
        pyxel.rectb(bx, by, bw, bh, WHITE)

        lines = [
            ("GAME OVER", RED),
            ("", WHITE),
            (f"SCORE: {self.score}", YELLOW),
            (f"MAX COMBO: {self.max_combo}", WHITE),
            ("", WHITE),
            ("PRESS SPACE TO RETRY", GRAY),
        ]
        y = SCREEN_H // 2 - 60
        for text, color in lines:
            pyxel.text(SCREEN_W // 2 - len(text) * 4 // 2, y, text, color)
            y += 12


if __name__ == "__main__":
    Game()
