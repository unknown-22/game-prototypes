"""Parkour Chain — A side-scrolling parkour game with echo trail combos."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Platform:
    x: float
    y: float
    w: int
    color: int
    landed: bool = False


@dataclass
class TrailPoint:
    x: float
    y: float
    color: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    gravity: float = 0.15


RED = pyxel.COLOR_RED
GREEN = pyxel.COLOR_GREEN
DARK_BLUE = pyxel.COLOR_DARK_BLUE
YELLOW = pyxel.COLOR_YELLOW
PLATFORM_COLORS = [RED, GREEN, DARK_BLUE, YELLOW]
WHITE = pyxel.COLOR_WHITE
GRAY = pyxel.COLOR_GRAY
BLACK = pyxel.COLOR_BLACK
ORANGE = pyxel.COLOR_ORANGE
CYAN = pyxel.COLOR_CYAN
PINK = pyxel.COLOR_PINK
PURPLE = pyxel.COLOR_PURPLE
LIGHT_BLUE = pyxel.COLOR_LIGHT_BLUE
NAVY = pyxel.COLOR_NAVY


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    PLAYER_X = 80
    PLAYER_W = 12
    PLAYER_H = 16
    GRAVITY = 0.5
    JUMP_VEL = -8.0
    RUN_SPEED = 3.0
    MAX_STAMINA = 100
    JUMP_COST = 10
    STAMINA_REGEN = 0.5
    PLATFORM_MIN_W = 48
    PLATFORM_MAX_W = 80
    PLATFORM_H = 8
    GAP_MIN = 30
    GAP_MAX = 100
    TRAIL_MAX = 40
    COMBO_FOR_SUPER = 4
    SUPER_DURATION = 300
    SUPER_MULTIPLIER = 3
    ECHO_MULTIPLIER = 2
    PLATFORM_Y_MIN = 40
    PLATFORM_Y_MAX = 200
    JUMP_COOLDOWN = 5

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="Parkour Chain")
        self.phase: Phase = Phase.TITLE
        self.player_y: float = 180.0
        self.player_vy: float = 0.0
        self.player_on_ground: bool = False
        self.player_landed_color: int = -1
        self.combo: int = 0
        self.max_combo: int = 0
        self.stamina: float = self.MAX_STAMINA
        self.score: int = 0
        self.distance: float = 0.0
        self.platforms: list[Platform] = []
        self.trail: list[TrailPoint] = []
        self.particles: list[Particle] = []
        self.super_timer: int = 0
        self.super_particles_timer: int = 0
        self.camera_x: float = 0.0
        self.frame: int = 0
        self.shake_frames: int = 0
        self.shake_intensity: int = 0
        self.next_color: int = RED
        self.last_jump_frame: int = -self.JUMP_COOLDOWN
        self.game_over_flash: int = 0
        self._buildings: list[tuple[float, float, float]] = []
        self._bg_buildings: list[tuple[float, float, float]] = []
        self._generate_buildings()
        pyxel.run(self.update, self.draw)

    def _generate_buildings(self) -> None:
        random.seed(42)
        for i in range(20):
            x = i * 160 + random.uniform(0, 60)
            w = random.uniform(20, 80)
            h = random.uniform(30, 120)
            self._buildings.append((x, w, h))
        for i in range(15):
            x = i * 200 + random.uniform(0, 80)
            w = random.uniform(15, 60)
            h = random.uniform(20, 80)
            self._bg_buildings.append((x, w, h))

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.player_y = 180.0
        self.player_vy = 0.0
        self.player_on_ground = True
        self.player_landed_color = -1
        self.combo = 0
        self.max_combo = 0
        self.stamina = self.MAX_STAMINA
        self.score = 0
        self.distance = 0.0
        self.platforms.clear()
        self.trail.clear()
        self.particles.clear()
        self.super_timer = 0
        self.super_particles_timer = 0
        self.camera_x = 0.0
        self.frame = 0
        self.shake_frames = 0
        self.shake_intensity = 0
        self.next_color = random.choice(PLATFORM_COLORS)
        self.last_jump_frame = -self.JUMP_COOLDOWN
        self.game_over_flash = 0
        first_plat = Platform(
            self.PLAYER_X - 20, 188.0, 80, random.choice(PLATFORM_COLORS)
        )
        self.platforms.append(first_plat)
        self._ensure_min_platforms()

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return
        if self.phase == Phase.GAME_OVER:
            self.game_over_flash += 1
            if self.game_over_flash > 30 and (
                pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN)
            ):
                self.reset()
            return

        self.frame += 1

        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_UP):
            self._jump()

        self._update_player()
        self._update_platforms()
        self._check_landings()
        self._update_trail()
        self._update_super()
        self._update_particles()
        self._update_stamina()

        self.camera_x += self.RUN_SPEED
        self.distance = self.camera_x

        if self.super_timer > 0:
            self.score += self.SUPER_MULTIPLIER
        else:
            self.score += 1

        if self.player_y > self.SCREEN_H + 20:
            self._game_over()

        if self.shake_frames > 0:
            self.shake_frames -= 1

    def _update_player(self) -> None:
        if self.super_timer > 0 and not self.player_on_ground:
            self.player_vy = 0
        else:
            self.player_vy += self.GRAVITY
            self.player_y += self.player_vy

    def _jump(self) -> None:
        if self.frame - self.last_jump_frame < self.JUMP_COOLDOWN:
            return
        if self.stamina < self.JUMP_COST:
            return
        if not self.player_on_ground and self.super_timer <= 0:
            return

        self.player_vy = self.JUMP_VEL
        self.player_on_ground = False
        self.stamina -= self.JUMP_COST
        self.last_jump_frame = self.frame

    def _update_stamina(self) -> None:
        if self.player_on_ground:
            self.stamina = min(self.stamina + self.STAMINA_REGEN, self.MAX_STAMINA)

    def _update_platforms(self) -> None:
        left_edge = self.camera_x - 100
        self.platforms = [p for p in self.platforms if p.x + p.w > left_edge]
        self._ensure_min_platforms()

    def _ensure_min_platforms(self) -> None:
        right_target = self.camera_x + self.SCREEN_W + self.GAP_MAX
        while len(self.platforms) < 2 or max(p.x + p.w for p in self.platforms) < right_target:
            if self.platforms:
                last_p = max(self.platforms, key=lambda p: p.x)
                start_x = last_p.x + last_p.w + random.uniform(self.GAP_MIN, self.GAP_MAX)
            else:
                start_x = self.camera_x + self.SCREEN_W + random.uniform(self.GAP_MIN, self.GAP_MAX)
            self.platforms.append(self._spawn_platform(start_x))

    def _spawn_platform(self, start_x: float) -> Platform:
        y = random.uniform(self.PLATFORM_Y_MIN, self.PLATFORM_Y_MAX)
        w = random.randint(self.PLATFORM_MIN_W, self.PLATFORM_MAX_W)
        color = self.next_color
        self.next_color = random.choice(PLATFORM_COLORS)
        return Platform(start_x, y, w, color)

    def _check_landings(self) -> None:
        if self.player_vy < 0:
            return

        world_x = self.camera_x + self.PLAYER_X
        player_bottom = self.player_y + self.PLAYER_H
        player_left = world_x
        player_right = world_x + self.PLAYER_W

        for plat in self.platforms:
            if plat.landed:
                continue
            if player_right <= plat.x or player_left >= plat.x + plat.w:
                continue
            if player_bottom >= plat.y and player_bottom <= plat.y + self.PLATFORM_H + 6:
                self.player_y = plat.y - self.PLAYER_H
                self.player_vy = 0
                self.player_on_ground = True
                if not plat.landed:
                    plat.landed = True
                    self._on_platform_landed(plat)
                break

    def _on_platform_landed(self, plat: Platform) -> None:
        world_x = self.camera_x + self.PLAYER_X

        if self.super_timer > 0:
            self.combo += 1
        elif plat.color == self.player_landed_color:
            self.combo += 1
        else:
            self.combo = 1
        self.player_landed_color = plat.color

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        landing_score = 10 * self.combo

        echo_triggered = self._check_echo(plat)
        if echo_triggered:
            landing_score *= self.ECHO_MULTIPLIER
            self._spawn_echo_particles(world_x, plat.y)

        if self.super_timer > 0:
            landing_score *= self.SUPER_MULTIPLIER

        self.score += int(landing_score)

        particle_color = self._rainbow_color() if self.super_timer > 0 else plat.color
        count = min(self.combo * 2, 12)
        if count < 2:
            count = 2
        self._spawn_landing_particles(world_x, plat.y, particle_color, count)

        if self.combo >= self.COMBO_FOR_SUPER and self.super_timer == 0:
            self.super_timer = self.SUPER_DURATION
            self.super_particles_timer = 0

    def _check_echo(self, plat: Platform) -> bool:
        world_x = self.camera_x + self.PLAYER_X
        for tp in self.trail:
            if tp.color == plat.color:
                if abs(tp.x - world_x) < 25 and abs(tp.y - self.player_y) < 25:
                    return True
        return False

    def _update_trail(self) -> None:
        if self.player_on_ground:
            world_x = self.camera_x + self.PLAYER_X
            color = self.player_landed_color if self.player_landed_color >= 0 else WHITE
            self.trail.append(TrailPoint(world_x, self.player_y, color))
            if len(self.trail) > self.TRAIL_MAX:
                self.trail = self.trail[-self.TRAIL_MAX:]

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            self.super_particles_timer += 1
            if self.super_particles_timer >= 10:
                self.super_particles_timer = 0
                self._spawn_super_particles()
            if self.super_timer == 0:
                self.combo = 0
                self.player_landed_color = -1
                if not self.player_on_ground:
                    self.player_vy = self.GRAVITY

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += p.gravity
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _spawn_landing_particles(
        self, x: float, y: float, color: int, count: int
    ) -> None:
        for _ in range(count):
            vx = random.uniform(-2, 2)
            vy = random.uniform(-6, -2)
            life = random.randint(15, 25)
            self.particles.append(Particle(x, y, vx, vy, life, color, gravity=0.15))

    def _spawn_echo_particles(self, x: float, y: float) -> None:
        for _ in range(8):
            vx = random.uniform(-3, 3)
            vy = random.uniform(-8, -3)
            life = random.randint(20, 30)
            self.particles.append(Particle(x, y, vx, vy, life, PINK, gravity=0.1))

    def _spawn_super_particles(self) -> None:
        world_x = self.camera_x + self.PLAYER_X
        for _ in range(2):
            vx = random.uniform(-1, 1)
            vy = random.uniform(-3, -1)
            life = random.randint(10, 20)
            color = self._rainbow_color()
            self.particles.append(
                Particle(
                    world_x + random.uniform(-10, 10),
                    self.player_y + random.uniform(-5, 10),
                    vx,
                    vy,
                    life,
                    color,
                    gravity=-0.05,
                )
            )

    def _rainbow_color(self) -> int:
        return PLATFORM_COLORS[(self.frame // 5) % len(PLATFORM_COLORS)]

    def _game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        self.game_over_flash = 0
        world_x = self.camera_x + self.PLAYER_X
        for _ in range(15):
            vx = random.uniform(-4, 4)
            vy = random.uniform(-10, -4)
            life = random.randint(20, 40)
            self.particles.append(
                Particle(world_x, self.player_y, vx, vy, life, WHITE, gravity=0.2)
            )
        self.shake_frames = 15
        self.shake_intensity = 4

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over()
        if self.phase in (Phase.PLAYING, Phase.GAME_OVER):
            self._draw_particles()

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)
        pyxel.text(110, 60, "PARKOUR CHAIN", WHITE)
        pyxel.text(90, 100, "SPACE to start", LIGHT_BLUE)
        pyxel.text(70, 130, "JUMP: SPACE / UP / RETURN", GRAY)
        pyxel.text(60, 150, "Chain same-color platforms!", GRAY)
        pyxel.text(45, 165, "COMBO x4 = SUPER FLOW (3x)", GRAY)
        pyxel.text(70, 185, "Cross trail for ECHO BONUS", PINK)
        for bx, bw, bh in self._bg_buildings[:6]:
            sx = bx % self.SCREEN_W
            pyxel.rect(sx, self.SCREEN_H - bh, bw, bh, GRAY)

    def _draw_game(self) -> None:
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = random.randint(-self.shake_intensity, self.shake_intensity)
            shake_y = random.randint(-self.shake_intensity, self.shake_intensity)

        pyxel.cls(DARK_BLUE)

        for bx, bw, bh in self._bg_buildings:
            sx = (bx - self.camera_x * 0.3) % (self.SCREEN_W + 200) - 100
            if -100 < sx < self.SCREEN_W + 100:
                pyxel.rect(sx + shake_x, self.SCREEN_H - bh, bw, bh, GRAY)

        for bx, bw, bh in self._buildings:
            sx = (bx - self.camera_x * 0.6) % (self.SCREEN_W + 160) - 80
            if -100 < sx < self.SCREEN_W + 100:
                pyxel.rect(sx + shake_x, self.SCREEN_H - bh, bw, bh, GRAY)

        for plat in self.platforms:
            sx = plat.x - self.camera_x
            if -plat.w < sx < self.SCREEN_W:
                color = self._rainbow_color() if self.super_timer > 0 else plat.color
                pyxel.rect(sx + shake_x, plat.y + shake_y, plat.w, self.PLATFORM_H, color)
                border = max(color - 1, 1)
                pyxel.rectb(
                    sx + shake_x, plat.y + shake_y, plat.w, self.PLATFORM_H, border
                )

        for i, tp in enumerate(self.trail):
            sx = tp.x - self.camera_x
            if 0 < sx < self.SCREEN_W and 0 < tp.y < self.SCREEN_H:
                alpha_color = PINK if i > len(self.trail) // 3 else LIGHT_BLUE
                pyxel.rect(sx + shake_x - 1, tp.y + shake_y - 1, 3, 3, alpha_color)

        player_color = self._rainbow_color() if self.super_timer > 0 else WHITE
        px = self.PLAYER_X + shake_x
        py = self.player_y + shake_y
        pyxel.rect(px, py, self.PLAYER_W, self.PLAYER_H, player_color)
        pyxel.rectb(px, py, self.PLAYER_W, self.PLAYER_H, BLACK)

        if self.next_color:
            pyxel.rect(
                self.PLAYER_X + self.PLAYER_W + 5,
                self.player_y - 5,
                8,
                8,
                self.next_color,
            )

        self._draw_hud()

    def _draw_hud(self) -> None:
        stamina_w = 80
        bar_x = 6
        bar_y = 6
        pyxel.rectb(bar_x - 1, bar_y - 1, stamina_w + 2, 8, GRAY)
        stamina_fill = int(self.stamina / self.MAX_STAMINA * stamina_w)
        pyxel.rect(bar_x, bar_y, stamina_fill, 6, ORANGE)
        pyxel.text(bar_x, bar_y + 10, "STAMINA", GRAY)

        if self.combo > 1:
            combo_text = f"COMBO x{self.combo}"
            cx = self.SCREEN_W // 2 - len(combo_text) * 2
            combo_color = (
                self._rainbow_color() if self.combo >= self.COMBO_FOR_SUPER else PURPLE
            )
            pyxel.text(cx, 8, combo_text, combo_color)

        if self.super_timer > 0:
            super_w = 60
            sx = self.SCREEN_W // 2 - super_w // 2
            sy = 20
            pyxel.rectb(sx - 1, sy - 1, super_w + 2, 6, GRAY)
            super_fill = int(self.super_timer / self.SUPER_DURATION * super_w)
            pyxel.rect(sx, sy, super_fill, 4, CYAN)
            pyxel.text(sx, sy + 6, "SUPER FLOW", self._rainbow_color())

        score_text = f"SCORE: {self.score}"
        pyxel.text(self.SCREEN_W - len(score_text) * 4 - 4, 8, score_text, WHITE)

        dist_text = f"DIST: {int(self.distance)}m"
        pyxel.text(self.SCREEN_W - len(dist_text) * 4 - 4, 18, dist_text, GRAY)

    def _draw_particles(self) -> None:
        for p in self.particles:
            sx = p.x - self.camera_x
            if 0 <= sx <= self.SCREEN_W and 0 <= p.y <= self.SCREEN_H:
                size = max(1, p.life // 8)
                pyxel.rect(sx, p.y, size, size, p.color)

    def _draw_game_over(self) -> None:
        for y in range(0, self.SCREEN_H, 4):
            for x in range(0, self.SCREEN_W, 6):
                if (x + y) % 12 == 0:
                    c = BLACK if self.game_over_flash % 20 < 10 else NAVY
                    pyxel.rect(x, y, 6, 4, c)

        if self.game_over_flash > 15:
            pyxel.text(115, 70, "GAME OVER", WHITE)
            pyxel.text(100, 100, f"SCORE: {self.score}", WHITE)
            pyxel.text(80, 120, f"MAX COMBO: x{self.max_combo}", PURPLE)
            pyxel.text(80, 140, f"DISTANCE: {int(self.distance)}m", GRAY)
            if self.game_over_flash > 40:
                pyxel.text(95, 170, "SPACE to retry", LIGHT_BLUE)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
