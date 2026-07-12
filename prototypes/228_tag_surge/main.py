import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240
FPS = 30
PLAYER_RADIUS = 8
RUNNER_RADIUS = 7
TAG_RADIUS = PLAYER_RADIUS + RUNNER_RADIUS + 2
PLAYER_SPEED = 2.5
RUNNER_BASE_SPEED = 1.2
RUNNER_MAX_SPEED = 3.5
MAX_RUNNERS = 10
INITIAL_RUNNERS = 5
COLORS: list[int] = [8, 11, 5, 10]
COLOR_NAMES: dict[int, str] = {8: "RED", 11: "LIME", 5: "BLUE", 10: "YEL"}
GAME_TIME = 60 * FPS
SUPER_DURATION = 300
STUN_DURATION = 15
COMBO_THRESHOLD = 4
HEAT_MAX = 100
HEAT_DECAY = 0.02
HEAT_MISMATCH = 15
COLOR_CYCLE_INTERVAL = 90
SUPER_SCORE_MULT = 3

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


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Runner:
    x: float
    y: float
    color: int
    vx: float = 0.0
    vy: float = 0.0
    speed: float = 1.2


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.5


class Game:

    phase: Phase
    score: int
    combo: int
    max_combo: int
    heat: float
    player_x: float
    player_y: float
    player_color: int
    color_idx: int
    color_timer: int
    stun_timer: int
    super_timer: int
    game_timer: int
    shake_frames: int
    frame: int
    runners: list[Runner]
    particles: list[Particle]
    floating_texts: list[FloatingText]
    rng: random.Random
    difficulty_level: int
    max_runners_now: int

    def __init__(self) -> None:
        self.rng = random.Random()
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.player_x = SCREEN_W / 2
        self.player_y = SCREEN_H / 2
        self.color_idx = 0
        self.player_color = COLORS[self.color_idx]
        self.color_timer = COLOR_CYCLE_INTERVAL
        self.stun_timer = 0
        self.super_timer = 0
        self.game_timer = GAME_TIME
        self.shake_frames = 0
        self.frame = 0
        self.runners = []
        self.particles = []
        self.floating_texts = []
        self.difficulty_level = 0
        self.max_runners_now = INITIAL_RUNNERS

    def reset_playing(self) -> None:
        self.reset()
        self.phase = Phase.PLAYING
        for _ in range(INITIAL_RUNNERS):
            self._spawn_runner()

    def _cycle_color(self) -> None:
        self.color_timer -= 1
        if self.color_timer <= 0:
            interval = int(COLOR_CYCLE_INTERVAL - self.difficulty_level * 3)
            interval = max(60, interval)
            self.color_timer = interval
            self.color_idx = (self.color_idx + 1) % len(COLORS)
            self.player_color = COLORS[self.color_idx]

    def _spawn_runner(self) -> None:
        if len(self.runners) >= self.max_runners_now:
            return
        side = self.rng.randint(0, 3)
        margin = RUNNER_RADIUS + 5
        if side == 0:
            x = self.rng.uniform(margin, SCREEN_W - margin)
            y = margin
        elif side == 1:
            x = self.rng.uniform(margin, SCREEN_W - margin)
            y = SCREEN_H - margin
        elif side == 2:
            x = margin
            y = self.rng.uniform(margin, SCREEN_H - margin)
        else:
            x = SCREEN_W - margin
            y = self.rng.uniform(margin, SCREEN_H - margin)

        dx = self.player_x - x
        dy = self.player_y - y
        dist = math.hypot(dx, dy)
        if dist < 40:
            offset_x = (dx / max(dist, 0.01)) * 40
            offset_y = (dy / max(dist, 0.01)) * 40
            x = self.player_x - offset_x
            y = self.player_y - offset_y
            x = max(margin, min(SCREEN_W - margin, x))
            y = max(margin, min(SCREEN_H - margin, y))

        speed = RUNNER_BASE_SPEED + self.difficulty_level * 0.15
        speed = min(speed, RUNNER_MAX_SPEED)
        color = self.rng.choice(COLORS)
        self.runners.append(Runner(x, y, color, 0.0, 0.0, speed))

    def _update_runners(self) -> None:
        for runner in self.runners:
            dx = runner.x - self.player_x
            dy = runner.y - self.player_y
            dist = max(math.hypot(dx, dy), 0.001)
            nx = dx / dist
            ny = dy / dist
            runner.vx += nx * 0.1
            runner.vy += ny * 0.1
            speed = math.hypot(runner.vx, runner.vy)
            if speed > runner.speed:
                scale = runner.speed / speed
                runner.vx *= scale
                runner.vy *= scale
            runner.x += runner.vx
            runner.y += runner.vy
            runner.vx *= 0.95
            runner.vy *= 0.95
            runner.x = max(RUNNER_RADIUS, min(SCREEN_W - RUNNER_RADIUS, runner.x))
            runner.y = max(RUNNER_RADIUS, min(SCREEN_H - RUNNER_RADIUS, runner.y))

    def _update_player(self) -> None:
        if self.stun_timer > 0:
            self.stun_timer -= 1
            return
        dx = 0.0
        dy = 0.0
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy -= 1.0
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy += 1.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx -= 1.0
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx += 1.0
        if dx != 0.0 and dy != 0.0:
            inv = 1.0 / math.sqrt(2.0)
            dx *= inv
            dy *= inv
        self.player_x += dx * PLAYER_SPEED
        self.player_y += dy * PLAYER_SPEED
        self.player_x = max(PLAYER_RADIUS, min(SCREEN_W - PLAYER_RADIUS, self.player_x))
        self.player_y = max(PLAYER_RADIUS, min(SCREEN_H - PLAYER_RADIUS, self.player_y))

    def _check_tags(self) -> None:
        tag_radius_sq = TAG_RADIUS * TAG_RADIUS
        for i, runner in enumerate(self.runners[:]):
            dx = self.player_x - runner.x
            dy = self.player_y - runner.y
            if dx * dx + dy * dy < tag_radius_sq:
                self._handle_tag(i)

    def _handle_tag(self, runner_index: int) -> None:
        runner = self.runners[runner_index]
        if self.super_timer > 0:
            is_match = True
        else:
            is_match = runner.color == self.player_color

        if is_match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            multiplier = 1.0 + self.combo * 0.5
            super_mult = SUPER_SCORE_MULT if self.super_timer > 0 else 1
            gain = int(10 * multiplier * super_mult)
            self.score += gain
            if self.super_timer > 0:
                self._add_floating_text(runner.x, runner.y - 10, f"+{gain}", WHITE)
                self._spawn_particles(runner.x, runner.y, runner.color, 20)
            else:
                self._add_floating_text(runner.x, runner.y - 10, f"+{gain}", runner.color)
                self._spawn_particles(runner.x, runner.y, runner.color, 12)
            self.shake_frames = 5
            if self.combo >= COMBO_THRESHOLD and self.super_timer == 0:
                self._trigger_super()
            self.runners.pop(runner_index)
            if self.super_timer > 0:
                self._auto_tag_nearby()
        else:
            self.combo = 0
            self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
            self.stun_timer = STUN_DURATION
            self.shake_frames = 8
            self._spawn_particles(runner.x, runner.y, GRAY, 5)
            self._add_floating_text(runner.x, runner.y - 10, "MISS!", RED)

    def _trigger_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self._spawn_particles(self.player_x, self.player_y, WHITE, 25)
        self._add_floating_text(
            self.player_x, self.player_y - 20, "SUPER TAG!", WHITE
        )

    def _auto_tag_nearby(self) -> None:
        auto_radius_sq = (TAG_RADIUS + 20) * (TAG_RADIUS + 20)
        to_remove: list[int] = []
        for i, runner in enumerate(self.runners):
            dx = self.player_x - runner.x
            dy = self.player_y - runner.y
            if dx * dx + dy * dy < auto_radius_sq:
                multiplier = 1.0 + self.combo * 0.5
                gain = int(10 * multiplier * SUPER_SCORE_MULT)
                self.score += gain
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                self._spawn_particles(runner.x, runner.y, runner.color, 15)
                self._add_floating_text(runner.x, runner.y - 10, f"+{gain}", runner.color)
                to_remove.append(i)
        for i in reversed(to_remove):
            self.runners.pop(i)

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self.combo = 0

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self.heat = HEAT_MAX
            self.phase = Phase.GAME_OVER
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_difficulty(self) -> None:
        new_level = (GAME_TIME - self.game_timer) // (10 * FPS)
        if new_level > self.difficulty_level:
            self.difficulty_level = new_level
            self.max_runners_now = min(MAX_RUNNERS, INITIAL_RUNNERS + self.difficulty_level)
            for _ in range(min(3, self.max_runners_now - len(self.runners))):
                self._spawn_runner()

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            p.size = max(1, p.size - 1)
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(0.5, 2.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self.rng.randint(10, 20)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, 30, color))

    def _update_playing(self) -> None:
        self.frame += 1
        self.game_timer -= 1

        self._update_player()
        self._update_runners()
        self._check_tags()
        self._cycle_color()
        self._update_super()
        self._update_heat()
        self._update_difficulty()
        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

        elite_elapsed = GAME_TIME - self.game_timer
        if elite_elapsed > 0 and elite_elapsed % (5 * FPS) == 0 and len(self.runners) < self.max_runners_now:
            self._spawn_runner()

        if self.game_timer <= 0:
            self.phase = Phase.GAME_OVER

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset_playing()
            self.frame += 1
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset_playing()
            self.frame += 1
            return

        if self.phase == Phase.PLAYING:
            self._update_playing()

    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self.shake_frames > 0:
            ox = self.rng.randint(-4, 4)
            oy = self.rng.randint(-4, 4)
        else:
            ox, oy = 0, 0

        try:
            pyxel.camera(ox, oy)
        except BaseException:
            pass

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        try:
            pyxel.camera(0, 0)
        except BaseException:
            pass

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 36, 40, "TAG SURGE", WHITE)
        pyxel.text(SCREEN_W // 2 - 56, 60, "CHASE & TAG THE RUNNERS!", GRAY)
        pyxel.text(SCREEN_W // 2 - 64, 90, "Arrow Keys: Move (IT)", GRAY)
        pyxel.text(SCREEN_W // 2 - 64, 100, "Tag same-color runners!", GRAY)
        pyxel.text(SCREEN_W // 2 - 64, 110, "COMBO>=4 = SUPER TAG", GRAY)
        pyxel.text(SCREEN_W // 2 - 64, 120, "Avoid mismatch = HEAT", GRAY)

        pyxel.text(SCREEN_W // 2 - 40, 150, "COLOR CYCLING:", WHITE)
        for i, c in enumerate(COLORS):
            cx = SCREEN_W // 2 - 28 + i * 16
            pyxel.circ(cx, 165, 5, c)

        pyxel.text(SCREEN_W // 2 - 52, 190, f"SCORE: {self.score}", GRAY)
        if (self.frame // 15) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - 52, 220, "PRESS ENTER TO START", WHITE)

    def _draw_playing(self) -> None:
        self._draw_runners()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()
        self._draw_super_indicator()

    def _draw_runners(self) -> None:
        for runner in self.runners:
            pyxel.circ(int(runner.x), int(runner.y), RUNNER_RADIUS, runner.color)
            pyxel.circb(int(runner.x), int(runner.y), RUNNER_RADIUS, WHITE)

    def _draw_player(self) -> None:
        if self.stun_timer > 0 and (self.frame // 3) % 2 == 0:
            return
        color = self._get_player_draw_color()
        pyxel.circ(int(self.player_x), int(self.player_y), PLAYER_RADIUS, color)
        pyxel.circb(int(self.player_x), int(self.player_y), PLAYER_RADIUS, WHITE)
        if self.super_timer > 0:
            pulse = 4 + (self.frame % 8) // 2
            pyxel.circb(int(self.player_x), int(self.player_y), PLAYER_RADIUS + pulse, WHITE)
            pyxel.circb(int(self.player_x), int(self.player_y), PLAYER_RADIUS + pulse + 2, YELLOW)

    def _get_player_draw_color(self) -> int:
        if self.super_timer > 0:
            idx = (self.frame // 5) % len(COLORS)
            return COLORS[idx]
        return self.player_color

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 20.0
            color = p.color
            if alpha < 0.3:
                if color > 0:
                    color = max(0, color - 1)
            pyxel.pset(int(p.x), int(p.y), color)
            if p.size > 1:
                pyxel.pset(int(p.x) + 1, int(p.y), color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            color = ft.color
            if alpha < 0.3:
                color = GRAY
            pyxel.text(int(ft.x) - 16, int(ft.y), ft.text, color)

    def _draw_hud(self) -> None:
        time_sec = max(0, self.game_timer // FPS)
        time_color = RED if time_sec < 15 else WHITE

        pyxel.text(8, 8, f"TIME: {time_sec}", time_color)
        pyxel.text(8, 18, f"SCORE: {self.score}", WHITE)

        combo_color = WHITE if self.combo >= COMBO_THRESHOLD else YELLOW
        pyxel.text(8, 28, f"COMBO: x{self.combo}", combo_color)

        bar_w = 80
        bar_h = 6
        bar_x = SCREEN_W - bar_w - 8
        bar_y = 8
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_w = int(bar_w * self.heat / HEAT_MAX)
        heat_color = RED
        if self.heat >= 80:
            if (self.frame % 4) < 2:
                heat_color = RED
            else:
                heat_color = WHITE
        elif self.heat >= 60:
            heat_color = ORANGE
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.text(SCREEN_W - bar_w - 8, bar_y + bar_h + 2, "HEAT", GRAY)

        color_name = COLOR_NAMES.get(self.player_color, "???")
        pyxel.text(SCREEN_W - 50, 28, color_name, self.player_color)

    def _draw_super_indicator(self) -> None:
        if self.super_timer > 0:
            idx = (self.frame // 4) % len(COLORS)
            color = COLORS[idx]
            remaining = self.super_timer // FPS
            pyxel.text(SCREEN_W // 2 - 40, 50, f"SUPER TAG! {remaining}s", color)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 28, 40, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 48, 80, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 48, 100, f"MAX COMBO: x{self.max_combo}", YELLOW)
        reason = "TIME" if self.game_timer <= 0 else "HEAT"
        pyxel.text(SCREEN_W // 2 - 32, 120, f"CAUSE: {reason}", GRAY)
        if self.game_timer > 0:
            pyxel.text(SCREEN_W // 2 - 40, 140, f"HEAT: {self.heat:.0f}%", ORANGE)
        if (self.frame // 15) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - 52, 200, "PRESS R TO RESTART", WHITE)


def main() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="Tag Surge")
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
