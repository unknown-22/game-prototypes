import random
from dataclasses import dataclass

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240
PAD_WIDTH = 40
PAD_HEIGHT = 8
PAD_SPACING = 55
PLAYER_W = 8
PLAYER_H = 16
GRAVITY = 0.3
MAX_CHARGE = 60
CHARGE_RATE = 1.0
MIN_BOUNCE = 4.0
MAX_BOUNCE = 12.0
MOVE_SPEED = 3.0
COMBO_FOR_SUPER = 5
SUPER_DURATION = 300
MAX_HEAT = 100
HEAT_PER_WRONG = 15
HEAT_DECAY = 0.05
LAVA_RISE_SPEED = 0.3
NUM_COLORS = 4
NUM_COLS = 5

COLOR_VALS = (8, 3, 6, 10)  # RED, GREEN, LIGHT_BLUE, YELLOW


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclass
class Pad:
    x: float
    y: float
    color: int  # 0-3
    width: int = 40
    height: int = 8
    active: bool = True


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
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
        self.phase = "TITLE"

    def _init_state(self) -> None:
        self.phase = "TITLE"
        self.player_x: float = 160.0
        self.player_y: float = 80.0
        self.player_vy: float = 0.0
        self.player_color: int = 0
        self.charge: float = 0.0
        self.is_charging: bool = False
        self.on_ground: bool = True
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.heat: float = 0.0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.pads: list[Pad] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.lava_y: float = float(SCREEN_H + 100)
        self.shake_frames: int = 0
        self.frame: int = 0
        self.rng: random.Random = random.Random()
        self._col_positions: list[int] = [40 + i * 60 for i in range(NUM_COLS)]

    def reset(self) -> None:
        self._init_state()
        self.phase = "PLAYING"
        self.rng = random.Random()
        self._spawn_pads()
        best_pad: Pad | None = None
        best_dist: float = float("inf")
        for pad in self.pads:
            dist = abs(pad.y - 80.0)
            if dist < best_dist:
                best_dist = dist
                best_pad = pad
        if best_pad is not None:
            self.player_x = best_pad.x
            self.player_y = best_pad.y - PLAYER_H
            self.player_color = best_pad.color
            self.on_ground = True

    # -- spawning -----------------------------------------------------------

    def _spawn_pads(self) -> None:
        self.pads.clear()
        cols = self._col_positions
        for row_y in range(-200, SCREEN_H + 200, PAD_SPACING):
            for col_x in cols:
                offset_y = self.rng.randint(-5, 5)
                self.pads.append(
                    Pad(
                        x=float(col_x),
                        y=float(row_y + offset_y),
                        color=self.rng.randint(0, NUM_COLORS - 1),
                    )
                )

    def _scroll_pads(self, dy: float) -> None:
        cols = self._col_positions
        for pad in self.pads:
            pad.y += dy
        self.pads = [p for p in self.pads if p.y < SCREEN_H + 50]
        if not self.pads:
            return
        top_y = min(p.y for p in self.pads)
        while top_y > -PAD_SPACING * 3:
            top_y -= PAD_SPACING
            for col_x in cols:
                self.pads.append(
                    Pad(
                        x=float(col_x),
                        y=float(top_y + self.rng.randint(-5, 5)),
                        color=self.rng.randint(0, NUM_COLORS - 1),
                    )
                )

    # -- physics & landing --------------------------------------------------

    def _update_physics(self) -> None:
        self.player_vy += GRAVITY
        self.player_y += self.player_vy

    def _check_landing(self) -> bool:
        if self.player_vy <= 0:
            return False
        player_bottom = self.player_y + PLAYER_H
        player_bottom_prev = player_bottom - self.player_vy

        for pad in self.pads:
            if not pad.active:
                continue
            if abs(self.player_x - pad.x) > (PLAYER_W + pad.width) / 2:
                continue
            if player_bottom_prev <= pad.y < player_bottom:
                self.player_y = pad.y - PLAYER_H
                self.player_vy = 0.0
                self.on_ground = True

                if self.super_mode:
                    self.combo += 1
                    score_gain = self.score_for_landing(True) * 3
                    self.score += score_gain
                    self._spawn_particles(
                        self.player_x, self.player_y + PLAYER_H,
                        COLOR_VALS[pad.color], 12,
                    )
                    self._add_floating_text(
                        self.player_x, self.player_y - 8,
                        f"x{self.combo} +{score_gain}", 7,
                    )
                    self.player_vy = -(MIN_BOUNCE + 3)
                    self.on_ground = False
                elif pad.color == self.player_color:
                    self.combo += 1
                    score_gain = self.score_for_landing(True)
                    self.score += score_gain
                    self._spawn_particles(
                        self.player_x, self.player_y + PLAYER_H,
                        COLOR_VALS[pad.color], 8,
                    )
                    self._add_floating_text(
                        self.player_x, self.player_y - 8,
                        f"x{self.combo} +{score_gain}", COLOR_VALS[pad.color],
                    )
                    if self.combo >= COMBO_FOR_SUPER and not self.super_mode:
                        self._start_super()
                else:
                    self.heat = min(float(MAX_HEAT), self.heat + HEAT_PER_WRONG)
                    if not self.super_mode:
                        self.combo = 0
                    score_gain = self.score_for_landing(False)
                    self.score += score_gain
                    self._spawn_particles(
                        self.player_x, self.player_y + PLAYER_H, 13, 4,
                    )
                    self._add_floating_text(
                        self.player_x, self.player_y - 8, "MISS", 8,
                    )

                self.player_color = pad.color
                self.max_combo = max(self.max_combo, self.combo)
                return True
        return False

    # -- heat / lava --------------------------------------------------------

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_lava(self) -> None:
        self.lava_y -= LAVA_RISE_SPEED

    # -- particles / texts --------------------------------------------------

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self.rng.uniform(-2.0, 2.0)
            vy = self.rng.uniform(-3.0, -1.0)
            life = self.rng.randint(15, 30)
            self.particles.append(
                Particle(x=x, y=y, vx=float(vx), vy=float(vy), color=color, life=life)
            )

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x - len(text) * 2, y=y, text=text, color=color, life=45)
        )

    # -- super mode ---------------------------------------------------------

    def _start_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        for _ in range(30):
            vx = self.rng.uniform(-3.0, 3.0)
            vy = self.rng.uniform(-4.0, -1.0)
            c = COLOR_VALS[self.rng.randint(0, 3)]
            self.particles.append(
                Particle(
                    x=self.player_x, y=self.player_y,
                    vx=float(vx), vy=float(vy), color=c,
                    life=self.rng.randint(20, 40),
                )
            )
        self._add_floating_text(self.player_x, self.player_y - 20, "SUPER!", 7)

    def _end_super(self) -> None:
        self.super_mode = False
        self.super_timer = 0
        self.combo = 0

    # -- scoring ------------------------------------------------------------

    def score_for_landing(self, color_match: bool) -> int:
        if color_match:
            base = 10
            multiplier = 1.0 + max(0, self.combo - 1) * 0.5
            return max(1, int(base * multiplier))
        return 1

    # -- update / draw ------------------------------------------------------

    def update(self) -> None:
        self.frame += 1
        if self.phase == "PLAYING":
            self._update_playing()
        elif self.phase == "GAME_OVER":
            self._update_particles()
            self._update_floating_texts()

    def _update_playing(self) -> None:
        if self.player_y > SCREEN_H + 50:
            self.phase = "GAME_OVER"
            return
        if self.heat >= MAX_HEAT:
            self.phase = "GAME_OVER"
            return

        scroll = LAVA_RISE_SPEED
        self._scroll_pads(scroll)
        if self.on_ground:
            self.player_y += scroll

        space_held = pyxel.btn(pyxel.KEY_SPACE)

        if self.super_mode:
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                self.player_x -= MOVE_SPEED
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                self.player_x += MOVE_SPEED
        else:
            if self.on_ground:
                if space_held:
                    self.is_charging = True
                    self.charge = min(float(MAX_CHARGE), self.charge + CHARGE_RATE)
                elif self.is_charging:
                    charge_ratio = self.charge / MAX_CHARGE
                    self.player_vy = -(
                        MIN_BOUNCE + charge_ratio * (MAX_BOUNCE - MIN_BOUNCE)
                    )
                    self.on_ground = False
                    self.is_charging = False
                    self.charge = 0.0
            if not self.on_ground:
                if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                    self.player_x -= MOVE_SPEED
                if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                    self.player_x += MOVE_SPEED

        if not self.on_ground:
            self._update_physics()

        if not self.on_ground:
            self._check_landing()

        self.player_x = max(float(PLAYER_W), min(float(SCREEN_W - PLAYER_W), self.player_x))

        self._update_lava()
        self._update_heat()

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self._end_super()

        self._update_particles()
        self._update_floating_texts()

        if self.heat > 60:
            self.shake_frames = max(1, int((self.heat - 60) / 5))
        elif self.shake_frames > 0:
            self.shake_frames -= 1

    def draw(self) -> None:
        pyxel.cls(0)
        if self.shake_frames > 0 and self.phase == "PLAYING":
            sx = self.rng.randint(-self.shake_frames, self.shake_frames)
            sy = self.rng.randint(-self.shake_frames // 2, self.shake_frames // 2)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        if self.phase == "TITLE":
            self._draw_title()
        elif self.phase == "PLAYING":
            self._draw_playing()
        elif self.phase == "GAME_OVER":
            self._draw_game_over()

    # -- drawing helpers ----------------------------------------------------

    def _draw_title(self) -> None:
        for i in range(SCREEN_H):
            c = 1 if i < SCREEN_H // 2 else 5
            pyxel.line(0, i, SCREEN_W, i, c)

        lava_y = int(self.lava_y)
        for i in range(max(0, lava_y), SCREEN_H):
            c = 9 if (i // 4) % 2 == 0 else 8
            pyxel.line(0, i, SCREEN_W, i, c)

        title = "POGO SURGE"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 40, title, 7)

        sub = "Color-match bouncing!"
        pyxel.text(SCREEN_W // 2 - len(sub) * 2, 56, sub, 6)

        inst = [
            "Hold SPACE to charge spring",
            "Release to BOUNCE!",
            "LEFT / RIGHT to steer in air",
            "Match pad colors for COMBO",
            "COMBO x5 = SUPER POGO!",
        ]
        for i, line in enumerate(inst):
            pyxel.text(SCREEN_W // 2 - len(line) * 2, 80 + i * 14, line, 7)

        prompt = "PRESS SPACE TO START"
        if (self.frame // 30) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - len(prompt) * 2, 180, prompt, 10)

    def _draw_playing(self) -> None:
        for i in range(SCREEN_H):
            if i < SCREEN_H // 3:
                c = 1
            elif i < SCREEN_H * 2 // 3:
                c = 5
            else:
                c = 13
            pyxel.line(0, i, SCREEN_W, i, c)

        for pad in self.pads:
            if pad.y < -PAD_HEIGHT or pad.y > SCREEN_H + PAD_HEIGHT:
                continue
            col = COLOR_VALS[pad.color]
            pyxel.rect(
                int(pad.x - pad.width // 2) + 1, int(pad.y) + 1,
                pad.width, pad.height, 0,
            )
            pyxel.rect(
                int(pad.x - pad.width // 2), int(pad.y),
                pad.width, pad.height, col,
            )
            pyxel.line(
                int(pad.x - pad.width // 2), int(pad.y),
                int(pad.x + pad.width // 2), int(pad.y), 7,
            )

        self._draw_player()

        if self.is_charging and self.on_ground and not self.super_mode:
            bar_w = 24
            bar_h = 3
            bx = int(self.player_x - bar_w // 2)
            by = int(self.player_y - 6)
            fill = int(self.charge / MAX_CHARGE * bar_w)
            pyxel.rect(bx, by, bar_w, bar_h, 13)
            if fill > 0:
                charge_color = 10 if self.charge >= MAX_CHARGE else 9
                pyxel.rect(bx, by, fill, bar_h, charge_color)

        lava_y = int(self.lava_y)
        for i in range(max(0, lava_y), SCREEN_H):
            if i < lava_y + 8:
                c = 10 if (self.frame + i) % 6 < 3 else 9
            else:
                c = 8 if (i // 6) % 2 == 0 else 9
            pyxel.line(0, i, SCREEN_W, i, c)

        for i in range(5):
            px = (self.frame * 3 + i * 67) % SCREEN_W
            py = lava_y + self.rng.randint(-4, 4)
            if 0 <= py < SCREEN_H:
                pyxel.pset(int(px), int(py), 10 if self.rng.random() < 0.5 else 9)

        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_player(self) -> None:
        px = int(self.player_x)
        py = int(self.player_y)

        if self.super_mode:
            rainbow = [8, 10, 3, 6]
            for i in range(py + 3, py + PLAYER_H, 2):
                idx = ((i - py) // 2 + self.frame // 4) % 4
                pyxel.line(px, i, px, min(i + 1, py + PLAYER_H), rainbow[idx])
        else:
            pyxel.line(px, py + 3, px, py + PLAYER_H - 3, 7)

        head_color = 7
        if self.super_mode:
            head_color = 10 if (self.frame // 4) % 2 == 0 else 8
        pyxel.circ(px, py + 1, 3, head_color)

        coil_y = py + PLAYER_H - 5
        coil_color = 7 if self.super_mode else 13
        for i in range(3):
            pyxel.rect(px - 3, coil_y + i, 6, 1, coil_color)

        pyxel.rect(px - 2, py + PLAYER_H - 1, 4, 1, 7)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 0:
                size = 2 if p.life > 10 else 1
                pyxel.rect(int(p.x), int(p.y), size, size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE {self.score}", 7)

        combo_color = 7
        if self.combo >= 3:
            combo_color = 10
        if self.combo >= COMBO_FOR_SUPER:
            combo_color = 8
        pyxel.text(4, 14, f"COMBO x{self.combo}", combo_color)
        pyxel.text(4, 24, f"MAX x{self.max_combo}", 6)

        bar_x = SCREEN_W - 64
        bar_y = 4
        bar_w = 56
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, 13)
        fill = int(self.heat / MAX_HEAT * bar_w)
        heat_color = 9 if self.heat < 50 else (10 if self.heat < 80 else 8)
        if fill > 0:
            pyxel.rect(bar_x, bar_y, fill, bar_h, heat_color)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, 7)
        pyxel.text(bar_x - 16, bar_y - 1, "HEAT", 7)

        if self.super_mode:
            secs = self.super_timer // 60 + 1
            suptext = f"SUPER {secs}s"
            pyxel.text(SCREEN_W // 2 - len(suptext) * 2, 4, suptext, 8)

    def _draw_game_over(self) -> None:
        for i in range(SCREEN_H):
            pyxel.line(0, i, SCREEN_W, i, 5 if i % 2 == 0 else 1)

        self._draw_particles()
        self._draw_floating_texts()

        go = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(go) * 2, 40, go, 8)

        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 2, 70, score_text, 7)

        combo_text = f"MAX COMBO: x{self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 90, combo_text, 10)

        if self.heat >= MAX_HEAT:
            reason = "OVERHEATED!"
        else:
            reason = "FELL INTO LAVA!"
        pyxel.text(SCREEN_W // 2 - len(reason) * 2, 115, reason, 8)

        retry = "PRESS SPACE TO RETRY"
        if (self.frame // 30) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - len(retry) * 2, 160, retry, 7)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="POGO SURGE", display_scale=2)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game
        if g.phase == "TITLE":
            if pyxel.btnp(pyxel.KEY_SPACE):
                g.reset()
            g.update()
        elif g.phase == "GAME_OVER":
            g.update()
            if pyxel.btnp(pyxel.KEY_SPACE):
                g.reset()
        elif g.phase == "PLAYING":
            g.update()

    def draw(self) -> None:
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
