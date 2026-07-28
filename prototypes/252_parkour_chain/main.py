from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

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
class Obstacle:
    x: float
    color: int
    processed: bool = False


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
    SCREEN_W = 320
    SCREEN_H = 240
    GROUND_Y = 200
    PLAYER_X = 60
    PLAYER_W = 12
    PLAYER_H = 24
    OBSTACLE_W = 16
    OBSTACLE_H = 32
    COLORS = (8, 11, 5, 10)
    COLOR_NAMES = ("RED", "LIME", "DARK_BLUE", "YELLOW")
    GAME_DURATION = 1800
    SUPER_DURATION = 300
    SUPER_COMBO_THRESHOLD = 4
    MAX_HEAT = 100.0
    JUMP_VY = -6.0
    GRAVITY = 0.4
    HEAT_ON_MISMATCH = 15.0
    HEAT_ON_CRASH = 25.0
    HEAT_DECAY = 0.02
    STUN_MISMATCH = 15
    STUN_CRASH = 20
    COLOR_CYCLE_COOLDOWN = 8
    INITIAL_SCROLL_SPEED = 2.0
    INITIAL_SPAWN_INTERVAL = 90
    MIN_SPAWN_INTERVAL = 25
    SPAWN_INTERVAL_DECREASE = 1
    MAX_OBSTACLES = 12

    phase: Phase
    frame: int
    score: int
    combo: int
    max_combo: int
    best_run_score: int
    flow_color_idx: int
    flow_color_cooldown: int
    player_y: float
    player_vy: float
    player_on_ground: bool
    player_ducking: bool
    player_stun: int
    obstacles: list[Obstacle]
    particles: list[Particle]
    floating_texts: list[FloatingText]
    heat: float
    game_timer: int
    super_timer: int
    scroll_speed: float
    spawn_timer: int
    ghost_trail: list[tuple[float, float]]
    ghost_recording: list[tuple[float, float]]
    shake_frames: int
    rng: random.Random
    _title_blink: int

    def __init__(self) -> None:
        self.rng = random.Random()
        self.reset()
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="PARKOUR CHAIN")
        pyxel.run(self._update, self._draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.frame = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.best_run_score = 0
        self.flow_color_idx = 0
        self.flow_color_cooldown = 0
        self.player_y = float(self.GROUND_Y - self.PLAYER_H)
        self.player_vy = 0.0
        self.player_on_ground = True
        self.player_ducking = False
        self.player_stun = 0
        self.obstacles = []
        self.particles = []
        self.floating_texts = []
        self.heat = 0.0
        self.game_timer = self.GAME_DURATION
        self.super_timer = 0
        self.scroll_speed = self.INITIAL_SCROLL_SPEED
        self.spawn_timer = self.INITIAL_SPAWN_INTERVAL
        self.ghost_trail = []
        self.ghost_recording = []
        self.shake_frames = 0
        self._title_blink = 0

    def _update(self) -> None:
        self.frame += 1
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        self._title_blink += 1
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._start_game()

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.frame = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.flow_color_idx = 0
        self.flow_color_cooldown = 0
        self.player_y = float(self.GROUND_Y - self.PLAYER_H)
        self.player_vy = 0.0
        self.player_on_ground = True
        self.player_ducking = False
        self.player_stun = 0
        self.obstacles = []
        self.particles = []
        self.floating_texts = []
        self.heat = 0.0
        self.game_timer = self.GAME_DURATION
        self.super_timer = 0
        self.scroll_speed = self.INITIAL_SCROLL_SPEED
        self.spawn_timer = self.INITIAL_SPAWN_INTERVAL
        self.ghost_trail = []
        self.ghost_recording = []
        self.shake_frames = 0

    def _update_playing(self) -> None:
        if self.player_stun > 0:
            self.player_stun -= 1

        self._update_player()

        if self.player_on_ground:
            self.player_ducking = pyxel.btn(pyxel.KEY_DOWN)

        if self.flow_color_cooldown > 0:
            self.flow_color_cooldown -= 1

        if pyxel.btnp(pyxel.KEY_UP):
            self._cycle_color(1)
        if pyxel.btnp(pyxel.KEY_DOWN) and not self.player_ducking:
            self._cycle_color(-1)

        if pyxel.btnp(pyxel.KEY_SPACE) and self.player_stun == 0:
            if self.player_on_ground and not self.player_ducking:
                self.player_vy = self.JUMP_VY
                self.player_on_ground = False

        self._update_obstacles()
        self._update_particles()
        self._update_floating_texts()

        if self.heat >= self.MAX_HEAT:
            self._end_game(is_victory=False)
            return

        self.game_timer -= 1

        if self.game_timer <= 0:
            self._end_game(is_victory=True)
            return

        if self.super_timer > 0:
            self.super_timer -= 1
        else:
            self.heat = max(0.0, self.heat - self.HEAT_DECAY)

        self.scroll_speed = self.INITIAL_SCROLL_SPEED + (1.0 - self.game_timer / self.GAME_DURATION) * 3.0

        if self.frame % 5 == 0:
            self.ghost_recording.append((float(self.PLAYER_X), self.player_y))

        elapsed = self.GAME_DURATION - self.game_timer
        interval = max(self.MIN_SPAWN_INTERVAL,
                       self.INITIAL_SPAWN_INTERVAL - (elapsed // 60) * self.SPAWN_INTERVAL_DECREASE)

        self.spawn_timer -= 1
        if self.spawn_timer <= 0 and len(self.obstacles) < self.MAX_OBSTACLES:
            self._spawn_obstacle()
            self.spawn_timer = self.rng.randint(interval, interval + 15)

    def _end_game(self, *, is_victory: bool) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_run_score:
            self.best_run_score = self.score
        self._last_victory = is_victory
        self.ghost_trail = list(self.ghost_recording)

    def _update_player(self) -> None:
        if not self.player_on_ground:
            self.player_vy += self.GRAVITY
            self.player_y += self.player_vy
            if self.player_y >= self.GROUND_Y - self.PLAYER_H:
                self.player_y = float(self.GROUND_Y - self.PLAYER_H)
                self.player_vy = 0.0
                self.player_on_ground = True

    def _cycle_color(self, direction: int) -> None:
        if self.flow_color_cooldown > 0:
            return
        self.flow_color_idx = (self.flow_color_idx + direction) % len(self.COLORS)
        self.flow_color_cooldown = self.COLOR_CYCLE_COOLDOWN

    def _spawn_obstacle(self) -> None:
        color = self.rng.choice(self.COLORS)
        self.obstacles.append(
            Obstacle(x=float(self.SCREEN_W + 20), color=color)
        )

    def _update_obstacles(self) -> None:
        player_center = float(self.PLAYER_X + self.PLAYER_W // 2)
        for obs in list(self.obstacles):
            obs.x -= self.scroll_speed
            if obs.x < -self.OBSTACLE_W - 20:
                self.obstacles.remove(obs)
                continue

            if obs.processed:
                continue

            obs_center = obs.x + self.OBSTACLE_W // 2
            if obs_center <= player_center:
                obs.processed = True
                self._process_obstacle(obs)

    def _process_obstacle(self, obs: Obstacle) -> None:
        obs_top = float(self.GROUND_Y - self.OBSTACLE_H)
        player_bottom = self.player_y + self.PLAYER_H

        cleared = player_bottom <= obs_top

        if cleared:
            matched = self.super_timer > 0 or self.flow_color() == obs.color
            self._apply_vault_result(matched)
        else:
            self._apply_crash()

    def flow_color(self) -> int:
        return self.COLORS[self.flow_color_idx]

    def _apply_vault_result(self, matched: bool) -> None:
        if self.super_timer > 0:
            matched = True

        if matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            multiplier = 3 if self.super_timer > 0 else 1
            gained = 10 * self.combo * multiplier
            self.score += gained
            self._spawn_particles(
                float(self.PLAYER_X + self.PLAYER_W // 2),
                self.player_y,
                8, 20, color=self.flow_color(),
            )
            self._spawn_floating_text(
                float(self.PLAYER_X),
                self.player_y - 10,
                f"+{gained}",
                WHITE,
            )
            if self.combo >= 2:
                self._spawn_floating_text(
                    float(self.PLAYER_X),
                    self.player_y - 20,
                    f"COMBO x{self.combo}",
                    YELLOW,
                )
            if self.combo >= self.SUPER_COMBO_THRESHOLD and self.super_timer == 0:
                self._activate_super()
        else:
            self.combo = 0
            self.heat = min(self.MAX_HEAT, self.heat + self.HEAT_ON_MISMATCH)
            self.player_stun = self.STUN_MISMATCH
            self._spawn_particles(
                float(self.PLAYER_X + self.PLAYER_W // 2),
                self.player_y,
                5, 10, color=GRAY,
            )
            self._spawn_floating_text(
                float(self.PLAYER_X),
                self.player_y - 10,
                "MISS!",
                RED,
            )
            self.shake_frames = 6

    def _apply_crash(self) -> None:
        self.combo = 0
        self.heat = min(self.MAX_HEAT, self.heat + self.HEAT_ON_CRASH)
        self.player_stun = self.STUN_CRASH
        self._spawn_particles(
            float(self.PLAYER_X + self.PLAYER_W // 2),
            self.GROUND_Y - 5,
            8, 15, color=RED,
        )
        self._spawn_floating_text(
            float(self.PLAYER_X),
            self.player_y - 10,
            "CRASH!",
            RED,
        )
        self.shake_frames = 10

    def _activate_super(self) -> None:
        self.super_timer = self.SUPER_DURATION
        self._spawn_floating_text(
            float(self.SCREEN_W // 2),
            float(self.SCREEN_H // 2 - 20),
            "SUPER FLOW!",
            YELLOW,
        )
        cx = float(self.PLAYER_X + self.PLAYER_W // 2)
        cy = self.player_y
        for c in self.COLORS:
            self._spawn_particles(cx, cy, 5, 15, color=c)

    def _spawn_particles(self, x: float, y: float, count: int, life: int, color: int = -1) -> None:
        for _ in range(count):
            vx = self.rng.uniform(-2, 2)
            vy = self.rng.uniform(-3, 0)
            c = color if color >= 0 else self.rng.choice(self.COLORS)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=c)
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=30, color=color)
        )

    def _update_particles(self) -> None:
        for p in list(self.particles):
            p.vy += 0.1
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in list(self.floating_texts):
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._start_game()

    def _draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)

        for i in range(3):
            x = (self.frame * 2 + i * 40) % 340 - 20
            pyxel.rect(x, 160, 30, self.rng.randint(40, 80), GRAY)
            pyxel.rect(x + 60, 140, 25, self.rng.randint(30, 70), GRAY)
            pyxel.rect(x + 120, 170, 35, self.rng.randint(50, 90), GRAY)

        pyxel.rect(0, self.GROUND_Y, self.SCREEN_W, self.SCREEN_H - self.GROUND_Y, BROWN)

        title = "PARKOUR CHAIN"
        tw = len(title) * 4
        pyxel.text(self.SCREEN_W // 2 - tw // 2, 60, title, WHITE)

        sub = "Color-Match Parkour"
        sw = len(sub) * 4
        pyxel.text(self.SCREEN_W // 2 - sw // 2, 74, sub, CYAN)

        if self._title_blink % 40 < 25:
            start_text = "Press SPACE to start"
            stw = len(start_text) * 4
            pyxel.text(self.SCREEN_W // 2 - stw // 2, 120, start_text, YELLOW)

        pyxel.text(48, 190, "UP/DOWN: Cycle Color  SPACE: Jump", WHITE)

        if self.best_run_score > 0:
            best_text = f"BEST SCORE: {self.best_run_score}"
            btw = len(best_text) * 4
            pyxel.text(self.SCREEN_W // 2 - btw // 2, 140, best_text, ORANGE)

    def _draw_playing(self) -> None:
        shake_x, shake_y = self._get_shake_offset()
        with _CameraOffset(shake_x, shake_y):
            self._draw_skyscrapers()
            self._draw_ground()

            self._draw_ghost_trail()

            for obs in self.obstacles:
                self._draw_obstacle(obs)

            self._draw_player()

            for p in self.particles:
                alpha = 12 if p.life > 10 else 7
                pyxel.pset(int(p.x), int(p.y), p.color if p.life > 5 else alpha)

            for ft in self.floating_texts:
                if ft.life > 5:
                    pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

        self._draw_hud()

        if self.super_timer > 0:
            self._draw_super_border()

    def _draw_skyscrapers(self) -> None:
        num_buildings = 8
        for i in range(num_buildings):
            bx = (i * 50 - int(self.frame * self.scroll_speed * 0.3)) % (self.SCREEN_W + 60) - 30
            bh = self.rng.randint(30, 80) if i % 3 != 0 else self.rng.randint(60, 100)
            by = self.GROUND_Y - bh
            bw = 30 if i % 2 == 0 else 40
            pyxel.rect(bx, by, bw, bh, GRAY)

    def _draw_ground(self) -> None:
        pyxel.rect(0, self.GROUND_Y, self.SCREEN_W, self.SCREEN_H - self.GROUND_Y, BROWN)
        pyxel.line(0, self.GROUND_Y, self.SCREEN_W, self.GROUND_Y, ORANGE)

    def _draw_ghost_trail(self) -> None:
        if self.best_run_score == 0 and not self.ghost_trail:
            return
        trail = self.ghost_trail if self.ghost_trail else self.ghost_recording
        if len(trail) < 2:
            return
        step = max(1, len(trail) // 30)
        for i in range(0, len(trail), step):
            gx, gy = trail[i]
            pyxel.pset(int(gx), int(gy + self.PLAYER_H // 2), CYAN)

    def _draw_obstacle(self, obs: Obstacle) -> None:
        x = int(obs.x)
        y = self.GROUND_Y - self.OBSTACLE_H
        pyxel.rect(x, y, self.OBSTACLE_W, self.OBSTACLE_H, obs.color)
        pyxel.rectb(x, y, self.OBSTACLE_W, self.OBSTACLE_H, WHITE)

        color_name = self.COLOR_NAMES[self.COLORS.index(obs.color)] if obs.color in self.COLORS else "?"
        label_x = x + self.OBSTACLE_W // 2 - len(color_name) * 2
        pyxel.text(label_x, y - 8, color_name, obs.color)

    def _draw_player(self) -> None:
        px = int(self.PLAYER_X)
        py = int(self.player_y)
        body_y = py + 6
        body_h = 12

        if self.player_stun > 0:
            blink = self.player_stun % 4 < 2
            if not blink:
                return

        current_color = self.flow_color()
        glow_color = YELLOW if self.super_timer > 0 else current_color

        pyxel.rect(px - 1, body_y - 1, self.PLAYER_W + 2, body_h + 12, glow_color)

        pyxel.circ(px + self.PLAYER_W // 2, py + 2, 5, WHITE)

        pyxel.rect(px + 3, body_y, 6, body_h, WHITE)

        leg_top = body_y + body_h
        pyxel.line(px + 4, leg_top, px + 3, py + self.PLAYER_H, WHITE)
        pyxel.line(px + 8, leg_top, px + 9, py + self.PLAYER_H, WHITE)

        color_box_x = px + self.PLAYER_W // 2 - 3
        color_box_y = py - 10
        pyxel.rect(color_box_x, color_box_y, 6, 4, current_color)

    def _draw_hud(self) -> None:
        color_name = self.COLOR_NAMES[self.flow_color_idx]
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        pyxel.text(4, 12, f"COMBO: x{self.combo}", YELLOW if self.combo >= 2 else WHITE)
        pyxel.text(4, 20, f"COLOR: {color_name}", self.flow_color())

        seconds = self.game_timer // 30
        pyxel.text(self.SCREEN_W - 60, 4, f"TIME: {seconds}s", WHITE)

        bar_x = self.SCREEN_W - 104
        bar_y = 16
        bar_w = 100
        bar_h = 6

        heat_color = GREEN
        if self.heat > 50:
            heat_color = YELLOW
        if self.heat > 75:
            heat_color = RED

        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        heat_w = int(self.heat / self.MAX_HEAT * bar_w)
        pyxel.rect(bar_x, bar_y, heat_w, bar_h, heat_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)

        if self.super_timer > 0:
            super_text = f"SUPER {self.super_timer // 30}s"
            pyxel.text(bar_x, bar_y + 10, super_text, YELLOW)

    def _draw_super_border(self) -> None:
        rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
        t = self.frame // 4
        for i in range(6):
            c = rainbow[(t + i) % len(rainbow)]
            pyxel.rect(0, i * 2, self.SCREEN_W, 2, c)
            pyxel.rect(0, self.SCREEN_H - 2 - i * 2, self.SCREEN_W, 2, c)
            pyxel.rect(i * 2, 0, 2, self.SCREEN_H, c)
            pyxel.rect(self.SCREEN_W - 2 - i * 2, 0, 2, self.SCREEN_H, c)

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)

        is_victory = getattr(self, "_last_victory", False)

        if is_victory:
            title = "TIME'S UP!"
            tc = LIME
        else:
            title = "GAME OVER"
            tc = RED

        tw = len(title) * 4
        pyxel.text(self.SCREEN_W // 2 - tw // 2, 40, title, tc)

        pyxel.text(self.SCREEN_W // 2 - 25, 80, f"SCORE: {self.score}", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 25, 92, f"MAX COMBO: x{self.max_combo}", YELLOW)
        pyxel.text(self.SCREEN_W // 2 - 25, 104, f"BEST: {self.best_run_score}", ORANGE)

        if self.score >= self.best_run_score and self.score > 0:
            new_text = "NEW BEST!"
            ntw = len(new_text) * 4
            pyxel.text(self.SCREEN_W // 2 - ntw // 2, 122, new_text, YELLOW)

        start_text = "Press SPACE to retry"
        stw = len(start_text) * 4
        if self.frame % 40 < 25:
            pyxel.text(self.SCREEN_W // 2 - stw // 2, 160, start_text, WHITE)

        controls = "UP/DOWN: Cycle Color  SPACE: Jump"
        ctw = len(controls) * 4
        pyxel.text(self.SCREEN_W // 2 - ctw // 2, 200, controls, WHITE)

    def _get_shake_offset(self) -> tuple[int, int]:
        if self.shake_frames <= 0:
            return 0, 0
        self.shake_frames -= 1
        sx = self.rng.randint(-2, 2)
        sy = self.rng.randint(-2, 2)
        return sx, sy


class _CameraOffset:
    def __init__(self, x: int, y: int) -> None:
        self._x = x
        self._y = y

    def __enter__(self) -> None:
        pyxel.camera(self._x, self._y)

    def __exit__(self, *args: object) -> None:
        pyxel.camera(0, 0)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
