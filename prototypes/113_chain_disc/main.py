import random
import pyxel
from dataclasses import dataclass
from enum import Enum, auto


class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    FLYING = auto()
    RESOLVE = auto()
    GAME_OVER = auto()


@dataclass
class Basket:
    x: float
    y: float
    color: int  # 8, 3, 5, 10
    value: int  # base score value
    radius: int = 12


@dataclass
class Obstacle:
    x: int  # grid position (not pixel)
    y: int
    radius: int = 6  # pixel radius for collision


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


BASKET_COLORS: tuple[int, ...] = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW


class Game:
    # Key constants
    MAX_HEAT: float = 10.0
    HEAT_PER_MISS: float = 2.0
    HEAT_DECAY: float = 0.01  # per frame
    DISC_SPEED: float = 4.0
    MAX_FLY_FRAMES: int = 60
    SUPER_DURATION: int = 150  # 5 seconds
    COMBO_FOR_SUPER: int = 4
    TIMER_FRAMES: int = 2700  # 90 seconds
    OBSTACLE_CELL: int = 8  # cell size for obstacle grid
    OBSTACLE_GRID_W: int = 40  # 320/8
    OBSTACLE_GRID_H: int = 30  # 240/8
    OBSTACLE_PIXEL_R: int = 4  # obstacle collision radius (pixel)
    BASKET_RADIUS: int = 14
    PLAYER_RADIUS: int = 6
    DISC_RADIUS: int = 4

    def __init__(self) -> None:
        pyxel.init(320, 240, "Chain Disc", display_scale=2)
        self._rng: random.Random = random.Random()
        self._init_state()
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player_x: float = 160.0
        self.player_y: float = 120.0
        self.disc_x: float = 0.0
        self.disc_y: float = 0.0
        self.disc_active: bool = False
        self.disc_vx: float = 0.0
        self.disc_vy: float = 0.0
        self.disc_color: int = 8  # RED — default disc color
        self.aim_start_x: float = 0.0
        self.aim_start_y: float = 0.0
        self.aim_end_x: float = 0.0
        self.aim_end_y: float = 0.0
        self.is_aiming: bool = False
        self.baskets: list[Basket] = self._spawn_initial_baskets()
        self.obstacles: list[Obstacle] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = self.TIMER_FRAMES
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.particles: list[Particle] = []
        self.last_basket_color: int = -1  # -1 means no combo active (any color hits)
        self.flying_basket_hit: Basket | None = None
        self._flying_frames: int = 0
        self._ca_timer: int = 0
        self._resolve_timer: int = 0

    def _spawn_initial_baskets(self) -> list[Basket]:
        colors = list(BASKET_COLORS)
        baskets: list[Basket] = []
        positions: list[tuple[float, float]] = [
            (80.0, 60.0),
            (240.0, 60.0),
            (80.0, 180.0),
            (240.0, 180.0),
        ]
        for i, (x, y) in enumerate(positions):
            c = colors[i % len(colors)]
            baskets.append(Basket(x=x, y=y, color=c, value=c))
        return baskets

    def _make_random_basket(self) -> Basket:
        c = self._rng.choice(BASKET_COLORS)
        x = float(self._rng.randint(40, 280))
        y = float(self._rng.randint(40, 200))
        return Basket(x=x, y=y, color=c, value=c)

    def _start_aim(self, mx: float, my: float) -> None:
        self.is_aiming = True
        self.aim_start_x = self.player_x
        self.aim_start_y = self.player_y
        self.aim_end_x = mx
        self.aim_end_y = my

    def _update_aim(self, mx: float, my: float) -> None:
        self.aim_end_x = mx
        self.aim_end_y = my

    def _release_throw(self) -> None:
        dx = self.aim_end_x - self.aim_start_x
        dy = self.aim_end_y - self.aim_start_y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1.0:
            dist = 1.0
        power = min(dist / 120.0, 2.0)
        speed = self.DISC_SPEED * power
        self.disc_vx = (dx / dist) * speed
        self.disc_vy = (dy / dist) * speed
        self.disc_x = self.player_x
        self.disc_y = self.player_y
        self.disc_active = True
        self._flying_frames = 0
        self.flying_basket_hit = None
        self.is_aiming = False
        self.phase = Phase.FLYING

    def _update_flying(self) -> None:
        self.disc_x += self.disc_vx
        self.disc_y += self.disc_vy
        self._flying_frames += 1

        # Edge bounce
        if self.disc_x < 0:
            self.disc_x = 0
            self.disc_vx = abs(self.disc_vx)
        elif self.disc_x > 320:
            self.disc_x = 320
            self.disc_vx = -abs(self.disc_vx)
        if self.disc_y < 0:
            self.disc_y = 0
            self.disc_vy = abs(self.disc_vy)
        elif self.disc_y > 240:
            self.disc_y = 240
            self.disc_vy = -abs(self.disc_vy)

        # Obstacle collision (skip in super mode — pierce)
        if not self.super_mode:
            if self._check_obstacle_collision(self.disc_x, self.disc_y) is not None:
                self._enter_resolve(None)
                return

        # Basket collision
        hit_basket = self._check_basket_collision(self.disc_x, self.disc_y)
        if hit_basket is not None:
            self._enter_resolve(hit_basket)
            return

        # Max fly frames
        if self._flying_frames >= self.MAX_FLY_FRAMES:
            self._enter_resolve(None)

    def _enter_resolve(self, hit_basket: Basket | None) -> None:
        self.disc_active = False
        self.flying_basket_hit = hit_basket
        self._resolve_throw(hit_basket)
        self._resolve_timer = 15
        self.phase = Phase.RESOLVE

    def _check_basket_collision(self, disc_x: float, disc_y: float) -> Basket | None:
        threshold = self.BASKET_RADIUS + self.DISC_RADIUS
        for basket in self.baskets:
            dx = disc_x - basket.x
            dy = disc_y - basket.y
            if (dx * dx + dy * dy) < threshold * threshold:
                return basket
        return None

    def _check_obstacle_collision(self, disc_x: float, disc_y: float) -> Obstacle | None:
        threshold = self.OBSTACLE_PIXEL_R + self.DISC_RADIUS
        half = self.OBSTACLE_CELL // 2
        for obs in self.obstacles:
            ox = obs.x * self.OBSTACLE_CELL + half
            oy = obs.y * self.OBSTACLE_CELL + half
            dx = disc_x - ox
            dy = disc_y - oy
            if (dx * dx + dy * dy) < threshold * threshold:
                return obs
        return None

    def _resolve_throw(self, hit_basket: Basket | None) -> None:
        if hit_basket is not None:
            # Check color match: first hit (-1) matches any; thereafter must match last color
            if self.last_basket_color == -1 or hit_basket.color == self.last_basket_color:
                self.combo += 1
                self.last_basket_color = hit_basket.color
                self.disc_color = hit_basket.color
                multiplier = 3 if self.super_mode else 1
                self.score += hit_basket.value * self.combo * multiplier
                if self.combo > self.max_combo:
                    self.max_combo = self.combo

                # Super mode unlock
                if self.combo >= self.COMBO_FOR_SUPER and not self.super_mode:
                    self.super_mode = True
                    self.super_timer = self.SUPER_DURATION

                # Particles
                if self.super_mode:
                    self._spawn_super_particles(hit_basket.x, hit_basket.y)
                else:
                    self._spawn_particles(hit_basket.x, hit_basket.y, hit_basket.color, 8)

                # Move player to basket, remove hit basket, spawn replacement
                self.player_x = hit_basket.x
                self.player_y = hit_basket.y
                self.baskets.remove(hit_basket)
                self.baskets.append(self._make_random_basket())
            else:
                # Wrong color — combo break
                self.combo = 0
                self.last_basket_color = -1
                self.disc_color = hit_basket.color
                self.heat += self.HEAT_PER_MISS
                self._spawn_particles(hit_basket.x, hit_basket.y, 13, 4)
                self.player_x = hit_basket.x
                self.player_y = hit_basket.y
                self.baskets.remove(hit_basket)
                self.baskets.append(self._make_random_basket())
        else:
            # Miss — disc hit obstacle or expired
            self.combo = 0
            self.last_basket_color = -1
            self.heat += self.HEAT_PER_MISS
            self._spawn_particles(self.disc_x, self.disc_y, 13, 3)

        # CA-style obstacle spread after every throw
        self._spread_obstacles()

    def _spread_obstacles(self) -> None:
        occupied: set[tuple[int, int]] = {(o.x, o.y) for o in self.obstacles}
        new_obs: list[Obstacle] = []
        for obs in self.obstacles:
            if self._rng.random() < 0.3:
                dirs: list[tuple[int, int]] = [(0, 1), (1, 0), (0, -1), (-1, 0)]
                self._rng.shuffle(dirs)
                for dx, dy in dirs:
                    nx = obs.x + dx
                    ny = obs.y + dy
                    if 0 <= nx < self.OBSTACLE_GRID_W and 0 <= ny < self.OBSTACLE_GRID_H:
                        if (nx, ny) not in occupied:
                            new_obs.append(Obstacle(x=nx, y=ny))
                            occupied.add((nx, ny))
                            break
        self.obstacles.extend(new_obs)

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-2.0, 2.0)
            life = self._rng.randint(15, 30)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _spawn_super_particles(self, x: float, y: float) -> None:
        colors = list(BASKET_COLORS)
        for _ in range(20):
            c = self._rng.choice(colors)
            vx = self._rng.uniform(-3.0, 3.0)
            vy = self._rng.uniform(-3.0, 3.0)
            life = self._rng.randint(20, 40)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=c))

    def _update_particles(self) -> None:
        surviving: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                surviving.append(p)
        self.particles = surviving

    def _update_timer(self) -> None:
        if self.timer > 0:
            self.timer -= 1
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

    # ------------------------------------------------------------------ #
    #  Pyxel Hooks
    # ------------------------------------------------------------------ #

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._init_state()
                self.phase = Phase.AIMING

        elif self.phase == Phase.AIMING:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._start_aim(float(pyxel.mouse_x), float(pyxel.mouse_y))
            if self.is_aiming:
                self._update_aim(float(pyxel.mouse_x), float(pyxel.mouse_y))
                if not pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
                    self._release_throw()
            self._update_timer()
            self._update_particles()
            if self.heat >= self.MAX_HEAT or self.timer <= 0:
                self.phase = Phase.GAME_OVER

        elif self.phase == Phase.FLYING:
            if self.disc_active:
                self._update_flying()
            self._update_timer()
            # Timer or heat check deferred to RESOLVE

        elif self.phase == Phase.RESOLVE:
            self._resolve_timer -= 1
            self._update_particles()
            self._update_timer()
            if self._resolve_timer <= 0:
                if self.heat >= self.MAX_HEAT or self.timer <= 0:
                    self.phase = Phase.GAME_OVER
                else:
                    self.phase = Phase.AIMING
                    self.is_aiming = False

        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._init_state()
                self.phase = Phase.AIMING

    def draw(self) -> None:
        pyxel.cls(0)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.AIMING, Phase.FLYING, Phase.RESOLVE):
            self._draw_field()
            self._draw_hud()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(120, 50, "CHAIN DISC", 7)
        pyxel.text(60, 80, "Click or press ENTER to start", 7)
        pyxel.text(40, 110, "Click-Drag-Release: aim & throw", 13)
        pyxel.text(40, 130, "Hit same-color baskets for COMBO chain", 7)
        pyxel.text(40, 150, "COMBO x4 = SUPER DISC (pierce + 3x score)", 14)
        pyxel.text(40, 175, "Wrong color or miss = HEAT up", 8)
        pyxel.text(80, 200, "Survive 90s — keep HEAT low!", 7)

    def _draw_field(self) -> None:
        # Obstacles
        for obs in self.obstacles:
            px = obs.x * self.OBSTACLE_CELL
            py = obs.y * self.OBSTACLE_CELL
            pyxel.rect(px, py, self.OBSTACLE_CELL, self.OBSTACLE_CELL, 4)

        # Baskets
        for basket in self.baskets:
            pyxel.circb(int(basket.x), int(basket.y), self.BASKET_RADIUS, basket.color)
            pyxel.circ(int(basket.x), int(basket.y), self.BASKET_RADIUS - 3, basket.color)
            # Show value text centered
            val_str = str(basket.value)
            pyxel.text(int(basket.x) - len(val_str) * 2, int(basket.y) - 2, val_str, 7)

        # Player
        pc = 14 if self.super_mode else 7
        pyxel.circ(int(self.player_x), int(self.player_y), self.PLAYER_RADIUS, pc)

        # Aim line (dashed)
        if self.phase == Phase.AIMING and self.is_aiming:
            sx = int(self.aim_start_x)
            sy = int(self.aim_start_y)
            ex = int(self.aim_end_x)
            ey = int(self.aim_end_y)
            dx = ex - sx
            dy = ey - sy
            steps = max(1, int((dx * dx + dy * dy) ** 0.5))
            for i in range(0, steps, 6):
                t = i / steps
                px = int(sx + dx * t)
                py = int(sy + dy * t)
                pyxel.pset(px, py, 13)

        # Flying disc
        if self.phase == Phase.FLYING and self.disc_active:
            dc = 14 if self.super_mode else self.disc_color
            pyxel.circ(int(self.disc_x), int(self.disc_y), self.DISC_RADIUS, dc)

        # Particles
        for p in self.particles:
            alpha = p.life / 30.0
            if alpha > 0:
                pyxel.pset(int(p.x), int(p.y), p.color)

        # SUPER mode screen border flash
        if self.super_mode:
            if (pyxel.frame_count // 4) % 2 == 0:
                pyxel.rectb(0, 0, 320, 240, 14)
            pyxel.text(int(self.player_x) - 12, int(self.player_y) - 18, "SUPER", 14)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)
        sec = max(0, self.timer // 30)
        pyxel.text(270, 4, f"{sec}", 7)

        # Combo
        combo_str = f"COMBO: x{self.combo}"
        if self.combo >= self.COMBO_FOR_SUPER:
            combo_str += " SUPER!"
        pyxel.text(4, 224, combo_str, 7)

        # Heat bar
        bar_w = 100
        bar_x = 200
        bar_y = 224
        fill = int(min(1.0, self.heat / self.MAX_HEAT) * bar_w)
        if self.heat < self.MAX_HEAT * 0.4:
            hc = 3
        elif self.heat < self.MAX_HEAT * 0.7:
            hc = 9
        else:
            hc = 8
        pyxel.rectb(bar_x, bar_y, bar_w + 2, 6, 13)
        if fill > 0:
            pyxel.rect(bar_x + 1, bar_y + 1, fill, 4, hc)
        pyxel.text(bar_x - 16, bar_y, "HT", 7)

    def _draw_game_over(self) -> None:
        pyxel.text(120, 60, "GAME OVER", 8)
        pyxel.text(100, 100, f"SCORE: {self.score}", 7)
        pyxel.text(90, 120, f"MAX COMBO: x{self.max_combo}", 7)
        pyxel.text(80, 160, "Click to retry", 7)


# ------------------------------------------------------------------ #
#  Headless test factory
# ------------------------------------------------------------------ #

def _make_game() -> Game:
    """Factory for headless tests — bypasses pyxel.init/run."""
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.player_x = 160.0
    g.player_y = 120.0
    g.disc_x = 0.0
    g.disc_y = 0.0
    g.disc_active = False
    g.disc_vx = 0.0
    g.disc_vy = 0.0
    g.disc_color = 8
    g.aim_start_x = 0.0
    g.aim_start_y = 0.0
    g.aim_end_x = 0.0
    g.aim_end_y = 0.0
    g.is_aiming = False
    g.baskets = []
    g.obstacles = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = 2700
    g.super_mode = False
    g.super_timer = 0
    g.particles = []
    g.last_basket_color = -1
    g.flying_basket_hit = None
    g._flying_frames = 0
    g._rng = random.Random(42)
    g._ca_timer = 0
    g._resolve_timer = 0
    g._init_state()
    return g


if __name__ == "__main__":
    Game()
