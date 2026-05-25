import pyxel
import math
import random
from dataclasses import dataclass

SCREEN_W = 320
SCREEN_H = 240
LANE_LEFT = 60
LANE_RIGHT = 260
LANE_CENTER = 160
LANE_TOP = 20
PIN_AREA_BOTTOM = 200

BALL_RADIUS = 6
PIN_RADIUS = 5
BALL_START_Y = 24

PIN_COLORS: tuple[int, ...] = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
PIN_VALUES: dict[int, int] = {8: 8, 3: 3, 5: 5, 10: 10}
COLOR_NAMES: dict[int, str] = {8: "RED", 3: "GREEN", 5: "BLUE", 10: "YELLOW"}

MAX_FRAMES = 10
MAX_HEAT = 5
SURGE_THRESHOLD = 5
HEAT_DRIFT_START = 3

ANGLE_MAX = 28.0  # degrees

POWER_MIN_SPEED = 3.0
POWER_MAX_SPEED = 8.0
POWER_CHARGE_TIME = 70  # frames to full power

SCORING_DURATION = 50  # frames
FRAME_END_DURATION = 30  # frames
GUTTER_X_MARGIN = 30  # beyond lane edges = gutter


@dataclass
class Pin:
    x: float
    y: float
    color: int
    alive: bool = True
    vy: float = 0.0
    vx: float = 0.0
    hit_order: int = -1  # -1 = not hit


@dataclass
class Ball:
    x: float
    y: float
    color: int
    vy: float = 0.0
    vx: float = 0.0
    rolling: bool = False


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
    def __init__(self) -> None:
        self._rng = random.Random()
        self.reset()

    def reset(self) -> None:
        self.pins: list[Pin] = []
        self.ball: Ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8)
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.phase: str = "title"
        self.frame: int = 1
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: int = 0
        self.power: float = 0.0
        self.aim_angle: float = 0.0
        self.charging: bool = False
        self.hit_order_counter: int = 0
        self.phase_timer: int = 0
        self.is_surge_ball: bool = False
        self.frame_score: int = 0
        self.frame_knocked_count: int = 0
        self.frame_combo_text: str = ""
        self.total_frames_played: int = 0
        self._init_pins()
        self._assign_random_ball_color()

    def _init_pins(self) -> None:
        """Create 10 pins in standard bowling triangle layout with random colors."""
        self.pins.clear()
        pin_layout = [
            (LANE_CENTER, 130),
            (LANE_CENTER - 10, 148), (LANE_CENTER + 10, 148),
            (LANE_CENTER - 20, 166), (LANE_CENTER, 166), (LANE_CENTER + 20, 166),
            (LANE_CENTER - 30, 184), (LANE_CENTER - 10, 184),
            (LANE_CENTER + 10, 184), (LANE_CENTER + 30, 184),
        ]
        for x, y in pin_layout:
            color = self._rng.choice(PIN_COLORS)
            self.pins.append(Pin(x=x, y=y, color=color))

    def _assign_random_ball_color(self) -> None:
        self.ball.color = self._rng.choice(PIN_COLORS)

    def _roll_ball(self, angle_deg: float, power: float) -> None:
        """Set ball velocity based on aim angle and power."""
        angle_rad = math.radians(angle_deg)
        speed = POWER_MIN_SPEED + power * (POWER_MAX_SPEED - POWER_MIN_SPEED)
        self.ball.vx = speed * math.sin(angle_rad)
        self.ball.vy = speed * math.cos(angle_rad)
        self.ball.rolling = True

    def _update_ball(self) -> bool:
        """Move ball down lane. Check pin collisions. Returns True if ball is done."""
        if not self.ball.rolling:
            return False

        # Heat drift
        if self.heat >= HEAT_DRIFT_START:
            drift = (self._rng.random() - 0.5) * (self.heat - HEAT_DRIFT_START + 1) * 0.6
            self.ball.vx += drift * 0.3

        self.ball.x += self.ball.vx
        self.ball.y += self.ball.vy

        # Check pin collisions
        for pin in self.pins:
            if pin.alive and self._check_collision(self.ball, pin):
                pin.alive = False
                pin.hit_order = self.hit_order_counter
                self.hit_order_counter += 1
                dx = pin.x - self.ball.x
                dy = pin.y - self.ball.y
                dist = max(0.1, math.hypot(dx, dy))
                knock_strength = 3.0 + self.power * 3.0
                pin.vx = (dx / dist) * knock_strength
                pin.vy = (dy / dist) * knock_strength - 2.0
                self._spawn_particles(pin.x, pin.y, pin.color, 8)
                # Slightly deflect ball
                self.ball.vx -= (dx / dist) * 0.5
                self.ball.vy -= (dy / dist) * 0.5

        # Check if ball is done
        in_gutter = (
            self.ball.x < LANE_LEFT - GUTTER_X_MARGIN or
            self.ball.x > LANE_RIGHT + GUTTER_X_MARGIN
        )
        past_pins = self.ball.y > PIN_AREA_BOTTOM + 20

        return in_gutter or past_pins

    def _check_collision(self, ball: Ball, pin: Pin) -> bool:
        """Circle-circle collision between ball and pin."""
        dist = math.hypot(ball.x - pin.x, ball.y - pin.y)
        return dist < (BALL_RADIUS + PIN_RADIUS)

    def _update_pins(self) -> None:
        """Animate knocked pins (knockback + gravity)."""
        for pin in self.pins:
            if not pin.alive:
                pin.x += pin.vx
                pin.y += pin.vy
                pin.vy += 0.2  # gravity
                pin.vx *= 0.96  # friction
                pin.vy *= 0.96
                # Clamp to screen-ish bounds to avoid floating forever
                if pin.y > SCREEN_H + 20:
                    pin.vx = 0.0
                    pin.vy = 0.0

    def _evaluate_combo(
        self, knocked_pins: list[Pin], ball_color: int
    ) -> tuple[int, int, bool, str]:
        """Evaluate combo and score for this frame.

        Returns (new_combo, frame_score, is_miss, combo_text).
        """
        if not knocked_pins:
            return (0, 0, True, "MISS!")

        # Sort by hit order
        knocked_pins_sorted = sorted(knocked_pins, key=lambda p: p.hit_order)
        first_pin = knocked_pins_sorted[0]

        if self.is_surge_ball:
            # RAINBOW ball: all colors match
            new_combo = self.combo + 1
            combo_text = "SURGE COMBO!"
        elif first_pin.color == ball_color:
            new_combo = self.combo + 1
            combo_text = f"COMBO {new_combo}!"
        else:
            new_combo = 1
            combo_text = "COMBO RESET"

        multiplier = 1 + (new_combo - 1) * 0.5
        frame_score = 0
        for pin in knocked_pins:
            frame_score += int(PIN_VALUES[pin.color] * multiplier)

        if self.is_surge_ball:
            frame_score *= 3

        return (new_combo, frame_score, False, combo_text)

    def _is_gutter(self) -> bool:
        """Check if ball is in the gutter."""
        return (
            self.ball.x < LANE_LEFT - GUTTER_X_MARGIN or
            self.ball.x > LANE_RIGHT + GUTTER_X_MARGIN
        )

    def _spawn_particles(
        self, x: float, y: float, color: int, count: int = 8
    ) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            life = self._rng.randint(10, 25)
            self.particles.append(Particle(
                x=x + self._rng.uniform(-4, 4),
                y=y + self._rng.uniform(-4, 4),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 1.0,
                life=life,
                color=color,
            ))

    def _spawn_surge_particles(self) -> None:
        for _ in range(35):
            x = self._rng.uniform(LANE_LEFT, LANE_RIGHT)
            y = self._rng.uniform(BALL_START_Y + 10, PIN_AREA_BOTTOM)
            color = self._rng.choice(PIN_COLORS)
            life = self._rng.randint(15, 35)
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-3, 3),
                vy=self._rng.uniform(-4, -1),
                life=life,
                color=color,
            ))

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int, life: int = 40
    ) -> None:
        self.floating_texts.append(FloatingText(
            x=x, y=y, text=text, life=life, color=color,
        ))

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
            ft.y -= 0.6
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _get_knocked_pins(self) -> list[Pin]:
        return [p for p in self.pins if not p.alive and p.hit_order >= 0]

    def _any_pins_animating(self) -> bool:
        for p in self.pins:
            if not p.alive:
                if abs(p.vx) > 0.05 or abs(p.vy) > 0.05:
                    return True
        return False

    # ── Update ──

    def update(self) -> None:
        if self.phase == "title":
            self._update_title()
        elif self.phase == "aiming":
            self._update_aiming()
        elif self.phase == "rolling":
            self._update_rolling()
        elif self.phase == "scoring":
            self._update_scoring()
        elif self.phase == "frame_end":
            self._update_frame_end()
        elif self.phase == "game_over":
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = "aiming"

    def _update_aiming(self) -> None:
        # Aim angle from mouse
        rel_x = pyxel.mouse_x - LANE_CENTER
        self.aim_angle = max(-ANGLE_MAX, min(ANGLE_MAX, rel_x * 0.22))

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.charging = True
            self.power = 0.0

        if self.charging and pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            self.power = min(1.0, self.power + 1.0 / POWER_CHARGE_TIME)
        elif self.charging:
            # Released: launch ball
            self.power = min(1.0, self.power + 0.05)  # minimum power
            self._launch_ball()

    def _launch_ball(self) -> None:
        self.charging = False
        self.ball.x = LANE_CENTER
        self.ball.y = BALL_START_Y
        self.hit_order_counter = 0

        # Determine ball color
        if self.combo >= SURGE_THRESHOLD:
            self.is_surge_ball = True
            self.ball.color = 7  # WHITE visual for rainbow
        else:
            self.is_surge_ball = False
            self._assign_random_ball_color()

        self._roll_ball(self.aim_angle, self.power)
        self.phase = "rolling"

    def _update_rolling(self) -> None:
        ball_done = self._update_ball()
        self._update_pins()
        self._update_particles()
        self._update_floating_texts()

        if ball_done:
            knocked = self._get_knocked_pins()
            is_gutter = self._is_gutter() and len(knocked) == 0

            if is_gutter or len(knocked) == 0:
                # Miss / gutter
                self.heat = min(MAX_HEAT, self.heat + 1)
                self.combo = 0
                self.frame_score = 0
                self.frame_knocked_count = 0
                self.frame_combo_text = "MISS!"
                if self.is_surge_ball:
                    self.is_surge_ball = False
                self._spawn_floating_text(
                    LANE_CENTER, BALL_START_Y + 10,
                    "MISS! +Heat", pyxel.COLOR_RED, 45,
                )
            else:
                ball_color = 8 if self.is_surge_ball else self.ball.color
                new_combo, frame_score, _, combo_text = self._evaluate_combo(
                    knocked, ball_color,
                )
                self.combo = new_combo
                self.max_combo = max(self.max_combo, self.combo)
                self.score += frame_score
                self.frame_score = frame_score
                self.frame_knocked_count = len(knocked)
                self.frame_combo_text = combo_text

                if self.is_surge_ball:
                    self._spawn_surge_particles()
                    self._spawn_floating_text(
                        LANE_CENTER, BALL_START_Y + 10,
                        "STRIKE SURGE!!", pyxel.COLOR_YELLOW, 60,
                    )
                    self.is_surge_ball = False
                    self.combo = 0
                else:
                    self._spawn_floating_text(
                        LANE_CENTER, BALL_START_Y + 10,
                        combo_text, pyxel.COLOR_WHITE, 40,
                    )

            self.total_frames_played += 1

            if self.heat >= MAX_HEAT:
                self.phase = "game_over"
                return

            self.phase = "scoring"
            self.phase_timer = SCORING_DURATION

        # Check heat game over mid-roll (unlikely but defensive)
        if self.heat >= MAX_HEAT:
            self.phase = "game_over"

    def _update_scoring(self) -> None:
        self._update_pins()
        self._update_particles()
        self._update_floating_texts()

        self.phase_timer -= 1
        if self.phase_timer <= 0 and not self._any_pins_animating():
            if self.frame >= MAX_FRAMES:
                self.phase = "game_over"
            else:
                self.frame += 1
                self.phase = "aiming"

    def _update_frame_end(self) -> None:
        self.phase_timer -= 1
        if self.phase_timer <= 0:
            if self.frame >= MAX_FRAMES:
                self.phase = "game_over"
            else:
                self.frame += 1
                self.phase = "aiming"

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            self.phase = "aiming"

    # ── Draw ──

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == "title":
            self._draw_title()
        else:
            self._draw_lane()
            self._draw_pins()
            self._draw_ball()
            self._draw_particles()
            self._draw_floating_texts()
            self._draw_aim_line()
            self._draw_power_gauge()
            self._draw_hud()

            if self.phase == "game_over":
                self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(95, 50, "STRIKE CHAIN", pyxel.COLOR_YELLOW)
        pyxel.text(70, 80, "Color-Match Bowling", pyxel.COLOR_WHITE)
        pyxel.text(62, 115, "SPACE or CLICK to START", pyxel.COLOR_CYAN)
        pyxel.text(50, 145, "MOUSE: Aim & Power", pyxel.COLOR_GREEN)
        pyxel.text(50, 157, "Click+Hold to charge power", pyxel.COLOR_GREEN)
        pyxel.text(50, 169, "Release to roll!", pyxel.COLOR_GREEN)
        pyxel.text(28, 190, "Same-color hits = COMBO", pyxel.COLOR_YELLOW)
        pyxel.text(28, 202, "COMBO x5 = STRIKE SURGE!", pyxel.COLOR_YELLOW)
        pyxel.text(28, 218, "MISS / Gutter = HEAT -> GAME OVER", pyxel.COLOR_RED)

        # Color legend
        for i, c in enumerate(PIN_COLORS):
            cx = 110 + i * 28
            pyxel.rect(cx, 180, 12, 8, c)

    def _draw_lane(self) -> None:
        # Lane border
        pyxel.rectb(LANE_LEFT - 2, 0, LANE_RIGHT - LANE_LEFT + 4, SCREEN_H, pyxel.COLOR_WHITE)
        # Lane surface
        pyxel.rect(LANE_LEFT, 0, LANE_RIGHT - LANE_LEFT, SCREEN_H, pyxel.COLOR_NAVY)

        # Lane markings
        for i in range(4):
            ly = 40 + i * 45
            pyxel.line(LANE_LEFT, ly, LANE_RIGHT, ly, pyxel.COLOR_DARK_BLUE)

        # Gutter indicators
        pyxel.rect(LANE_LEFT - 22, 0, 20, PIN_AREA_BOTTOM, pyxel.COLOR_BROWN)
        pyxel.rect(LANE_RIGHT + 2, 0, 20, PIN_AREA_BOTTOM, pyxel.COLOR_BROWN)

    def _draw_pins(self) -> None:
        for pin in self.pins:
            if not pin.alive:
                if abs(pin.vx) < 0.05 and abs(pin.vy) < 0.05:
                    if pin.y > SCREEN_H:
                        continue
                pyxel.circ(int(pin.x), int(pin.y), PIN_RADIUS, pin.color)
                pyxel.circb(int(pin.x), int(pin.y), PIN_RADIUS, pyxel.COLOR_BLACK)
            elif self.phase != "title":
                pyxel.circ(int(pin.x), int(pin.y), PIN_RADIUS, pin.color)
                pyxel.circb(int(pin.x), int(pin.y), PIN_RADIUS, pyxel.COLOR_WHITE)

    def _draw_ball(self) -> None:
        if self.phase in ("title",):
            return
        if self.ball.rolling or self.phase in ("aiming", "scoring"):
            ball_c = self.ball.color if not self.is_surge_ball else pyxel.COLOR_WHITE
            # Surge ball has rainbow ring
            if self.is_surge_ball and self.phase == "aiming":
                rainbow_colors = [8, 9, 10, 11, 12, 14, 3, 5]
                r_idx = (pyxel.frame_count // 4) % len(rainbow_colors)
                pyxel.circ(int(self.ball.x), int(self.ball.y), BALL_RADIUS + 2,
                           rainbow_colors[r_idx])
            pyxel.circ(int(self.ball.x), int(self.ball.y), BALL_RADIUS, ball_c)
            pyxel.circb(int(self.ball.x), int(self.ball.y), BALL_RADIUS, pyxel.COLOR_WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25.0
            if alpha > 0.3:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 60.0
            if alpha > 0.15:
                pyxel.text(int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, ft.color)

    def _draw_aim_line(self) -> None:
        if self.phase not in ("aiming",):
            return
        if self.ball.rolling:
            return

        # Dashed aim line from ball toward aim direction
        angle_rad = math.radians(self.aim_angle)
        sx = self.ball.x
        sy = self.ball.y
        dash_len = 6
        gap_len = 4
        total_seg = dash_len + gap_len
        max_dist = 400
        drawn = 0.0
        idx = 0
        while drawn < max_dist:
            nx = sx + math.sin(angle_rad) * drawn
            ny = sy + math.cos(angle_rad) * drawn
            if ny > PIN_AREA_BOTTOM + 10:
                break
            if idx % 2 == 0:
                ex = sx + math.sin(angle_rad) * min(drawn + dash_len, max_dist)
                ey = sy + math.cos(angle_rad) * min(drawn + dash_len, max_dist)
                pyxel.line(int(nx), int(ny), int(ex), int(ey), pyxel.COLOR_LIGHT_BLUE)
            drawn += total_seg
            idx += 1

    def _draw_power_gauge(self) -> None:
        if self.phase == "aiming" and self.charging:
            bar_x = LANE_RIGHT + 14
            bar_y = 50
            bar_w = 10
            bar_h = 120
            fill_h = int(bar_h * self.power)
            pyxel.rectb(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, pyxel.COLOR_WHITE)
            pyxel.rect(bar_x, bar_y + bar_h - fill_h, bar_w, fill_h, pyxel.COLOR_YELLOW)
            pyxel.text(bar_x - 4, bar_y + bar_h + 4, "PWR", pyxel.COLOR_WHITE)

    def _draw_hud(self) -> None:
        # Frame
        pyxel.text(2, 2, f"Frame {self.frame}/{MAX_FRAMES}", pyxel.COLOR_WHITE)
        # Score
        pyxel.text(2, 12, f"Score: {self.score}", pyxel.COLOR_WHITE)
        # Combo
        combo_c = pyxel.COLOR_YELLOW if self.combo >= SURGE_THRESHOLD else pyxel.COLOR_WHITE
        pyxel.text(2, 22, f"Combo: {self.combo}", combo_c)
        if self.is_surge_ball and self.phase == "aiming":
            rainbow = [pyxel.COLOR_RED, pyxel.COLOR_ORANGE, pyxel.COLOR_YELLOW,
                       pyxel.COLOR_LIME, pyxel.COLOR_CYAN]
            c = rainbow[(pyxel.frame_count // 8) % len(rainbow)]
            pyxel.text(80, 22, "SURGE READY!", c)
        # Heat gauge
        pyxel.text(2, 32, "Heat:", pyxel.COLOR_WHITE)
        for i in range(MAX_HEAT):
            hx = 38 + i * 10
            hc = pyxel.COLOR_RED if i < self.heat else pyxel.COLOR_GRAY
            pyxel.rect(hx, 32, 7, 6, hc)
        # Frame score (shown during scoring)
        if self.phase == "scoring":
            pyxel.text(LANE_CENTER - 30, BALL_START_Y + 22,
                       f"+{self.frame_score}", pyxel.COLOR_YELLOW)
            pyxel.text(LANE_CENTER - 25, BALL_START_Y + 34,
                       self.frame_combo_text, pyxel.COLOR_WHITE)
        # Ball color hint
        if self.phase == "aiming" and not self.is_surge_ball:
            bc = self.ball.color
            pyxel.text(LANE_CENTER - 30, 6,
                       f"Ball: {COLOR_NAMES.get(bc, '?')}", bc)
        # Max combo
        pyxel.text(2, 42, f"MaxCombo: {self.max_combo}", pyxel.COLOR_PURPLE)

    def _draw_game_over(self) -> None:
        # Semi-transparent overlay using pattern
        for y in range(0, SCREEN_H, 2):
            for x in range(0, SCREEN_W, 2):
                if (x // 2 + y // 2) % 2 == 0:
                    pyxel.pset(x, y, pyxel.COLOR_BLACK)

        pyxel.text(100, 50, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(68, 75, f"FINAL SCORE: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(68, 90, f"FRAMES: {self.total_frames_played}/{MAX_FRAMES}", pyxel.COLOR_WHITE)
        pyxel.text(68, 105, f"MAX COMBO: {self.max_combo}", pyxel.COLOR_YELLOW)

        reason = "Lane unplayable!" if self.heat >= MAX_HEAT else "All frames complete!"
        pyxel.text(68, 125, reason, pyxel.COLOR_CYAN)
        pyxel.text(72, 155, "Press R to Retry", pyxel.COLOR_CYAN)


class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Strike Chain", display_scale=2)
        self.game = Game()
        pyxel.run(self.game.update, self.game.draw)


if __name__ == "__main__":
    App()
