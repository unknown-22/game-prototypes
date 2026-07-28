import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240
FPS = 30
GROUND_Y = 200
FOUL_LINE_X = 260
RUNNER_START_X = 30
RUN_SPEED_BASE = 0.5
RUN_SPEED_MAX = 5.0
POWER_CHARGE_RATE = 100.0 / 60.0
POWER_DECAY_RATE = POWER_CHARGE_RATE * 0.5
GRAVITY = 0.25
NUM_JUMPS = 6
GAME_TIME = 60 * FPS

COLOR_RED = 8
COLOR_LIME = 11
COLOR_DARK_BLUE = 5
COLOR_YELLOW = 10
PLAYER_COLORS = (COLOR_RED, COLOR_LIME, COLOR_DARK_BLUE, COLOR_YELLOW)
COLOR_NAMES = ("RED", "LIME", "DARK_BLUE", "YELLOW")
COLOR_GRAY = 13
COLOR_WHITE = 7
COLOR_BLACK = 0
COLOR_NAVY = 1
COLOR_BROWN = 4

ZONE_DEFS = [
    (100, 40, "4.0m"),
    (140, 40, "5.0m"),
    (180, 40, "6.0m"),
    (220, 40, "7.0m"),
    (260, 40, "8.0m"),
]
SUPER_DURATION = 300
COMBO_THRESHOLD = 4
HEAT_MAX = 100
HEAT_DECAY = 0.02
HEAT_MISMATCH = 15
HEAT_FOUL = 20
COLOR_CYCLE_SPEED = 20
SCORING_FRAMES = 45
FOUL_SCORING_FRAMES = 30


class Phase(Enum):
    TITLE = auto()
    APPROACH = auto()
    FLIGHT = auto()
    SCORING = auto()
    GAME_OVER = auto()
    VICTORY = auto()


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


@dataclass
class Zone:
    x: float
    y: float
    width: int
    color: int
    distance_label: str


def parse_distance(label: str) -> float:
    return float(label.rstrip("m"))


class Game:
    def __init__(self):
        pyxel.init(SCREEN_W, SCREEN_H, title="LEAP CHAIN", fps=FPS)
        self.zones: list[Zone] = []
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.runner_x = float(RUNNER_START_X)
        self.runner_y = float(GROUND_Y)
        self.power = 0.0
        self.angle = 45.0
        self.vx = 0.0
        self.vy = 0.0
        self.flight_frame = 0
        self.jump_x_start = 0.0

        self.combo = 0
        self.score = 0
        self.jumps_used = 0
        self.heat = 0.0
        self.timer = GAME_TIME

        self.super_remaining = 0
        self.super_active = False

        self.current_color_idx = 0
        self.color_timer = 0

        self.best_distance = 0.0
        self.jump_distances: list[float] = []

        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

        self.scoring_timer = 0
        self.scoring_zone_idx = -1
        self.scoring_distance = 0.0
        self.scoring_is_foul = False

        self.screen_shake = 0

        self._spawn_zones()

    def _spawn_zones(self) -> None:
        self.zones = []
        colors_pool = list(PLAYER_COLORS)
        random.shuffle(colors_pool)
        zone_colors = [colors_pool[i % len(colors_pool)] for i in range(len(ZONE_DEFS))]
        random.shuffle(zone_colors)
        for i, (cx, width, label) in enumerate(ZONE_DEFS):
            self.zones.append(Zone(float(cx), float(GROUND_Y), width, zone_colors[i], label))

    def _cycle_color(self) -> None:
        self.color_timer += 1
        if self.color_timer >= COLOR_CYCLE_SPEED:
            self.color_timer = 0
            self.current_color_idx = (self.current_color_idx + 1) % len(PLAYER_COLORS)

    @property
    def current_color(self) -> int:
        return PLAYER_COLORS[self.current_color_idx]

    @property
    def current_color_name(self) -> str:
        return COLOR_NAMES[self.current_color_idx]

    # --- Testable pure-logic methods ---

    def _get_power(self) -> float:
        return self.power

    def _get_launch_velocity(self, power: float, angle: float) -> tuple[float, float]:
        angle_rad = math.radians(angle)
        speed = 2.0 + (power / 100.0) * 8.0
        vx = speed * math.cos(angle_rad)
        vy = -speed * math.sin(angle_rad)
        return vx, vy

    def _get_flight_position(self, t: int, vx: float, vy: float) -> tuple[float, float]:
        x = self.jump_x_start + vx * t
        y = GROUND_Y + vy * t + 0.5 * GRAVITY * t * t
        return x, y

    def _check_landing_zone(self, x: float) -> tuple[int, float]:
        for i, zone in enumerate(self.zones):
            if zone.x - zone.width / 2 <= x < zone.x + zone.width / 2:
                return i, parse_distance(zone.distance_label)
        first_zone = self.zones[0]
        if x < first_zone.x - first_zone.width / 2:
            return -1, 0.0
        return -1, 0.0

    def _compute_score(self, distance: float, combo: int, is_super: bool) -> int:
        multiplier = 3 if is_super else 1
        base = int(distance * 10)
        combo_bonus = max(1, combo)
        return base * combo_bonus * multiplier

    def _update_heat(self, heat: float) -> tuple[float, bool]:
        if heat >= HEAT_MAX:
            return heat, True
        return max(0.0, heat - HEAT_DECAY), False

    def _angle_from_mouse(self, mouse_y: int) -> float:
        normalized = max(0.0, min(1.0, mouse_y / GROUND_Y))
        return 75.0 - normalized * 55.0

    # --- Add particles / floating text (pure helpers, random seeded for tests) ---

    def _add_particles(self, x: float, y: float, count: int, colors: list[int], spread: float = 2.0) -> None:
        for _ in range(count):
            color = random.choice(colors)
            vx = random.uniform(-spread, spread)
            vy = random.uniform(-spread - 1.0, -1.0)
            self.particles.append(Particle(x, y, vx, vy, random.randint(15, 30), color))

    def _add_floating_text(self, x: float, y: float, text: str, color: int, life: int = 60) -> None:
        self.floating_texts.append(FloatingText(x, y, text, life, color))

    # --- Update ---

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.APPROACH:
            self._update_approach()
        elif self.phase == Phase.FLIGHT:
            self._update_flight()
        elif self.phase == Phase.SCORING:
            self._update_scoring()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()
        elif self.phase == Phase.VICTORY:
            self._update_victory()

        self._update_particles()
        self._update_floating_texts()
        if self.screen_shake > 0:
            self.screen_shake -= 1

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.APPROACH

    def _update_approach(self) -> None:
        self.timer -= 1

        run_speed = RUN_SPEED_BASE + (RUN_SPEED_MAX - RUN_SPEED_BASE) * (self.power / 100.0)
        self.runner_x += run_speed

        if self.runner_x >= FOUL_LINE_X:
            self._handle_foul("foul_line")
            return

        if self.super_remaining > 0:
            self.super_remaining -= 1
            if self.super_remaining <= 0:
                self.super_active = False

        self._cycle_color()

        if pyxel.btn(pyxel.KEY_SPACE):
            self.power = min(100.0, self.power + POWER_CHARGE_RATE)
        elif pyxel.btnr(pyxel.KEY_SPACE):
            if self.power > 0:
                self._launch()
                return
            self.power = max(0.0, self.power - POWER_DECAY_RATE)
        else:
            self.power = max(0.0, self.power - POWER_DECAY_RATE)

    def _launch(self) -> None:
        if self.super_active:
            actual_power = 100.0
        else:
            actual_power = self.power
        self.angle = self._angle_from_mouse(pyxel.mouse_y)
        self.vx, self.vy = self._get_launch_velocity(actual_power, self.angle)
        self.jump_x_start = self.runner_x
        self.flight_frame = 0
        self.phase = Phase.FLIGHT

    def _handle_foul(self, reason: str) -> None:
        self.power = 0.0
        self._add_particles(self.runner_x, GROUND_Y - 5, 6, [COLOR_GRAY], spread=1.5)
        self._add_floating_text(self.runner_x - 10, GROUND_Y - 25, "FOUL!", COLOR_RED, 60)
        if not self.super_active:
            self.heat += HEAT_FOUL
        self.combo = 0
        self.best_distance = max(self.best_distance, 0.0)
        self.jump_distances.append(0.0)
        self.scoring_timer = FOUL_SCORING_FRAMES
        self.scoring_zone_idx = -1
        self.scoring_distance = 0.0
        self.scoring_is_foul = True
        self.phase = Phase.SCORING

    def _update_flight(self) -> None:
        self.timer -= 1
        self.flight_frame += 1
        self.runner_x, self.runner_y = self._get_flight_position(self.flight_frame, self.vx, self.vy)

        color = self.current_color
        if self.super_active:
            color = PLAYER_COLORS[(self.flight_frame // 4) % len(PLAYER_COLORS)]
        if self.flight_frame % 4 == 0:
            self._add_particles(self.runner_x, self.runner_y, 1, [color], spread=1.0)

        if self.runner_y >= GROUND_Y:
            self.runner_y = GROUND_Y
            self._resolve_landing()

    def _resolve_landing(self) -> None:
        zone_idx, distance = self._check_landing_zone(self.runner_x)

        if zone_idx < 0:
            self._add_particles(self.runner_x, GROUND_Y - 5, 6, [COLOR_GRAY], spread=1.5)
            self._add_floating_text(self.runner_x - 10, GROUND_Y - 25, "SHORT!", COLOR_RED, 45)
            if not self.super_active:
                self.heat += HEAT_FOUL
            self.combo = 0
            self.best_distance = max(self.best_distance, distance)
            self.jump_distances.append(distance)
            self.scoring_timer = FOUL_SCORING_FRAMES
            self.scoring_zone_idx = -1
            self.scoring_distance = distance
            self.scoring_is_foul = True
            self.phase = Phase.SCORING
            return

        landing_zone = self.zones[zone_idx]
        is_match = landing_zone.color == self.current_color
        is_super = self.super_active

        if is_match or is_super:
            self.combo += 1
            pts = self._compute_score(distance, self.combo, is_super)
            self.score += pts

            if is_super:
                self._add_particles(self.runner_x, GROUND_Y - 5, 25, list(PLAYER_COLORS), spread=4.0)
                self._add_floating_text(self.runner_x - 25, GROUND_Y - 40, "SUPER LEAP!", COLOR_WHITE, 60)
                self._add_floating_text(self.runner_x - 10, GROUND_Y - 25, f"+{pts}", COLOR_WHITE, 45)
                self.screen_shake = 10
            else:
                self._add_particles(self.runner_x, GROUND_Y - 5, 12, [self.current_color], spread=2.5)
                self._add_floating_text(self.runner_x - 10, GROUND_Y - 25, f"+{pts}", self.current_color, 45)
                if self.combo >= 2:
                    self._add_floating_text(self.runner_x - 15, GROUND_Y - 40, f"COMBO x{self.combo}", COLOR_WHITE, 30)

            if self.combo >= COMBO_THRESHOLD and not self.super_active:
                self.super_active = True
                self.super_remaining = SUPER_DURATION
                self._add_floating_text(self.runner_x - 25, GROUND_Y - 55, "SUPER LEAP READY!", COLOR_WHITE, 60)
        else:
            self._add_particles(self.runner_x, GROUND_Y - 5, 5, [COLOR_GRAY], spread=1.5)
            self._add_floating_text(self.runner_x - 15, GROUND_Y - 25, "WRONG!", COLOR_RED, 40)
            if not self.super_active:
                self.heat += HEAT_MISMATCH
            self.combo = 0

        self.best_distance = max(self.best_distance, distance)
        self.jump_distances.append(distance)
        self.scoring_timer = SCORING_FRAMES
        self.scoring_zone_idx = zone_idx
        self.scoring_distance = distance
        self.scoring_is_foul = False
        self.phase = Phase.SCORING

    def _update_scoring(self) -> None:
        self.scoring_timer -= 1

        if self.super_remaining > 0:
            self.super_remaining -= 1
            if self.super_remaining <= 0:
                self.super_active = False

        if self.scoring_timer <= 0:
            self.jumps_used += 1

            if self.heat >= HEAT_MAX:
                self.phase = Phase.GAME_OVER
                return
            if self.timer <= 0:
                self.phase = Phase.GAME_OVER
                return
            if self.jumps_used >= NUM_JUMPS:
                self.phase = Phase.VICTORY
                return

            self.heat, _ = self._update_heat(self.heat)
            self._reset_for_next_jump()

    def _reset_for_next_jump(self) -> None:
        self.runner_x = float(RUNNER_START_X)
        self.runner_y = float(GROUND_Y)
        self.power = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.flight_frame = 0
        self.angle = 45.0
        self._spawn_zones()
        self.phase = Phase.APPROACH

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.APPROACH

    def _update_victory(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.APPROACH

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # --- Draw ---

    def draw(self) -> None:
        pyxel.cls(COLOR_BLACK)

        if self.phase in (Phase.APPROACH, Phase.FLIGHT, Phase.SCORING):
            self._draw_game()
        elif self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        elif self.phase == Phase.VICTORY:
            self._draw_victory()

    def _draw_title(self) -> None:
        pyxel.cls(COLOR_DARK_BLUE)
        pyxel.text(110, 50, "LEAP CHAIN", COLOR_WHITE)
        pyxel.text(85, 70, "Long Jump Color-Match", COLOR_WHITE)
        pyxel.text(60, 100, "HOLD SPACE to charge", COLOR_WHITE)
        pyxel.text(60, 110, "RELEASE to jump", COLOR_WHITE)
        pyxel.text(60, 120, "Mouse Y = angle", COLOR_WHITE)
        pyxel.text(60, 140, "Match color = COMBO", COLOR_WHITE)
        pyxel.text(60, 150, "COMBO x4 = SUPER LEAP!", COLOR_WHITE)
        pyxel.text(75, 175, "Press SPACE to start", COLOR_YELLOW)

    def _draw_game(self) -> None:
        shake_x = 0
        shake_y = 0
        if self.screen_shake > 0:
            shake_x = random.randint(-3, 3)
            shake_y = random.randint(-3, 3)

        pyxel.cls(COLOR_NAVY)

        # Ground
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, COLOR_BROWN)

        # Landing zones
        for zone in self.zones:
            x1 = int(zone.x - zone.width // 2) + shake_x
            x2 = int(zone.x + zone.width // 2) + shake_x
            pyxel.rect(x1, GROUND_Y - 8, x2 - x1, 8, zone.color)
            pyxel.text(int(zone.x) - 8 + shake_x, GROUND_Y - 18, zone.distance_label, COLOR_WHITE)

        # Foul line
        pyxel.rect(int(FOUL_LINE_X) + shake_x - 1, GROUND_Y - 15, 2, 15, COLOR_WHITE)

        # Runner
        self._draw_runner(shake_x, shake_y)

        # Particles
        for p in self.particles:
            x = int(p.x) + shake_x
            y = int(p.y) + shake_y
            if 0 <= x < SCREEN_W and 0 <= y < SCREEN_H:
                pyxel.pset(x, y, p.color)

        # Floating texts
        for ft in self.floating_texts:
            x = int(ft.x) + shake_x
            y = int(ft.y) + shake_y
            if 0 <= x < SCREEN_W and 0 <= y < SCREEN_H:
                pyxel.text(x, y, ft.text, ft.color)

        # Power bar
        if self.phase == Phase.APPROACH:
            bar_x = 8
            bar_y = 8
            bar_w = 50
            bar_h = 6
            pyxel.rectb(bar_x, bar_y, bar_w, bar_h, COLOR_WHITE)
            fill_w = int(bar_w * self.power / 100.0)
            bar_color = COLOR_LIME
            if self.power > 66:
                bar_color = COLOR_RED
            elif self.power > 33:
                bar_color = COLOR_YELLOW
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, bar_color)

        # HUD
        pyxel.text(4, 18, f"SCORE: {self.score}", COLOR_WHITE)
        pyxel.text(4, 26, f"COMBO: {self.combo}", COLOR_WHITE)
        pyxel.text(4, 34, f"JUMP: {self.jumps_used}/{NUM_JUMPS}", COLOR_WHITE)
        pyxel.text(4, 42, f"TIME: {max(0, self.timer // FPS)}s", COLOR_WHITE)
        pyxel.text(4, 50, f"COLOR: {self.current_color_name}", self.current_color)

        if self.super_active:
            pyxel.text(4, 58, f"SUPER: {self.super_remaining}f", COLOR_WHITE)

        # HEAT bar
        heat_x = SCREEN_W - 60
        heat_y = 8
        heat_w = 50
        heat_h = 6
        pyxel.rectb(heat_x, heat_y, heat_w, heat_h, COLOR_WHITE)
        fill_w = int(heat_w * min(1.0, self.heat / HEAT_MAX))
        heat_color = COLOR_LIME
        if self.heat > 66:
            heat_color = COLOR_RED
        elif self.heat > 33:
            heat_color = COLOR_YELLOW
        pyxel.rect(heat_x, heat_y, fill_w, heat_h, heat_color)
        pyxel.text(heat_x, heat_y + 8, "HEAT:" + f"{self.heat:.0f}", COLOR_WHITE)

        # Score popup during SCORING
        if self.phase == Phase.SCORING and self.scoring_distance > 0:
            pyxel.text(SCREEN_W // 2 - 20, GROUND_Y - 50, f"{self.scoring_distance:.1f}m", COLOR_WHITE)

        # SUPER border
        if self.super_active:
            c = PLAYER_COLORS[(pyxel.frame_count // 4) % len(PLAYER_COLORS)]
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, c)
            pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, c)

    def _draw_runner(self, shake_x: int, shake_y: int) -> None:
        if self.super_active:
            c = PLAYER_COLORS[(pyxel.frame_count // 5) % len(PLAYER_COLORS)]
        elif self.phase == Phase.SCORING:
            c = self.current_color
        else:
            c = self.current_color

        rx = int(self.runner_x) + shake_x
        ry = int(self.runner_y) + shake_y

        pyxel.circ(rx, ry - 18, 3, c)
        pyxel.line(rx, ry - 15, rx, ry - 5, c)
        pyxel.line(rx, ry - 12, rx - 5, ry - 8, c)
        pyxel.line(rx, ry - 12, rx + 5, ry - 8, c)

        if self.phase == Phase.FLIGHT:
            pyxel.line(rx, ry - 5, rx - 4, ry + 2, c)
            pyxel.line(rx, ry - 5, rx + 4, ry + 2, c)
        else:
            leg_offset = pyxel.frame_count % 12
            if leg_offset < 6:
                pyxel.line(rx, ry - 5, rx - 4, ry, c)
                pyxel.line(rx, ry - 5, rx + 4, ry, c)
            else:
                pyxel.line(rx, ry - 5, rx + 4, ry, c)
                pyxel.line(rx, ry - 5, rx - 4, ry, c)

    def _draw_game_over(self) -> None:
        pyxel.cls(COLOR_DARK_BLUE)
        pyxel.text(100, 40, "GAME OVER", COLOR_RED)
        pyxel.text(75, 60, f"Score: {self.score}", COLOR_WHITE)
        pyxel.text(55, 72, f"Best Distance: {self.best_distance:.1f}m", COLOR_WHITE)
        pyxel.text(60, 88, f"HEAT: {self.heat:.0f}", COLOR_RED)
        pyxel.text(60, 98, f"Jumps: {len(self.jump_distances)}", COLOR_WHITE)

        y = 115
        for i, d in enumerate(self.jump_distances):
            pyxel.text(90, y, f"Jump {i + 1}: {d:.1f}m", COLOR_WHITE)
            y += 10

        pyxel.text(55, y + 10, "Press SPACE to retry", COLOR_YELLOW)

    def _draw_victory(self) -> None:
        pyxel.cls(COLOR_DARK_BLUE)
        pyxel.text(105, 30, "VICTORY!", COLOR_LIME)
        pyxel.text(75, 50, f"Total Score: {self.score}", COLOR_WHITE)
        pyxel.text(55, 62, f"Best Distance: {self.best_distance:.1f}m", COLOR_WHITE)
        pyxel.text(60, 74, f"Jumps: {len(self.jump_distances)}", COLOR_WHITE)

        y = 90
        for i, d in enumerate(self.jump_distances):
            pyxel.text(90, y, f"Jump {i + 1}: {d:.1f}m", COLOR_WHITE)
            y += 10

        pyxel.text(55, y + 10, "Press SPACE to play again", COLOR_YELLOW)


if __name__ == "__main__":
    Game()
