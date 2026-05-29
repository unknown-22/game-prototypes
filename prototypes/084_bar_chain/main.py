from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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

POUR_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
POUR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]
NUM_BOTTLES: int = 4

MAX_HEAT: int = 10
HEAT_DECAY_ON_SERVE: int = 2
MAX_TARGET_COLORS: int = 4

ORDER_BASE_TIMER: int = 300
ORDER_MIN_TIMER: int = 180
ORDER_TIMER_STEP: int = 30

SCORE_CORRECT_BASE: int = 10
SCORE_EXTRA_BASE: int = 5
SCORE_COMPLETION_BONUS_MULT: int = 50
SCORE_HEAT_PENALTY: int = 20

WIDTH: int = 320
HEIGHT: int = 240

# Layout
ORDER_Y: int = 0
ORDER_H: int = 30
GLASS_X: int = 100
GLASS_Y: int = 40
GLASS_W: int = 120
GLASS_H: int = 100
GLASS_INNER_PAD: int = 4
MESSAGE_Y: int = 150
MESSAGE_H: int = 20
BOTTLE_Y: int = 180
BOTTLE_W: int = 55
BOTTLE_H: int = 30
BOTTLE_GAP: int = 10
BOTTLE_START_X: int = (WIDTH - (BOTTLE_W * NUM_BOTTLES + BOTTLE_GAP * (NUM_BOTTLES - 1))) // 2
SERVE_Y: int = 218
SERVE_W: int = 80
SERVE_H: int = 18
SERVE_X: int = (WIDTH - SERVE_W) // 2
HUD_Y: int = 236
HUD_HEIGHT: int = 4


class Phase(Enum):
    TITLE = auto()
    ORDER_APPEAR = auto()
    POURING = auto()
    SERVE_ANIM = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Order:
    target_colors: list[int]
    reward_base: int = 100
    time_limit: int = 300
    timer: int = 300


@dataclass
class PourRecord:
    color: int
    combo: int
    is_correct: bool


@dataclass
class Particle:
    x: float
    y: float
    dx: float
    dy: float
    color: int
    life: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------


class Game:
    def __init__(self) -> None:
        self._init_state()

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.heat: int = 0
        self.max_heat: int = MAX_HEAT
        self.combo: int = 0
        self.max_combo: int = 0
        self.order: Order | None = None
        self.pours: list[PourRecord] = []
        self.last_color: int | None = None
        self.serve_ready: bool = False
        self.serve_flash_timer: int = 0
        self.frame_timer: int = 0
        self.game_over: bool = False
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._round: int = 0
        self._order_appear_timer: int = 0
        self._serve_anim_timer: int = 0
        self._order_matched: int = 0
        self._rng: random.Random = random.Random()
        self._title_flash: int = 0

    def reset(self) -> None:
        self._init_state()

    # ------------------------------------------------------------------
    # Order generation
    # ------------------------------------------------------------------

    def _get_difficulty(self) -> tuple[int, int]:
        if self._round <= 3:
            return 2, 300
        elif self._round <= 6:
            return 3, 270
        else:
            return 4, 240

    def _generate_order(self) -> Order:
        num_colors, time_limit = self._get_difficulty()
        colors = [
            self._rng.choice(POUR_COLORS) for _ in range(num_colors)
        ]
        return Order(
            target_colors=colors,
            reward_base=100,
            time_limit=time_limit,
            timer=time_limit,
        )

    # ------------------------------------------------------------------
    # Pour logic
    # ------------------------------------------------------------------

    def _pour(self, color: int) -> bool:
        """Pour a color. Returns True if pour was accepted."""
        if self.order is None:
            return False

        target_colors = self.order.target_colors
        in_target_set = color in set(target_colors)

        if self._order_matched < len(target_colors):
            if color == target_colors[self._order_matched]:
                is_correct = True
                self._order_matched += 1
            elif in_target_set:
                is_correct = True
            else:
                is_correct = False
        else:
            is_correct = in_target_set

        if self.last_color == color:
            self.combo += 1
        else:
            self.combo = 1

        self.last_color = color
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        record = PourRecord(color=color, combo=self.combo, is_correct=is_correct)
        self.pours.append(record)

        if not is_correct:
            self.heat += 1
            self._spawn_floating_text(
                "HEAT +1",
                ORANGE,
            )
            if self.heat >= MAX_HEAT:
                self._trigger_game_over()
                return True

        self._spawn_pour_particles(color)

        self._check_serve_ready()

        return True

    def _check_serve_ready(self) -> None:
        if self.order is None:
            self.serve_ready = False
            return
        self.serve_ready = self._order_matched >= len(self.order.target_colors)

    def _can_serve(self) -> bool:
        return self.serve_ready

    # ------------------------------------------------------------------
    # Serve logic
    # ------------------------------------------------------------------

    def _serve(self) -> int:
        """Calculate and return the score for the current glass."""
        if self.order is None:
            return 0

        target_colors = self.order.target_colors.copy()
        total_score = 0
        heat_penalty = 0
        extra_count = 0

        for pour in self.pours:
            if target_colors and pour.color == target_colors[0] and pour.is_correct:
                target_colors.pop(0)
                total_score += SCORE_CORRECT_BASE * pour.combo
            elif pour.is_correct:
                extra_count += 1
                total_score += SCORE_EXTRA_BASE * pour.combo
            else:
                heat_penalty += SCORE_HEAT_PENALTY * pour.combo

        if len(target_colors) == 0:
            total_score += len(self.order.target_colors) * SCORE_COMPLETION_BONUS_MULT

        total_score -= heat_penalty

        if self.heat > 0:
            self.heat = max(0, self.heat - HEAT_DECAY_ON_SERVE)

        if total_score < 0:
            total_score = 0

        self.score += total_score

        self.pours.clear()
        self.last_color = None
        self.combo = 0
        self.serve_ready = False
        self._order_matched = 0
        self.order = None

        if total_score > 0:
            text = f"+{total_score}"
            col = YELLOW if total_score >= 200 else WHITE
            self._spawn_floating_text(text, col)

        return total_score

    # ------------------------------------------------------------------
    # Order timer
    # ------------------------------------------------------------------

    def _update_order_timer(self) -> bool:
        """Decrements timer. Returns True if timer expired."""
        if self.order is None:
            return False
        if self.order.timer > 0:
            self.order.timer -= 1
            return False
        return True

    def _handle_order_timeout(self) -> None:
        self.heat = min(MAX_HEAT, self.heat + 2)
        self._spawn_floating_text("TIME UP! HEAT+2", RED)
        if self.heat >= MAX_HEAT:
            self._trigger_game_over()
            return
        self.order = None
        self.pours.clear()
        self.last_color = None
        self.combo = 0
        self.serve_ready = False
        self._order_matched = 0

    # ------------------------------------------------------------------
    # Heat / Game Over
    # ------------------------------------------------------------------

    def _update_heat(self) -> bool:
        """Check if heat has reached threshold. Returns True if game over."""
        if self.heat >= MAX_HEAT:
            self.game_over = True
            return True
        return False

    def _trigger_game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        self.game_over = True
        self.serve_ready = False

    # ------------------------------------------------------------------
    # Phase transitions
    # ------------------------------------------------------------------

    def _start_order(self) -> None:
        self._round += 1
        self.order = self._generate_order()
        self.pours.clear()
        self.last_color = None
        self.combo = 0
        self.serve_ready = False
        self._order_matched = 0
        self.phase = Phase.ORDER_APPEAR
        self._order_appear_timer = 15  # ~0.5s at 30fps

    def _begin_serve_animation(self) -> None:
        self.phase = Phase.SERVE_ANIM
        self._serve_anim_timer = 20
        self._serve()
        self._spawn_serve_particles()

    # ------------------------------------------------------------------
    # Update helpers
    # ------------------------------------------------------------------

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.dx
            p.y += p.dy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.6
            ft.life -= 1
        self.floating_texts = [
            ft for ft in self.floating_texts if ft.life > 0
        ]

    # ------------------------------------------------------------------
    # Particle spawning
    # ------------------------------------------------------------------

    def _spawn_pour_particles(self, color: int) -> None:
        cx = GLASS_X + GLASS_W // 2
        cy = GLASS_Y + GLASS_H - 10
        count = self.combo * 3
        for _ in range(min(count, 30)):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.0)
            self.particles.append(
                Particle(
                    x=float(cx),
                    y=float(cy),
                    dx=math.cos(angle) * speed,
                    dy=math.sin(angle) * speed - 1.0,
                    color=color,
                    life=self._rng.randint(8, 18),
                )
            )

    def _spawn_serve_particles(self) -> None:
        cx = GLASS_X + GLASS_W // 2
        cy = GLASS_Y + GLASS_H // 2
        for _ in range(20):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=float(cx),
                    y=float(cy),
                    dx=math.cos(angle) * speed,
                    dy=math.sin(angle) * speed,
                    color=YELLOW,
                    life=self._rng.randint(10, 25),
                )
            )

    def _spawn_floating_text(self, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(
                x=float(WIDTH // 2),
                y=float(MESSAGE_Y + 10),
                text=text,
                color=color,
                life=30,
            )
        )

    # ------------------------------------------------------------------
    # Bottle click detection
    # ------------------------------------------------------------------

    def _bottle_at_mouse(self, mx: int, my: int) -> int | None:
        for i in range(NUM_BOTTLES):
            bx = BOTTLE_START_X + i * (BOTTLE_W + BOTTLE_GAP)
            if bx <= mx <= bx + BOTTLE_W and BOTTLE_Y <= my <= BOTTLE_Y + BOTTLE_H:
                return i
        return None

    def _serve_button_hit(self, mx: int, my: int) -> bool:
        return (
            SERVE_X <= mx <= SERVE_X + SERVE_W
            and SERVE_Y <= my <= SERVE_Y + SERVE_H
        )

    # ------------------------------------------------------------------
    # Phase-specific updates
    # ------------------------------------------------------------------

    def update_title(self) -> None:
        self._title_flash += 1
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_order()

    def update_order_appear(self) -> None:
        self._order_appear_timer -= 1
        if self._order_appear_timer <= 0:
            self.phase = Phase.POURING

    def update_pouring(self) -> None:
        self._update_particles()
        self._update_floating_texts()

        if self._update_order_timer():
            self._handle_order_timeout()
            if self.phase == Phase.GAME_OVER:
                return
            self._start_order()
            return

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y

            bottle_idx = self._bottle_at_mouse(mx, my)
            if bottle_idx is not None:
                self._pour(POUR_COLORS[bottle_idx])
                return

            if self.serve_ready and self._serve_button_hit(mx, my):
                self._begin_serve_animation()

    def update_serve_anim(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        self._serve_anim_timer -= 1
        if self._serve_anim_timer <= 0:
            self._start_order()

    def update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_R):
            self.reset()
            self._start_order()

    # ------------------------------------------------------------------
    # Global update
    # ------------------------------------------------------------------

    def update(self) -> None:
        self.frame_timer += 1

        match self.phase:
            case Phase.TITLE:
                self.update_title()
            case Phase.ORDER_APPEAR:
                self.update_order_appear()
            case Phase.POURING:
                self.update_pouring()
            case Phase.SERVE_ANIM:
                self.update_serve_anim()
            case Phase.GAME_OVER:
                self.update_game_over()

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _draw_order(self) -> None:
        pyxel.rect(0, ORDER_Y, WIDTH, ORDER_H, NAVY)
        pyxel.line(0, ORDER_H, WIDTH, ORDER_H, GRAY)

        if self.order is None:
            return

        target_colors = self.order.target_colors.copy()
        target_matched: list[bool] = []
        for pour in self.pours:
            if target_colors and pour.color == target_colors[0] and pour.is_correct:
                target_colors.pop(0)
                target_matched.append(True)
            else:
                target_matched.append(False)

        remaining = self.order.target_colors.copy()
        for pour in self.pours:
            if remaining and pour.color == remaining[0] and pour.is_correct:
                remaining.pop(0)

        square_size = 12
        gap = 4
        start_x = 10
        for i, color in enumerate(self.order.target_colors):
            x = start_x + i * (square_size + gap)
            y = ORDER_Y + (ORDER_H - square_size) // 2
            is_remaining = i >= len(self.order.target_colors) - len(remaining)
            if is_remaining:
                pyxel.rectb(x, y, square_size, square_size, color)
            else:
                pyxel.rect(x, y, square_size, square_size, color)
                pyxel.rectb(x, y, square_size, square_size, WHITE)

        # Timer bar
        if self.order.timer > 0:
            timer_ratio = self.order.timer / max(self.order.time_limit, 1)
            timer_x = 100
            timer_y = ORDER_Y + ORDER_H - 6
            timer_w = 210
            timer_h = 4
            pyxel.rect(timer_x, timer_y, timer_w, timer_h, NAVY)
            fill_w = int(timer_w * timer_ratio)
            timer_col = GREEN if timer_ratio > 0.5 else (ORANGE if timer_ratio > 0.25 else RED)
            pyxel.rect(timer_x, timer_y, fill_w, timer_h, timer_col)

    def _draw_glass(self) -> None:
        pyxel.rectb(GLASS_X, GLASS_Y, GLASS_W, GLASS_H, WHITE)

        pour_h = (GLASS_H - GLASS_INNER_PAD * 2) // max(MAX_TARGET_COLORS + 4, 1)
        pour_h = min(pour_h, 10)

        max_visible = (GLASS_H - GLASS_INNER_PAD * 2) // pour_h
        visible_pours = self.pours[-max_visible:] if len(self.pours) > max_visible else self.pours

        for i, pour in enumerate(visible_pours):
            x = GLASS_X + GLASS_INNER_PAD
            y = GLASS_Y + GLASS_H - GLASS_INNER_PAD - (i + 1) * pour_h
            w = GLASS_W - GLASS_INNER_PAD * 2
            pyxel.rect(x, y, w, pour_h, pour.color)

        if not self.pours:
            pyxel.text(GLASS_X + GLASS_W // 2 - 25, GLASS_Y + GLASS_H // 2, "Empty Glass", GRAY)

    def _draw_combo(self) -> None:
        if self.combo <= 1:
            return

        combo_x = GLASS_X + GLASS_W + 15
        combo_y = GLASS_Y + 20
        size = 1.0
        if self.combo >= 4:
            size = 1.0 + math.sin(pyxel.frame_count * 0.15) * 0.3
        combo_col = WHITE
        if self.combo >= 5:
            combo_col = YELLOW
        elif self.combo >= 3:
            combo_col = CYAN

        if size > 1.0:
            sx = combo_x + 10
            sy = combo_y + 10
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if dx == 0 and dy == 0:
                        continue
                    pyxel.text(
                        sx + dx,
                        sy + dy,
                        f"x{self.combo}",
                        combo_col,
                    )
        pyxel.text(combo_x + 10, combo_y + 10, f"x{self.combo}", combo_col)
        pyxel.text(combo_x + 5, combo_y, "COMBO", GRAY)

    def _draw_message(self) -> None:
        if self.combo > 1:
            msg = f"COMBO x{self.combo}"
            col = YELLOW if self.combo >= 5 else CYAN
            pyxel.text(WIDTH // 2 - len(msg) * 2, MESSAGE_Y, msg, col)

    def _draw_bottles(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        for i, color in enumerate(POUR_COLORS):
            bx = BOTTLE_START_X + i * (BOTTLE_W + BOTTLE_GAP)
            hover = (
                BOTTLE_START_X + i * (BOTTLE_W + BOTTLE_GAP) <= mx <= BOTTLE_START_X + i * (BOTTLE_W + BOTTLE_GAP) + BOTTLE_W
                and BOTTLE_Y <= my <= BOTTLE_Y + BOTTLE_H
            )

            body_col = color if not hover else WHITE
            neck_x = bx + BOTTLE_W // 2 - 8
            neck_w = 16
            neck_h = 8
            neck_y = BOTTLE_Y - neck_h

            pyxel.rect(neck_x, neck_y, neck_w, neck_h, GRAY)
            pyxel.rect(bx, BOTTLE_Y, BOTTLE_W, BOTTLE_H, body_col)
            pyxel.rectb(bx, BOTTLE_Y, BOTTLE_W, BOTTLE_H, WHITE)

            label_y = BOTTLE_Y + BOTTLE_H // 2 - 4
            label_text = POUR_NAMES[i][:3]
            label_col = BLACK if color in (YELLOW, WHITE) else WHITE
            pyxel.text(bx + BOTTLE_W // 2 - len(label_text) * 2, label_y, label_text, label_col)

    def _draw_serve_button(self) -> None:
        btn_col = LIME if self.serve_ready else GRAY
        txt_col = WHITE if self.serve_ready else DARK_BLUE
        pyxel.rectb(SERVE_X, SERVE_Y, SERVE_W, SERVE_H, btn_col)
        label = "SERVE"
        pyxel.text(SERVE_X + SERVE_W // 2 - len(label) * 2, SERVE_Y + SERVE_H // 2 - 4, label, txt_col)

        if self.serve_ready and (pyxel.frame_count // 15) % 2 == 0:
            pyxel.rectb(SERVE_X - 1, SERVE_Y - 1, SERVE_W + 2, SERVE_H + 2, YELLOW)

    def _draw_hud(self) -> None:
        pyxel.rect(0, HUD_Y, WIDTH, HUD_HEIGHT, NAVY)

        pyxel.text(4, HUD_Y + 0, f"SCORE: {self.score}", WHITE)

        heat_bar_x = 120
        heat_label = f"HEAT: {self.heat}/{MAX_HEAT}"
        pyxel.text(heat_bar_x - 3, HUD_Y + 0, heat_label, ORANGE)

        bar_x = 210
        bar_w = 100
        bar_h = 4
        pyxel.rect(bar_x, HUD_Y + 0, bar_w, bar_h, DARK_BLUE)
        fill = int(bar_w * self.heat / MAX_HEAT)
        heat_color = RED if self.heat >= 7 else (ORANGE if self.heat >= 4 else YELLOW)
        pyxel.rect(bar_x, HUD_Y + 0, fill, bar_h, heat_color)
        pyxel.rectb(bar_x, HUD_Y + 0, bar_w, bar_h, GRAY)

    # ------------------------------------------------------------------
    # Phase-specific draws
    # ------------------------------------------------------------------

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)

        pyxel.text(110, 40, "BAR CHAIN", WHITE)
        pyxel.text(60, 60, "A Bartending Chain Game", GRAY)

        pyxel.text(95, 90, "Pour colored liquids", WHITE)
        pyxel.text(80, 105, "Match customer orders", WHITE)
        pyxel.text(72, 120, "Chain same colors for COMBO!", CYAN)

        if (self._title_flash // 20) % 2 == 0:
            pyxel.text(110, 150, "Click to Start", YELLOW)

        pyxel.text(70, 180, "Controls:", GRAY)
        pyxel.text(70, 195, "Click bottles to pour", GRAY)
        pyxel.text(70, 210, "Click SERVE when order complete", GRAY)
        pyxel.text(70, 225, "R = Restart anytime", GRAY)

    def _draw_order_appear(self) -> None:
        self._draw_game_base()
        if self.order is not None:
            names = [POUR_NAMES[POUR_COLORS.index(c)] for c in self.order.target_colors]
            order_text = " -> ".join(names)
            pyxel.text(
                WIDTH // 2 - len(order_text) * 2,
                50,
                order_text,
                WHITE,
            )

    def _draw_game_base(self) -> None:
        pyxel.cls(BLACK)
        self._draw_order()
        self._draw_glass()
        self._draw_combo()
        self._draw_message()
        self._draw_bottles()
        self._draw_serve_button()
        self._draw_hud()
        self._draw_floating_texts()
        self._draw_particles()

    def _draw_serve_anim(self) -> None:
        self._draw_game_base()
        flash = self._serve_anim_timer % 4 < 2
        if flash:
            pyxel.rectb(0, 0, WIDTH, HEIGHT, WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25.0
            c = p.color if alpha > 0.4 else GRAY
            s = max(1, min(3, int(self.combo * 0.5) + 1))
            pyxel.rect(int(p.x) - s // 2, int(p.y) - s // 2, s, s, c)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            c = ft.color if alpha > 0.5 else GRAY
            offset = int(30 - ft.life) * 0.3
            pyxel.text(
                int(ft.x) - len(ft.text) * 2,
                int(ft.y) - int(offset),
                ft.text,
                c,
            )

    def _draw_gameover(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(110, 30, "GAME OVER", RED)
        pyxel.text(80, 55, "You overheated!", ORANGE)

        pyxel.text(110, 80, f"Score: {self.score}", WHITE)
        pyxel.text(80, 100, f"Max COMBO: x{self.max_combo}", CYAN)
        pyxel.text(90, 120, f"Rounds: {self._round}", GRAY)
        pyxel.text(70, 145, f"Total Pours: {len(self.pours)}", GRAY)

        if (pyxel.frame_count // 20) % 2 == 0:
            pyxel.text(85, 180, "Click or R to Retry", YELLOW)

        self._draw_particles()
        self._draw_floating_texts()

    # ------------------------------------------------------------------
    # Global draw
    # ------------------------------------------------------------------

    def draw(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.ORDER_APPEAR:
                self._draw_order_appear()
            case Phase.POURING:
                self._draw_game_base()
            case Phase.SERVE_ANIM:
                self._draw_serve_anim()
            case Phase.GAME_OVER:
                self._draw_gameover()


# ---------------------------------------------------------------------------
# App wrapper
# ---------------------------------------------------------------------------


class App:
    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="BAR CHAIN", display_scale=2)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        self.game.update()

    def draw(self) -> None:
        self.game.draw()


if __name__ == "__main__":
    App()
