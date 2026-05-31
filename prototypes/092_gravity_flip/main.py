from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ─── Color Constants ───────────────────────────────────────────────────────
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

GEM_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]

# ─── Constants ──────────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
ROOM_L = 4
ROOM_T = 16
ROOM_R = SCREEN_W - 4
ROOM_B = SCREEN_H - 4
PLAYER_RADIUS = 6.0
GEM_RADIUS = 4.0
GRAVITY_ACCEL = 0.3
MAX_SPEED = 3.0
DRAG = 0.95
HEAT_PER_FLIP = 15
HEAT_DECAY = 0.3
MAX_HEAT = 100
MAX_HP = 5
INVULN_FRAMES = 90
SUPER_DURATION = 480
GAME_TIMER = 3600
GEM_SPAWN_MIN = 60
GEM_SPAWN_MAX = 90
SPIKE_SPAWN_MIN = 180
SPIKE_SPAWN_MAX = 300
BASE_GEM_VALUE = 10
EMPTY_COLOR = -1

# ─── Enums ──────────────────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class Gravity(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


# ─── Data Classes ───────────────────────────────────────────────────────────


@dataclass
class Gem:
    x: float
    y: float
    color: int
    value: int = BASE_GEM_VALUE
    radius: float = GEM_RADIUS


@dataclass
class Spike:
    x: float
    y: float
    wall: str
    width: float = 16.0
    height: float = 4.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    max_life: int = 20


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.0


# ─── Game Class ─────────────────────────────────────────────────────────────


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Gravity Flux", display_scale=2)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player_x: float = SCREEN_W / 2
        self.player_y: float = SCREEN_H / 2
        self.player_vx: float = 0.0
        self.player_vy: float = 0.0
        self.gravity: Gravity = Gravity.DOWN
        self.player_radius: float = PLAYER_RADIUS
        self.hp: int = MAX_HP
        self.max_hp: int = MAX_HP
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.combo_color: int = EMPTY_COLOR
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.heat: float = 0.0
        self.max_heat: int = MAX_HEAT
        self.invuln_timer: int = 0
        self.game_timer: int = GAME_TIMER
        self.gems: list[Gem] = []
        self.spikes: list[Spike] = []
        self.particles: list[Particle] = []
        self.float_texts: list[FloatText] = []
        self.spawn_timer: int = 0
        self.spike_spawn_timer: int = 0
        self.shake_frames: int = 0
        self.high_score: int = 0

    # ─── Phase Machine ──────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        if pyxel.btnp(pyxel.KEY_UP):
            self._on_gravity_flip(Gravity.UP)
        elif pyxel.btnp(pyxel.KEY_DOWN):
            self._on_gravity_flip(Gravity.DOWN)
        elif pyxel.btnp(pyxel.KEY_LEFT):
            self._on_gravity_flip(Gravity.LEFT)
        elif pyxel.btnp(pyxel.KEY_RIGHT):
            self._on_gravity_flip(Gravity.RIGHT)

        self._apply_gravity()
        self._clamp_to_room()
        self._collect_gems()
        self._check_spike_collisions()
        self._update_super_mode()
        self._update_heat()
        self._update_timers()
        self._update_particles()
        self._update_float_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self.hp <= 0 or self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            if self.score > self.high_score:
                self.high_score = self.score

    # ─── Testable Logic ─────────────────────────────────────────────────────

    def _on_gravity_flip(self, new_gravity: Gravity) -> None:
        if new_gravity == self.gravity:
            return
        self.gravity = new_gravity
        self.heat += HEAT_PER_FLIP
        if self.gravity == Gravity.UP:
            self.player_vy = -MAX_SPEED
        elif self.gravity == Gravity.DOWN:
            self.player_vy = MAX_SPEED
        elif self.gravity == Gravity.LEFT:
            self.player_vx = -MAX_SPEED
        elif self.gravity == Gravity.RIGHT:
            self.player_vx = MAX_SPEED

    def _apply_gravity(self) -> None:
        if self.gravity == Gravity.UP:
            self.player_vy -= GRAVITY_ACCEL
        elif self.gravity == Gravity.DOWN:
            self.player_vy += GRAVITY_ACCEL
        elif self.gravity == Gravity.LEFT:
            self.player_vx -= GRAVITY_ACCEL
        elif self.gravity == Gravity.RIGHT:
            self.player_vx += GRAVITY_ACCEL

        self.player_vx *= DRAG
        self.player_vy *= DRAG

        speed = math.sqrt(self.player_vx**2 + self.player_vy**2)
        if speed > MAX_SPEED:
            scale = MAX_SPEED / speed
            self.player_vx *= scale
            self.player_vy *= scale

        self.player_x += self.player_vx
        self.player_y += self.player_vy

    def _clamp_to_room(self) -> None:
        mnx = ROOM_L + self.player_radius
        mxx = ROOM_R - self.player_radius
        mny = ROOM_T + self.player_radius
        mxy = ROOM_B - self.player_radius

        if self.player_x < mnx:
            self.player_x = mnx
            self.player_vx = 0.0
        elif self.player_x > mxx:
            self.player_x = mxx
            self.player_vx = 0.0

        if self.player_y < mny:
            self.player_y = mny
            self.player_vy = 0.0
        elif self.player_y > mxy:
            self.player_y = mxy
            self.player_vy = 0.0

    def _collect_gems(self) -> None:
        to_remove: list[int] = []
        for i, gem in enumerate(self.gems):
            dx = self.player_x - gem.x
            dy = self.player_y - gem.y
            if math.sqrt(dx * dx + dy * dy) < self.player_radius + gem.radius:
                to_remove.append(i)
                self._spawn_collect_particles(gem.x, gem.y, gem.color)

                if self.combo_color == gem.color:
                    self.combo += 1
                else:
                    self.combo = 1
                    self.combo_color = gem.color

                if self.combo > self.max_combo:
                    self.max_combo = self.combo

                if self.combo >= 3:
                    self._activate_super_mode()

                value = gem.value * self.combo
                if self.super_mode:
                    value *= 3
                self.score += value

                if self.combo >= 3:
                    txt_color = ORANGE
                elif self.combo >= 2:
                    txt_color = gem.color
                else:
                    txt_color = WHITE
                self.float_texts.append(
                    FloatText(gem.x, gem.y, f"+{value}", 30, txt_color)
                )

        for i in reversed(to_remove):
            self.gems.pop(i)

    def _check_spike_collisions(self) -> None:
        if self.invuln_timer > 0 or self.super_mode:
            return

        for spike in self.spikes:
            if spike.wall == "top":
                bx = spike.x - spike.width / 2
                by = ROOM_T
                bw = spike.width
                bh = spike.height
            elif spike.wall == "bottom":
                bx = spike.x - spike.width / 2
                by = ROOM_B - spike.height
                bw = spike.width
                bh = spike.height
            elif spike.wall == "left":
                bx = ROOM_L
                by = spike.y - spike.width / 2
                bw = spike.height
                bh = spike.width
            else:  # "right"
                bx = ROOM_R - spike.height
                by = spike.y - spike.width / 2
                bw = spike.height
                bh = spike.width

            closest_x = max(bx, min(self.player_x, bx + bw))
            closest_y = max(by, min(self.player_y, by + bh))
            dx = self.player_x - closest_x
            dy = self.player_y - closest_y
            if dx * dx + dy * dy < self.player_radius * self.player_radius:
                self.hp -= 1
                self.invuln_timer = INVULN_FRAMES
                self.shake_frames = 8
                self._spawn_damage_particles(self.player_x, self.player_y)
                break

    def _update_super_mode(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

    def _activate_super_mode(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat -= HEAT_DECAY
            if self.heat < 0:
                self.heat = 0.0

        if self.heat >= self.max_heat and not self.super_mode:
            self.hp -= 1
            self.heat = 0.0
            self.shake_frames = 8
            self._spawn_damage_particles(self.player_x, self.player_y)

    def _update_timers(self) -> None:
        self.game_timer -= 1

        if self.invuln_timer > 0:
            self.invuln_timer -= 1

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_gem()
            wave = self._current_wave()
            spawn_min = max(20, GEM_SPAWN_MIN - wave * 5)
            spawn_max = max(40, GEM_SPAWN_MAX - wave * 5)
            self.spawn_timer = self._rng.randint(spawn_min, spawn_max)

        self.spike_spawn_timer -= 1
        if self.spike_spawn_timer <= 0:
            self._spawn_spike()
            wave = self._current_wave()
            spike_min = max(60, SPIKE_SPAWN_MIN - wave * 10)
            spike_max = max(100, SPIKE_SPAWN_MAX - wave * 10)
            self.spike_spawn_timer = self._rng.randint(spike_min, spike_max)

    def _current_wave(self) -> int:
        elapsed = GAME_TIMER - self.game_timer
        return 1 + elapsed // 600

    def _spawn_gem(self) -> None:
        color = self._rng.choice(GEM_COLORS)
        if self._rng.random() < 0.4:
            x = self._rng.uniform(ROOM_L + 20, ROOM_R - 20)
            y = self._rng.uniform(ROOM_T + 20, ROOM_B - 20)
        else:
            wall = self._rng.choice(["top", "bottom", "left", "right"])
            if wall == "top":
                x = self._rng.uniform(ROOM_L + 12, ROOM_R - 12)
                y = ROOM_T + 12
            elif wall == "bottom":
                x = self._rng.uniform(ROOM_L + 12, ROOM_R - 12)
                y = ROOM_B - 12
            elif wall == "left":
                x = ROOM_L + 12
                y = self._rng.uniform(ROOM_T + 12, ROOM_B - 12)
            else:
                x = ROOM_R - 12
                y = self._rng.uniform(ROOM_T + 12, ROOM_B - 12)
        self.gems.append(Gem(x, y, color))

    def _spawn_spike(self) -> None:
        wall = self._rng.choice(["top", "bottom", "left", "right"])
        if wall == "top":
            x = self._rng.uniform(ROOM_L + 10, ROOM_R - 10)
            y = ROOM_T
        elif wall == "bottom":
            x = self._rng.uniform(ROOM_L + 10, ROOM_R - 10)
            y = ROOM_B
        elif wall == "left":
            x = ROOM_L
            y = self._rng.uniform(ROOM_T + 10, ROOM_B - 10)
        else:
            x = ROOM_R
            y = self._rng.uniform(ROOM_T + 10, ROOM_B - 10)

        self.spikes.append(Spike(x, y, wall))
        max_spikes = 8 + self._current_wave()
        if len(self.spikes) > max_spikes:
            self.spikes.pop(0)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_float_texts(self) -> None:
        for ft in self.float_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.float_texts = [ft for ft in self.float_texts if ft.life > 0]

    def _spawn_collect_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(8):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 1.5)
            life = self._rng.randint(15, 25)
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    life,
                    color,
                    life,
                )
            )

    def _spawn_damage_particles(self, x: float, y: float) -> None:
        for _ in range(6):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.0)
            life = self._rng.randint(10, 20)
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    life,
                    RED,
                    life,
                )
            )

    # ─── Drawing ─────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 44, 54, "GRAVITY FLUX", WHITE)

        y = 80
        pyxel.text(SCREEN_W // 2 - 62, y, "ARROWS: Flip Gravity", GRAY)
        pyxel.text(SCREEN_W // 2 - 36, y + 10, "UP / DOWN", WHITE)
        pyxel.text(SCREEN_W // 2 - 46, y + 18, "LEFT / RIGHT", WHITE)

        y = 122
        pyxel.text(SCREEN_W // 2 - 70, y, "Collect same-color gems", GRAY)
        pyxel.text(SCREEN_W // 2 - 70, y + 10, "to build COMBO multiplier", GRAY)
        pyxel.text(SCREEN_W // 2 - 70, y + 22, "COMBO x3 = SYNTHESIS: ", CYAN)
        pyxel.text(SCREEN_W // 2 + 70, y + 22, "invincible + 3x score", CYAN)
        pyxel.text(SCREEN_W // 2 - 70, y + 34, "Frequent flips build HEAT", ORANGE)
        pyxel.text(SCREEN_W // 2 - 70, y + 46, "HEAT=100 damages you!", RED)
        pyxel.text(SCREEN_W // 2 - 70, y + 58, "Avoid spikes on walls!", RED)

        pyxel.text(SCREEN_W // 2 - 40, 202, "SPACE to start", WHITE)
        if self.high_score > 0:
            pyxel.text(
                SCREEN_W // 2 - 32, 222, f"HIGH SCORE: {self.high_score}", YELLOW
            )

    def _draw_game(self) -> None:
        self._apply_shake()

        pyxel.rectb(ROOM_L, ROOM_T, ROOM_R - ROOM_L, ROOM_B - ROOM_T, GRAY)

        if self.super_mode:
            flash = (pyxel.frame_count // 15) % 2 == 0
            bc = CYAN if flash else PURPLE
            pyxel.rectb(ROOM_L - 1, ROOM_T - 1, ROOM_R - ROOM_L + 2, ROOM_B - ROOM_T + 2, bc)
            pyxel.rectb(ROOM_L - 2, ROOM_T - 2, ROOM_R - ROOM_L + 4, ROOM_B - ROOM_T + 4, bc)

        for spike in self.spikes:
            self._draw_spike(spike)

        for gem in self.gems:
            self._draw_gem(gem)

        for ft in self.float_texts:
            pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

        for p in self.particles:
            alpha = p.life / p.max_life
            if alpha > 0.5:
                pyxel.pset(int(p.x), int(p.y), p.color)
            elif alpha > 0.2:
                pyxel.pset(int(p.x), int(p.y), DARK_BLUE)

        self._draw_player()
        self._draw_hud()
        pyxel.camera()

    def _apply_shake(self) -> None:
        if self.shake_frames > 0:
            sx = self._rng.randint(-2, 2)
            sy = self._rng.randint(-2, 2)
            try:
                pyxel.camera(sx, sy)
            except BaseException:
                pass

    def _draw_player(self) -> None:
        if self.invuln_timer > 0 and self.invuln_timer % 6 < 3:
            return

        px = int(self.player_x)
        py = int(self.player_y)
        r = int(self.player_radius)

        flash_on = self.super_mode and (pyxel.frame_count // 8) % 2 == 0
        color = CYAN if flash_on else WHITE

        pyxel.tri(px, py - r, px - r, py, px + r, py, color)
        pyxel.tri(px, py + r, px - r, py, px + r, py, color)

    def _draw_gem(self, gem: Gem) -> None:
        gx = int(gem.x)
        gy = int(gem.y)
        pyxel.circ(gx, gy, int(gem.radius + 1), BLACK)
        pyxel.circ(gx, gy, int(gem.radius), gem.color)
        pyxel.circ(gx - 1, gy - 1, 1, WHITE)

    def _draw_spike(self, spike: Spike) -> None:
        x = int(spike.x)
        y = int(spike.y)
        hw = int(spike.width / 2)
        h = int(spike.height)

        if spike.wall == "top":
            pyxel.tri(x - hw, y, x + hw, y, x, y + h, RED)
        elif spike.wall == "bottom":
            pyxel.tri(x - hw, y, x + hw, y, x, y - h, RED)
        elif spike.wall == "left":
            pyxel.tri(x, y - hw, x, y + hw, x + h, y, RED)
        else:
            pyxel.tri(x, y - hw, x, y + hw, x - h, y, RED)

    def _draw_hud(self) -> None:
        for i in range(self.max_hp):
            hx = ROOM_L + i * 10
            hy = 4
            if i < self.hp:
                pyxel.text(hx, hy, "@", RED)
            else:
                pyxel.text(hx, hy, "@", DARK_BLUE)

        bar_x = ROOM_L + 54
        bar_y = 5
        bar_w = 52
        bar_h = 3
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_w = int(bar_w * min(self.heat / self.max_heat, 1.0))
        heat_c = RED if self.heat < 70 else ORANGE
        if fill_w > 0:
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_c)
        pyxel.text(bar_x - 12, 3, "HEAT", ORANGE)

        pyxel.text(SCREEN_W - 80, 2, f"SCORE: {self.score}", WHITE)
        if self.super_mode:
            pyxel.text(SCREEN_W - 80, 11, "SYNTHESIS!", CYAN)
        else:
            cc = self.combo_color if self.combo_color >= 0 else GRAY
            pyxel.text(SCREEN_W - 80, 11, f"x{self.combo}", cc)

        secs = max(0, self.game_timer // 60)
        tc = WHITE if secs > 10 else RED
        pyxel.text(SCREEN_W // 2 - 16, 2, f"{secs}s", tc)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 30, 76, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 44, 104, f"Score: {self.score}", WHITE)
        pyxel.text(
            SCREEN_W // 2 - 44, 116,
            f"Max Combo: x{self.max_combo}", ORANGE,
        )

        if self.score >= self.high_score and self.score > 0:
            pyxel.text(SCREEN_W // 2 - 38, 136, "NEW HIGH SCORE!", YELLOW)
        elif self.high_score > 0:
            pyxel.text(SCREEN_W // 2 - 44, 136, f"High: {self.high_score}", GRAY)

        pyxel.text(SCREEN_W // 2 - 46, 176, "SPACE to retry", WHITE)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
