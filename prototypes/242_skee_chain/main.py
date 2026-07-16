"""Skee Chain - Color-match skee-ball COMBO chain game."""
import enum
import math
import random
from dataclasses import dataclass

import pyxel


class Phase(enum.Enum):
    TITLE = enum.auto()
    AIMING = enum.auto()
    FLYING = enum.auto()
    SCORING = enum.auto()
    GAME_OVER = enum.auto()


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


@dataclass
class Hole:
    x: int
    y: int
    color: int
    radius: int
    score: int


@dataclass
class GhostPoint:
    x: float
    y: float


class Game:
    SCREEN_W = 320
    SCREEN_H = 240

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

    COLORS = (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW
    COLOR_NAMES = ("RED", "LIME", "DARK_BLUE", "YELLOW")
    NUM_COLORS = 4
    SUPER_DURATION = 300
    SUPER_COMBO_THRESHOLD = 4
    SUPER_MULTIPLIER = 3
    MAX_HEAT = 100.0
    HEAT_MISMATCH = 15
    HEAT_MISS = 10
    HEAT_DECAY = 0.02
    TIMER_START = 60 * 30
    HOLE_RADIUS = 12
    BALL_RADIUS = 5
    GRAVITY = 0.25
    MAX_POWER = 12.0
    POWER_CHARGE_RATE = 0.3
    FRICTION = 0.98
    COLOR_CYCLE_COOLDOWN = 10

    LAUNCH_X = 50
    LAUNCH_Y = 190
    SCORING_DURATION = 15
    SUPER_PARTICLE_COUNT = 15
    HIT_PARTICLE_COUNT = 8
    MISS_PARTICLE_COUNT = 4
    GHOST_TRAIL_COLOR = 12  # CYAN

    RAMP_POINTS: list[tuple[int, int]] = [
        (30, 200),
        (50, 195),
        (80, 188),
        (110, 178),
        (140, 165),
        (170, 150),
        (200, 133),
        (220, 120),
        (235, 105),
        (245, 88),
    ]

    def __init__(self) -> None:
        self._rng = random.Random()
        self._init_state()

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = self.TIMER_START
        self.ball_color_idx = 0
        self.ball_x = float(self.LAUNCH_X)
        self.ball_y = float(self.LAUNCH_Y)
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.power = 0.0
        self.charging = False
        self.super_timer = 0
        self.scoring_timer = 0
        self.color_cycle_cooldown = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.ghost_points: list[GhostPoint] = []
        self.best_ghost: list[GhostPoint] = []
        self.holes: list[Hole] = []
        self._rng = random.Random()
        self._init_holes()

    def _init_holes(self) -> None:
        hole_colors = list(self.COLORS)
        self._rng.shuffle(hole_colors)
        hole_positions = [(190, 70), (230, 70), (270, 70), (310, 70)]
        self.holes = []
        for i, (hx, hy) in enumerate(hole_positions):
            self.holes.append(
                Hole(x=hx, y=hy, color=hole_colors[i], radius=self.HOLE_RADIUS, score=100)
            )

    def start_game(self) -> None:
        self.phase = Phase.AIMING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = self.TIMER_START
        self.ball_color_idx = 0
        self.ball_x = float(self.LAUNCH_X)
        self.ball_y = float(self.LAUNCH_Y)
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.power = 0.0
        self.charging = False
        self.super_timer = 0
        self.scoring_timer = 0
        self.color_cycle_cooldown = 0
        self.particles = []
        self.floating_texts = []
        self.ghost_points = []
        self.best_ghost = []
        self._init_holes()

    def _handle_aiming_input(self, mouse_down: bool, cycle_left: bool, cycle_right: bool) -> str:
        if mouse_down and not self.charging:
            self.charging = True
            return "charge_start"
        if mouse_down and self.charging:
            self.power = min(self.MAX_POWER, self.power + self.POWER_CHARGE_RATE)
            return "charging"
        if not mouse_down and self.charging:
            self._launch_ball()
            return "launch"

        if cycle_right:
            if self.color_cycle_cooldown <= 0:
                self.ball_color_idx = (self.ball_color_idx + 1) % self.NUM_COLORS
                self.color_cycle_cooldown = self.COLOR_CYCLE_COOLDOWN
                return "color_next"
        elif cycle_left:
            if self.color_cycle_cooldown <= 0:
                self.ball_color_idx = (self.ball_color_idx - 1) % self.NUM_COLORS
                self.color_cycle_cooldown = self.COLOR_CYCLE_COOLDOWN
                return "color_prev"

        return "idle"

    def _launch_ball(self) -> None:
        angle = -math.radians(45 + (1.0 - self.power / self.MAX_POWER) * 20)
        speed = self.power
        self.ball_vx = math.cos(angle) * speed
        self.ball_vy = math.sin(angle) * speed
        self.ball_x = float(self.LAUNCH_X)
        self.ball_y = float(self.LAUNCH_Y)
        self.ghost_points = []
        self.charging = False
        self.power = 0.0
        self.phase = Phase.FLYING

    def _update_flying(self) -> None:
        self.ball_vy += self.GRAVITY
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        self.ghost_points.append(GhostPoint(x=self.ball_x, y=self.ball_y))
        if len(self.ghost_points) > 120:
            self.ghost_points = self.ghost_points[-120:]

        hit_hole = self._check_hole_collision(self.ball_x, self.ball_y)
        if hit_hole is not None:
            self._handle_hit(hit_hole)
            return

        if self._ball_out_of_bounds():
            self._handle_miss()
            return

    def _ball_out_of_bounds(self) -> bool:
        return (
            self.ball_x < -20
            or self.ball_x > self.SCREEN_W + 20
            or self.ball_y < -20
            or self.ball_y > self.SCREEN_H + 20
        )

    def _check_hole_collision(self, ball_x: float, ball_y: float) -> Hole | None:
        for hole in self.holes:
            dx = ball_x - hole.x
            dy = ball_y - hole.y
            if dx * dx + dy * dy < hole.radius * hole.radius:
                return hole
        return None

    def _handle_hit(self, hole: Hole) -> None:
        matched = self._is_super_mode() or self.COLORS[self.ball_color_idx] == hole.color
        if matched:
            multiplier = self.SUPER_MULTIPLIER if self._is_super_mode() else 1
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            gained = hole.score * self.combo * multiplier
            self.score += gained

            p_color = hole.color
            p_count = self.SUPER_PARTICLE_COUNT if self._is_super_mode() else self.HIT_PARTICLE_COUNT
            self._spawn_hit_particles(hole.x, hole.y, p_color, p_count)

            if self._is_super_mode():
                rainbow_color = self.COLORS[(self.combo + self.super_timer) % self.NUM_COLORS]
                self._spawn_floating_text(hole.x, hole.y - 8, f"+{gained}", rainbow_color)
            elif self.combo >= 3:
                self._spawn_floating_text(hole.x, hole.y - 8, f"COMBO x{self.combo}", hole.color)
            else:
                self._spawn_floating_text(hole.x, hole.y - 8, f"+{gained}", self.WHITE)

            if self.combo >= self.SUPER_COMBO_THRESHOLD and not self._is_super_mode():
                self.super_timer = self.SUPER_DURATION
                self._spawn_floating_text(hole.x, hole.y - 16, "SUPER BALL!", self.YELLOW)

            if self._is_super_mode():
                self.super_timer = self.SUPER_DURATION
                if self.ghost_points and not self.best_ghost:
                    self.best_ghost = list(self.ghost_points)

            self._spawn_hit_particles(hole.x, hole.y, self.WHITE, 4)
        else:
            self.combo = 0
            self.heat = min(self.MAX_HEAT, self.heat + self.HEAT_MISMATCH)
            self._spawn_hit_particles(hole.x, hole.y, self.GRAY, self.MISS_PARTICLE_COUNT)
            self._spawn_floating_text(hole.x, hole.y - 8, "MISMATCH!", self.GRAY)

        self.scoring_timer = self.SCORING_DURATION
        self.phase = Phase.SCORING

    def _handle_miss(self) -> None:
        self.combo = 0
        self.heat = min(self.MAX_HEAT, self.heat + self.HEAT_MISS)
        self._spawn_hit_particles(self.ball_x, self.ball_y, self.GRAY, self.MISS_PARTICLE_COUNT)
        self._spawn_floating_text(self.ball_x, self.ball_y, "MISS!", self.GRAY)

        if self.ghost_points and not self.best_ghost:
            self.best_ghost = list(self.ghost_points)

        self.scoring_timer = self.SCORING_DURATION
        self.phase = Phase.SCORING

    def _is_super_mode(self) -> bool:
        return self.super_timer > 0

    def _update_heat(self) -> None:
        if self.heat >= self.MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.life -= 1
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.life -= 1
            ft.y -= 0.8
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER

    def _spawn_hit_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.random() * math.pi * 2
            speed = self._rng.random() * 2.5 + 0.5
            p_life = 15 + self._rng.randint(0, 10)
            self.particles.append(
                Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, p_life, color, 2)
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, 30, color))

    def _escalation_params(self) -> tuple[float, int]:
        elapsed = self.TIMER_START - self.timer
        seconds = elapsed // 30
        if seconds < 15:
            return (1.0, 0)
        elif seconds < 30:
            return (1.2, 45 * 30)  # shuffle holes every 45s
        elif seconds < 45:
            return (1.4, 30 * 30)
        else:
            return (1.6, 20 * 30)

    def _handle_title_input(self, action_pressed: bool) -> bool:
        if action_pressed:
            self.start_game()
            return True
        return False

    def _handle_gameover_input(self, action_pressed: bool) -> bool:
        if action_pressed:
            self.start_game()
            return True
        return False

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.start_game()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.start_game()
            return

        self._update_timer()
        if self.phase == Phase.GAME_OVER:
            return

        if self.color_cycle_cooldown > 0:
            self.color_cycle_cooldown -= 1

        if self._is_super_mode():
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.combo = 0

        if self.phase == Phase.AIMING:
            self._handle_aiming_input(
                mouse_down=pyxel.btn(pyxel.MOUSE_BUTTON_LEFT),
                cycle_left=pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A),
                cycle_right=pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D),
            )
        elif self.phase == Phase.FLYING:
            self._update_flying()
        elif self.phase == Phase.SCORING:
            self.scoring_timer -= 1
            if self.scoring_timer <= 0:
                self.ball_x = float(self.LAUNCH_X)
                self.ball_y = float(self.LAUNCH_Y)
                self.ball_vx = 0.0
                self.ball_vy = 0.0
                self.ghost_points = []
                self.phase = Phase.AIMING

        self._update_heat()
        if self.phase == Phase.GAME_OVER:
            return

        self._update_particles()
        self._update_floating_texts()

    def draw(self) -> None:
        pyxel.cls(self.DARK_BLUE)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_game()

    def _draw_title(self) -> None:
        title = "SKEE CHAIN"
        pyxel.text(self.SCREEN_W // 2 - len(title) * 4 // 2, 40, title, self.YELLOW)

        lines = [
            "Color-match skee-ball!",
            "",
            "Hold MOUSE to charge power",
            "Release to launch ball",
            "LEFT/RIGHT or A/D: cycle color",
            "Match ball color to hole!",
            "",
            "COMBO>=4 -> SUPER BALL (3x, rainbow)",
            "Mismatch = HEAT  /  HEAT>=100 = GAME OVER",
            "",
            "SPACE or RETURN to Start",
        ]
        y = 65
        for line in lines:
            color = self.WHITE
            if "SUPER BALL" in line:
                color = self.YELLOW
            elif "HEAT" in line:
                color = self.RED
            pyxel.text(self.SCREEN_W // 2 - len(line) * 4 // 2, y, line, color)
            y += 12

    def _draw_game_over(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 24, 60, "GAME OVER", self.RED)

        score_text = f"SCORE: {self.score}"
        pyxel.text(self.SCREEN_W // 2 - len(score_text) * 4 // 2, 90, score_text, self.WHITE)

        combo_text = f"MAX COMBO: {self.max_combo}"
        pyxel.text(self.SCREEN_W // 2 - len(combo_text) * 4 // 2, 110, combo_text, self.WHITE)

        seconds_left = max(0, self.timer) // 30
        time_text = f"SURVIVED: {60 - seconds_left}s"
        pyxel.text(self.SCREEN_W // 2 - len(time_text) * 4 // 2, 130, time_text, self.WHITE)

        retry_text = "SPACE or RETURN to Retry"
        pyxel.text(self.SCREEN_W // 2 - len(retry_text) * 4 // 2, 160, retry_text, self.WHITE)

    def _draw_game(self) -> None:
        self._draw_ramp()
        self._draw_holes()
        self._draw_ball()
        self._draw_ghost_trail()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_ramp(self) -> None:
        ramp = self.RAMP_POINTS
        for i in range(len(ramp) - 1):
            pyxel.line(ramp[i][0], ramp[i][1], ramp[i + 1][0], ramp[i + 1][1], self.BROWN)
        # ramp floor line
        pyxel.line(ramp[0][0] + 20, ramp[0][1], ramp[-1][0], ramp[-1][1] + 8, self.BROWN)

    def _draw_holes(self) -> None:
        for hole in self.holes:
            pyxel.circ(hole.x, hole.y, hole.radius, self.BLACK)
            pyxel.circb(hole.x, hole.y, hole.radius, hole.color)
            pyxel.circb(hole.x, hole.y, hole.radius - 1, hole.color)
            score_label = str(hole.score)
            pyxel.text(hole.x - len(score_label) * 2, hole.y + hole.radius + 2, score_label, self.WHITE)

    def _draw_ball(self) -> None:
        bx = int(self.ball_x)
        by = int(self.ball_y)
        ball_color = self.COLORS[self.ball_color_idx]
        if self._is_super_mode():
            ball_color = self.COLORS[(self.combo + self.super_timer) % self.NUM_COLORS]
        pyxel.circ(bx, by, self.BALL_RADIUS, ball_color)
        pyxel.circb(bx, by, self.BALL_RADIUS, self.WHITE)

    def _draw_ghost_trail(self) -> None:
        if not self.best_ghost:
            return
        for gp in self.best_ghost:
            gx = int(gp.x)
            gy = int(gp.y)
            if 0 <= gx < self.SCREEN_W and 0 <= gy < self.SCREEN_H:
                pyxel.pset(gx, gy, self.GHOST_TRAIL_COLOR)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.rect(int(p.x), int(p.y), p.size, p.size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            tx = int(ft.x) - len(ft.text) * 2
            ty = int(ft.y)
            pyxel.text(tx, ty, ft.text, ft.color)

    def _draw_hud(self) -> None:
        score_text = f"SCORE: {self.score}"
        pyxel.text(2, 2, score_text, self.WHITE)

        combo_color = self.WHITE
        if self.combo >= self.SUPER_COMBO_THRESHOLD:
            combo_color = self.YELLOW
        elif self.combo >= 2:
            combo_color = self.LIME
        combo_text = f"COMBO: {self.combo}"
        pyxel.text(self.SCREEN_W // 2 - len(combo_text) * 2, 2, combo_text, combo_color)

        seconds = max(0, self.timer) // 30
        timer_text = f"TIME: {seconds}"
        timer_color = self.RED if seconds <= 10 else self.WHITE
        pyxel.text(self.SCREEN_W - len(timer_text) * 4 - 2, 2, timer_text, timer_color)

        heat_bw = self.SCREEN_W - 4
        heat_bh = 4
        heat_bx = 2
        heat_by = self.SCREEN_H - 10
        pyxel.rect(heat_bx, heat_by, heat_bw, heat_bh, self.DARK_BLUE)
        heat_hw = int(heat_bw * self.heat / self.MAX_HEAT)
        heat_hc = self.GREEN
        if self.heat > 75:
            heat_hc = self.RED
        elif self.heat > 50:
            heat_hc = self.ORANGE
        elif self.heat > 25:
            heat_hc = self.YELLOW
        if heat_hw > 0:
            pyxel.rect(heat_bx, heat_by, heat_hw, heat_bh, heat_hc)
        pyxel.rectb(heat_bx, heat_by, heat_bw, heat_bh, self.WHITE)
        pyxel.text(heat_bx, heat_by + 5, "HEAT", self.WHITE)

        if self.phase == Phase.AIMING:
            color_name = self.COLOR_NAMES[self.ball_color_idx]
            ball_color = self.COLORS[self.ball_color_idx]
            cx = 50
            cy = self.SCREEN_H - 22
            pyxel.rect(cx, cy, 8, 8, ball_color)
            pyxel.text(cx + 10, cy - 1, f"COLOR: {color_name}", self.WHITE)

            bar_x = 160
            bar_y = self.SCREEN_H - 18
            bar_w = 100
            bar_h = 6
            pyxel.rect(bar_x, bar_y, bar_w, bar_h, self.DARK_BLUE)
            pw = int(bar_w * self.power / self.MAX_POWER)
            pcolor = self.GREEN if self.power < self.MAX_POWER * 0.5 else self.YELLOW if self.power < self.MAX_POWER * 0.8 else self.RED
            if pw > 0:
                pyxel.rect(bar_x, bar_y, pw, bar_h, pcolor)
            pyxel.rectb(bar_x, bar_y, bar_w, bar_h, self.WHITE)
            pyxel.text(bar_x + bar_w + 4, bar_y - 1, "POWER", self.GRAY)

        if self._is_super_mode():
            border_color = self.COLORS[(self.combo + self.super_timer) % self.NUM_COLORS]
            pyxel.rectb(0, 0, self.SCREEN_W, self.SCREEN_H, border_color)
            pyxel.rectb(1, 1, self.SCREEN_W - 2, self.SCREEN_H - 2, border_color)
            st = f"SUPER BALL! {self.super_timer // 30}s"
            sc = self.COLORS[(self.combo + self.super_timer) % self.NUM_COLORS]
            pyxel.text(self.SCREEN_W // 2 - len(st) * 2, self.SCREEN_H - 32, st, sc)


class App:
    def __init__(self) -> None:
        self.game = Game()
        pyxel.init(Game.SCREEN_W, Game.SCREEN_H, title="Skee Chain")
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        self.game.update()

    def draw(self) -> None:
        self.game.draw()


if __name__ == "__main__":
    App()
