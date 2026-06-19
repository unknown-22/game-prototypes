import pyxel
import random
import math
from dataclasses import dataclass
from enum import Enum, auto


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# Internal color indices
COLOR_RED = 0
COLOR_GREEN = 1
COLOR_BLUE = 2
COLOR_YELLOW = 3
NUM_COLORS = 4
ALL_COLORS = [COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW]

# Pyxel colors for rings (DARK_BLUE for blue ring visibility)
RING_PYXEL = [pyxel.COLOR_RED, pyxel.COLOR_GREEN, pyxel.COLOR_DARK_BLUE, pyxel.COLOR_YELLOW]
# Pyxel colors for balloon (LIGHT_BLUE for better contrast)
BALLOON_PYXEL = [pyxel.COLOR_RED, pyxel.COLOR_GREEN, pyxel.COLOR_LIGHT_BLUE, pyxel.COLOR_YELLOW]

# Balloon
BALLOON_Y = 160
BALLOON_RADIUS = 18
BALLOON_ENVELOPE_R = 16

# Ring
RING_RADIUS = 14
RING_THICKNESS = 3
COLLIDE_DIST = BALLOON_RADIUS + RING_RADIUS

# Bars
BAR_WIDTH = 60
BAR_HEIGHT = 6

# SUPER LIFT
SUPER_DURATION = 300
SUPER_COMBO_TRIGGER = 5

# Fuel/Heat
FUEL_MAX = 100.0
HEAT_MAX = 100.0
FUEL_BURN_RATE = 0.3
HEAT_BURN_RATE = 0.15
FUEL_BASE_RATE = 0.05
HEAT_DECAY_RATE = 0.05
HEAT_WRONG_COLOR = 15.0
HEAT_SUPER_END = 10.0

# Scroll
SCROLL_BURN = 3.0
SCROLL_PASSIVE = 0.8

# Movement
MOVE_SPEED = 2.0
WIND_CHANGE_INTERVAL_MIN = 120
WIND_CHANGE_INTERVAL_MAX = 180
WIND_MIN = -1.5
WIND_MAX = 1.5
BALLOON_MIN_X = 30
BALLOON_MAX_X = 290

# Spawning
RING_SPAWN_BASE = 45
RING_SPAWN_MIN = 20
RING_SPAWN_Y = 260

# Ring speed
RING_SPEED_BASE = 0.6
RING_SPEED_MAX = 1.5

# Match probability
MATCH_PROB_BASE = 0.35
MATCH_PROB_MIN = 0.15

# Cloud
NUM_CLOUDS = 5

# Particles
PARTICLE_RING_COLLECT = 6
PARTICLE_SUPER_TRIGGER = 20
PARTICLE_WRONG_COLOR = 4

# Rainbow cycle colors for SUPER mode
RAINBOW_CYCLE = [
    pyxel.COLOR_RED,
    pyxel.COLOR_ORANGE,
    pyxel.COLOR_YELLOW,
    pyxel.COLOR_LIME,
    pyxel.COLOR_CYAN,
    pyxel.COLOR_LIGHT_BLUE,
    pyxel.COLOR_PURPLE,
    pyxel.COLOR_PINK,
]
RAINBOW_LEN = len(RAINBOW_CYCLE)


@dataclass
class Ring:
    x: float
    y: float
    color: int
    radius: int = RING_RADIUS
    active: bool = True


@dataclass
class Cloud:
    x: float
    y: float
    width: int
    speed: float


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int
    vy: float = -1.0


class Game:
    def __init__(self) -> None:
        pyxel.init(320, 240, display_scale=2, title="Balloon Surge")
        self._rng: random.Random = random.Random()
        self.phase: Phase = Phase.TITLE
        self.balloon_x: float = 160.0
        self.balloon_color: int = COLOR_RED
        self.fuel: float = FUEL_MAX
        self.heat: float = 0.0
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.altitude: float = 0.0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.rings: list[Ring] = []
        self.clouds: list[Cloud] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.wind: float = 0.0
        self.scroll_offset: float = 0.0
        self.shake_frames: int = 0
        self.frame: int = 0
        self._ring_spawn_timer: int = 0
        self._wind_timer: int = 0
        self.game_over_reason: str = ""
        self._reset()
        pyxel.run(self._update, self._draw)

    # ── Reset ──

    def _reset(self) -> None:
        self.balloon_x = 160.0
        self.balloon_color = self._rng.randint(0, NUM_COLORS - 1)
        self.fuel = FUEL_MAX
        self.heat = 0.0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.altitude = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.rings.clear()
        self.clouds.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.wind = 0.0
        self.scroll_offset = 0.0
        self.shake_frames = 0
        self.frame = 0
        self._ring_spawn_timer = 30
        self._wind_timer = self._rng.randint(WIND_CHANGE_INTERVAL_MIN, WIND_CHANGE_INTERVAL_MAX)
        self.game_over_reason = ""
        self._init_clouds()

    def _init_clouds(self) -> None:
        self.clouds.clear()
        for _ in range(NUM_CLOUDS):
            self.clouds.append(Cloud(
                x=float(self._rng.randint(0, 320)),
                y=float(self._rng.randint(0, 240)),
                width=self._rng.randint(30, 80),
                speed=self._rng.uniform(0.2, 0.6),
            ))

    # ── Update ──

    def _update(self) -> None:
        self.frame += 1

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.PLAYING
                self._reset()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floating_texts()
            self._update_clouds()
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        burning = pyxel.btn(pyxel.KEY_SPACE)
        left = pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A)
        right = pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D)

        # Movement
        if left:
            self.balloon_x -= MOVE_SPEED
        if right:
            self.balloon_x += MOVE_SPEED
        self.balloon_x += self.wind
        self.balloon_x = max(BALLOON_MIN_X, min(BALLOON_MAX_X, self.balloon_x))

        # Fuel/Heat update
        self._update_fuel(burning)

        # Scroll
        can_burn = burning and self.fuel > 0
        scroll_speed = SCROLL_BURN if can_burn else SCROLL_PASSIVE
        self.scroll_offset += scroll_speed
        self.altitude += scroll_speed * 0.1

        # Wind timer
        self._wind_timer -= 1
        if self._wind_timer <= 0:
            self.wind = self._rng.uniform(WIND_MIN, WIND_MAX)
            self._wind_timer = self._rng.randint(WIND_CHANGE_INTERVAL_MIN, WIND_CHANGE_INTERVAL_MAX)

        # Spawn rings
        self._ring_spawn_timer -= 1
        if self._ring_spawn_timer <= 0:
            self._spawn_ring()
            spawn_interval = max(RING_SPAWN_MIN, RING_SPAWN_BASE - int(self.altitude // 500))
            self._ring_spawn_timer = self._rng.randint(spawn_interval, spawn_interval + 10)

        # Update rings
        ring_speed = min(RING_SPEED_MAX, RING_SPEED_BASE + self.altitude * 0.05 / 1000.0)
        for ring in self.rings[:]:
            ring.y -= ring_speed + scroll_speed * 0.3
            if ring.y < -20:
                self.rings.remove(ring)
                continue
            if ring.active:
                dist = math.hypot(self.balloon_x - ring.x, BALLOON_Y - ring.y)
                if dist < COLLIDE_DIST:
                    self._handle_ring_pass(ring)

        # Super mode timer
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0
                self.combo = 0
                self.heat = min(HEAT_MAX, self.heat + HEAT_SUPER_END)

        # Shake decay
        if self.shake_frames > 0:
            self.shake_frames -= 1

        # Heat decay (after game over check)
        self.heat = max(0.0, self.heat - HEAT_DECAY_RATE)

        # Check game over
        self._check_game_over()

        # Particle/text/cloud updates
        self._update_particles()
        self._update_floating_texts()
        self._update_clouds()

    # ── Fuel / Heat ──

    def _update_fuel(self, burning: bool) -> None:
        if self.super_mode:
            return
        if burning and self.fuel > 0:
            self.fuel = max(0.0, self.fuel - FUEL_BURN_RATE)
            self.heat = min(HEAT_MAX, self.heat + HEAT_BURN_RATE)
        else:
            self.fuel = max(0.0, self.fuel - FUEL_BASE_RATE)

    # ── Ring Spawn ──

    def _spawn_ring(self) -> None:
        x = float(self._rng.randint(40, 280))
        # Ensure minimum distance from existing rings
        for _ in range(10):
            too_close = False
            for ring in self.rings:
                if abs(ring.x - x) < 40 and abs(ring.y - RING_SPAWN_Y) < 40:
                    too_close = True
                    break
            if not too_close:
                break
            x = float(self._rng.randint(40, 280))

        # Weighted random color: chance to match balloon_color
        match_prob = max(MATCH_PROB_MIN, MATCH_PROB_BASE - self.altitude * 0.02 / 1000.0)
        if self._rng.random() < match_prob:
            color = self.balloon_color
        else:
            color = self._rng.randint(0, NUM_COLORS - 1)

        self.rings.append(Ring(x=x, y=float(RING_SPAWN_Y), color=color))

    # ── Ring Pass ──

    def _handle_ring_pass(self, ring: Ring) -> None:
        ring.active = False
        gx = ring.x
        gy = ring.y

        is_same_color = ring.color == self.balloon_color

        if self.super_mode or is_same_color:
            self.combo += 1
            points = 10 + self.combo * 5
            if self.super_mode:
                points *= 3
            self.score += points
            self.balloon_color = ring.color
            self._spawn_particles_at(gx, gy, ring.color, PARTICLE_RING_COLLECT)
            self._spawn_floating_text(gx, gy, f"+{points}", RING_PYXEL[ring.color])
            if self.combo >= 2:
                self._spawn_floating_text(gx + 15, gy - 10, f"x{self.combo}", pyxel.COLOR_YELLOW)
        else:
            self.combo = 1
            points = 5
            self.score += points
            self.balloon_color = ring.color
            self.heat = min(HEAT_MAX, self.heat + HEAT_WRONG_COLOR)
            self._spawn_particles_at(gx, gy, ring.color, PARTICLE_WRONG_COLOR)
            self._spawn_floating_text(gx, gy, f"+{points}", pyxel.COLOR_RED)

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        # Trigger SUPER LIFT
        if self.combo >= SUPER_COMBO_TRIGGER and not self.super_mode:
            self._trigger_super()

        if ring in self.rings:
            self.rings.remove(ring)

    def _trigger_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self.shake_frames = 10
        bx = self.balloon_x
        by = BALLOON_Y
        for i in range(PARTICLE_SUPER_TRIGGER):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 4.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = RAINBOW_CYCLE[i % RAINBOW_LEN]
            self.particles.append(Particle(
                x=bx, y=by, vx=vx, vy=vy,
                color=color, life=self._rng.randint(15, 20), size=3,
            ))
        self._spawn_floating_text(bx, by - 25, "SUPER LIFT!", pyxel.COLOR_ORANGE)

    # ── Game Over ──

    def _check_game_over(self) -> None:
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            self.game_over_reason = "Overheated!"
            self.shake_frames = 5
        elif self.fuel <= 0 and self.altitude < 0:
            self.phase = Phase.GAME_OVER
            self.game_over_reason = "Out of fuel!"

    # ── Particle / Text updates ──

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _update_clouds(self) -> None:
        for cloud in self.clouds:
            cloud.x -= cloud.speed
            if cloud.x < -cloud.width:
                cloud.x = 320 + cloud.width
                cloud.y = float(self._rng.randint(20, 200))

    def _spawn_particles_at(self, x: float, y: float, color_idx: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self._rng.randint(8, 15)
            c = RING_PYXEL[color_idx]
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, color=c, life=life))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x - len(text) * 2, y=y, text=text, life=20, color=color))

    # ── Draw ──

    def _draw(self) -> None:
        pyxel.cls(pyxel.COLOR_LIGHT_BLUE)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        # Sky gradient and clouds (shared by PLAYING and GAME_OVER)
        self._draw_sky()
        self._draw_clouds()

        if self.phase == Phase.PLAYING:
            self._draw_rings()
            self._draw_balloon()
            self._draw_particles()
            self._draw_floating_texts()
            self._draw_hud()
        elif self.phase == Phase.GAME_OVER:
            self._draw_rings()
            self._draw_balloon()
            self._draw_particles()
            self._draw_floating_texts()
            self._draw_hud()
            self._draw_game_over()

    def _draw_sky(self) -> None:
        # Simple sky gradient: light blue at top, white at bottom
        for y in range(0, 120):
            pyxel.line(0, y, 320, y, pyxel.COLOR_LIGHT_BLUE)
        for y in range(120, 240):
            pyxel.line(0, y, 320, y, pyxel.COLOR_WHITE)

    def _draw_clouds(self) -> None:
        for cloud in self.clouds:
            cx = int(cloud.x)
            cy = int(cloud.y)
            w = cloud.width
            h = w // 3
            # Simple cloud shape with overlapping circles
            pyxel.circ(cx, cy, h, pyxel.COLOR_WHITE)
            pyxel.circ(cx - w // 4, cy + h // 3, h - 2, pyxel.COLOR_WHITE)
            pyxel.circ(cx + w // 4, cy + h // 3, h - 2, pyxel.COLOR_WHITE)

    def _draw_rings(self) -> None:
        for ring in self.rings:
            if not ring.active:
                continue
            rx = int(ring.x)
            ry = int(ring.y)
            rcolor = RING_PYXEL[ring.color]
            # Pulsing glow
            pulse = int(math.sin(self.frame * 0.1 + ring.x * 0.01) * 2)
            pr = RING_RADIUS + pulse
            # Outer glow
            pyxel.circb(rx, ry, pr, rcolor)
            pyxel.circb(rx, ry, pr - 1, rcolor)
            pyxel.circb(rx, ry, pr - 2, rcolor)

    def _draw_balloon(self) -> None:
        bx = int(self.balloon_x)
        by = BALLOON_Y

        # Screen shake
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)

        bx += shake_x
        by += shake_y

        # Balloon color
        if self.super_mode:
            cycle_index = (self.frame // 4) % RAINBOW_LEN
            balloon_color = RAINBOW_CYCLE[cycle_index]
            # Super glow
            glow_r = BALLOON_ENVELOPE_R + 4
            glow_color = RAINBOW_CYCLE[(cycle_index + RAINBOW_LEN // 2) % RAINBOW_LEN]
            pyxel.circ(bx, by, glow_r, glow_color)
        else:
            balloon_color = BALLOON_PYXEL[self.balloon_color]

        # Envelope
        pyxel.circ(bx, by, BALLOON_ENVELOPE_R, balloon_color)
        # Highlight
        pyxel.circ(bx - 4, by - 4, 4, pyxel.COLOR_WHITE)

        # Ropes
        pyxel.line(bx - 4, by + BALLOON_ENVELOPE_R, bx - 2, by + BALLOON_ENVELOPE_R + 6, pyxel.COLOR_BROWN)
        pyxel.line(bx + 4, by + BALLOON_ENVELOPE_R, bx + 2, by + BALLOON_ENVELOPE_R + 6, pyxel.COLOR_BROWN)

        # Basket
        basket_top = by + BALLOON_ENVELOPE_R + 6
        pyxel.rect(bx - 3, basket_top, 6, 6, pyxel.COLOR_BROWN)
        pyxel.rectb(bx - 3, basket_top, 6, 6, pyxel.COLOR_BLACK)

        # Burner flame
        if pyxel.btn(pyxel.KEY_SPACE) and self.phase == Phase.PLAYING and self.fuel > 0:
            flame_h = self._rng.randint(4, 8)
            pyxel.tri(bx - 3, by + BALLOON_ENVELOPE_R, bx + 3, by + BALLOON_ENVELOPE_R,
                      bx, by + BALLOON_ENVELOPE_R - flame_h, pyxel.COLOR_ORANGE)
            pyxel.tri(bx - 1, by + BALLOON_ENVELOPE_R, bx + 1, by + BALLOON_ENVELOPE_R,
                      bx, by + BALLOON_ENVELOPE_R - flame_h + 2, pyxel.COLOR_YELLOW)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), p.size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        # Score (top-left)
        pyxel.text(4, 4, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        # Altitude
        pyxel.text(4, 14, f"ALT: {int(self.altitude)}m", pyxel.COLOR_WHITE)

        # Combo (top-right)
        combo_color = pyxel.COLOR_YELLOW
        if self.combo >= 3 and (self.frame // 15) % 2 == 0:
            combo_color = pyxel.COLOR_ORANGE
        pyxel.text(260, 4, f"COMBO: x{self.combo}", combo_color)

        # Heat bar
        heat_ratio = self.heat / HEAT_MAX
        heat_fill = int(BAR_WIDTH * heat_ratio)
        bar_x = 256
        bar_y = 16
        pyxel.rect(bar_x, bar_y, BAR_WIDTH, BAR_HEIGHT, pyxel.COLOR_GRAY)
        pyxel.rect(bar_x, bar_y, heat_fill, BAR_HEIGHT, pyxel.COLOR_RED)
        pyxel.text(bar_x - 18, bar_y, "H", pyxel.COLOR_RED)

        # Fuel bar
        fuel_ratio = self.fuel / FUEL_MAX
        fuel_fill = int(BAR_WIDTH * fuel_ratio)
        fuel_bar_y = bar_y + BAR_HEIGHT + 2
        pyxel.rect(bar_x, fuel_bar_y, BAR_WIDTH, BAR_HEIGHT, pyxel.COLOR_GRAY)
        pyxel.rect(bar_x, fuel_bar_y, fuel_fill, BAR_HEIGHT, pyxel.COLOR_YELLOW)
        pyxel.text(bar_x - 18, fuel_bar_y, "F", pyxel.COLOR_YELLOW)

        # SUPER timer
        if self.super_mode:
            remaining = self.super_timer // 60 + 1
            cycle_idx = (self.frame // 4) % RAINBOW_LEN
            sc = RAINBOW_CYCLE[cycle_idx]
            super_text = f"SUPER LIFT! {remaining}s"
            pyxel.text(160 - len(super_text) * 2, 220, super_text, sc)

    def _draw_title(self) -> None:
        # Title with cycling colors
        title = "BALLOON SURGE"
        for i, ch in enumerate(title):
            x = 160 - len(title) * 4 // 2 + i * 4
            c = RAINBOW_CYCLE[(i + self.frame // 8) % RAINBOW_LEN]
            pyxel.text(x, 50, ch, c)

        subtitle = "Color-Match Flight"
        pyxel.text(160 - len(subtitle) * 4 // 2, 68, subtitle, pyxel.COLOR_WHITE)

        instructions = [
            ("LEFT/RIGHT  -- Steer", pyxel.COLOR_LIGHT_BLUE),
            ("SPACE  -- Burn Fuel (Rise)", pyxel.COLOR_YELLOW),
            ("Match ring color for COMBO!", pyxel.COLOR_GREEN),
        ]
        y = 100
        for text, color in instructions:
            pyxel.text(160 - len(text) * 4 // 2, y, text, color)
            y += 18

        # Blinking start prompt
        if (self.frame // 30) % 2 == 0:
            prompt = "Press SPACE to Start"
            pyxel.text(160 - len(prompt) * 4 // 2, 180, prompt, pyxel.COLOR_WHITE)

    def _draw_game_over(self) -> None:
        # Dim overlay
        for y in range(0, 240, 2):
            pyxel.line(0, y, 320, y, pyxel.COLOR_BLACK)
        # Actually, use rect with transparency isn't available. Let's use a darker overlay pattern
        # Just draw text on top directly
        pyxel.text(160 - 30, 60, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(160 - 40, 85, f"Score: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(160 - 48, 105, f"Max Combo: x{self.max_combo}", pyxel.COLOR_YELLOW)
        pyxel.text(160 - 44, 125, f"Altitude: {int(self.altitude)}m", pyxel.COLOR_LIGHT_BLUE)

        reason = self.game_over_reason if self.game_over_reason else "Overheated!"
        pyxel.text(160 - len(reason) * 4 // 2, 150, reason, pyxel.COLOR_ORANGE)

        # Altitude bonus
        alt_bonus = int(self.altitude / 100)
        pyxel.text(160 - 48, 170, f"Altitude Bonus: +{alt_bonus}", pyxel.COLOR_WHITE)

        if (self.frame // 30) % 2 == 0:
            prompt = "Press SPACE to Retry"
            pyxel.text(160 - len(prompt) * 4 // 2, 200, prompt, pyxel.COLOR_WHITE)


if __name__ == "__main__":
    Game()
