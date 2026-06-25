"""161_hanoi_surge — Tower of Hanoi Color-Match COMBO Chain."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto


import pyxel


# ── Phase Enum ──

class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    ANIM = auto()
    GAME_OVER = auto()


# ── Data Classes ──

@dataclass
class Disk:
    size: int  # 1-5 (1=smallest, 5=largest)
    color: int  # Pyxel color constant
    peg: int  # 0, 1, 2


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


# ── Constants ──

SCREEN_W = 320
SCREEN_H = 240
PEG_X = [53, 160, 267]
PEG_Y_TOP = 40
PEG_Y_BOTTOM = 200
DISK_H = 16
DISK_W_UNIT = 20
MAX_HEAT = 100.0
SUPER_THRESHOLD = 4
DISK_COLORS = [8, 3, 12, 10, 2]  # RED, GREEN, CYAN, YELLOW, PURPLE
OPTIMAL_MOVES = 31  # 2^5 - 1
GAME_TIME = 120.0  # seconds
ANIM_DURATION = 0.5  # seconds for super move animation
HEAT_INVALID = 15.0
HEAT_DECAY = 0.02  # per frame at 60fps
DISK_COUNT = 5
CLICK_RANGE = 55  # max distance in pixels for peg click detection
COMBO_BONUS_PER_STEP = 50

# Pyxel palette aliases
BLACK = 0
NAVY = 1
PURPLE_C = 2
GREEN_C = 3
BROWN = 4
DARK_BLUE = 5
LIGHT_BLUE = 6
WHITE = 7
RED_C = 8
ORANGE = 9
YELLOW = 10
LIME = 11
CYAN_C = 12
GRAY = 13
PINK = 14
PEACH = 15

RAINBOW = [RED_C, ORANGE, YELLOW, GREEN_C, LIGHT_BLUE, PURPLE_C]


# ── Optimal Path Generator ──

def _generate_optimal_path(n: int = DISK_COUNT, src: int = 0, dst: int = 2, aux: int = 1) -> list[tuple[int, int]]:
    """Generate the optimal Tower of Hanoi move sequence from src to dst."""
    result: list[tuple[int, int]] = []

    def hanoi(k: int, frm: int, to: int, via: int) -> None:
        if k == 0:
            return
        hanoi(k - 1, frm, via, to)
        result.append((frm, to))
        hanoi(k - 1, via, to, frm)

    hanoi(n, src, dst, aux)
    return result


OPTIMAL_PATH = _generate_optimal_path()


# ── Game Class (pure logic, testable) ──

class Game:
    """Core game logic. No Pyxel input calls inside logic methods."""

    def __init__(self) -> None:
        self.pegs: list[list[Disk]] = [[], [], []]
        self.selected_peg: int = -1
        self.phase: Phase = Phase.TITLE
        self.moves: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.heat: float = 0.0
        self.game_timer: float = GAME_TIME
        self.super_moves_left: int = 0
        self.last_color: int = -1
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.ghost_moves: list[tuple[int, int]] = list(OPTIMAL_PATH)
        self.ghost_step: int = 0
        self.anim_timer: float = 0.0
        self.rng: random.Random = random.Random()
        self._title_blink: int = 0
        self._go_blink: int = 0
        self._camera_shake: float = 0.0
        self._init_state()

    # ── State Init / Reset ──

    def _init_state(self) -> None:
        """Initialize/reset all game state."""
        self.pegs = [[], [], []]
        colors_pool = list(DISK_COLORS)
        for size in range(DISK_COUNT, 0, -1):
            # Assign colors randomly for combo variety, but guarantee at least one duplicate
            color = self.rng.choice(colors_pool)
            self.pegs[0].append(Disk(size=size, color=color, peg=0))
        self.selected_peg = -1
        self.phase = Phase.TITLE
        self.moves = 0
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.game_timer = GAME_TIME
        self.super_moves_left = 0
        self.last_color = -1
        self.particles.clear()
        self.floating_texts.clear()
        self.ghost_moves = list(OPTIMAL_PATH)
        self.ghost_step = 0
        self.anim_timer = 0.0
        self._camera_shake = 0.0

    def start_game(self) -> None:
        """Start or restart the game from TITLE or GAME_OVER."""
        self._init_state()
        self.phase = Phase.PLAYING

    # ── Core Move Logic ──

    def _valid_move(self, from_peg: int, to_peg: int) -> bool:
        """Check if moving top disk from from_peg to to_peg is valid (size rules)."""
        source = self.pegs[from_peg]
        if not source:
            return False
        moving_disk = source[-1]
        target = self.pegs[to_peg]
        if not target:
            return True
        return moving_disk.size < target[-1].size

    def _move_disk(self, from_peg: int, to_peg: int) -> int:
        """
        Move top disk from from_peg to to_peg.
        Returns disk color if valid, -1 otherwise.
        """
        if not self._valid_move(from_peg, to_peg):
            return -1
        disk = self.pegs[from_peg].pop()
        disk.peg = to_peg
        self.pegs[to_peg].append(disk)
        self.moves += 1
        return disk.color

    def _do_super_move(self, from_peg: int, to_peg: int) -> bool:
        """
        Execute super move: move any disk ignoring size rules.
        Consumes one charge. Returns True if successful.
        """
        if self.super_moves_left <= 0:
            return False
        source = self.pegs[from_peg]
        if not source:
            return False
        if from_peg == to_peg:
            return False
        disk = source.pop()
        disk.peg = to_peg
        self.pegs[to_peg].append(disk)
        self.moves += 1
        self.super_moves_left -= 1
        return True

    def _can_super_move(self) -> bool:
        """Check if super move is available."""
        return self.super_moves_left > 0

    # ── Combo System ──

    def _update_combo(self, color: int) -> None:
        """Update combo counter based on move color."""
        if self.last_color == -1:
            # First move
            self.combo = 1
            self.last_color = color
        elif color == self.last_color:
            self.combo += 1
        else:
            self.combo = 1
            self.last_color = color

        self.max_combo = max(self.max_combo, self.combo)

        # Grant super move charge when combo reaches threshold
        if self.combo >= SUPER_THRESHOLD:
            self.super_moves_left += 1
            # Only grant once per threshold reach (reset combo tracking)
            # Actually let's grant each step beyond threshold
            # But that's too easy. Let's grant once when reaching threshold
            # and then again at threshold * 2, etc.
            if self.combo == SUPER_THRESHOLD:
                self.super_moves_left += 1

    def _has_just_reached_super_threshold(self, old_combo: int) -> bool:
        """Check if combo just reached SUPER_THRESHOLD this move."""
        return old_combo < SUPER_THRESHOLD and self.combo >= SUPER_THRESHOLD

    # ── Score ──

    def _compute_score(self) -> int:
        """Score formula: base = (OPTIMAL / moves) * 1000, combo_bonus = max_combo * 50."""
        moves = max(self.moves, 1)
        base = int((OPTIMAL_MOVES / moves) * 1000)
        combo_bonus = self.max_combo * COMBO_BONUS_PER_STEP
        return base + combo_bonus

    # ── Victory ──

    def _check_victory(self) -> bool:
        """Check if all DISK_COUNT disks are on peg 2 in correct order (size 5 bottom to 1 top)."""
        if len(self.pegs[2]) != DISK_COUNT:
            return False
        expected_sizes = list(range(DISK_COUNT, 0, -1))
        actual_sizes = [d.size for d in self.pegs[2]]
        return actual_sizes == expected_sizes

    # ── Heat ──

    def _add_heat(self, amount: float) -> None:
        """Add heat. Check if >= MAX_HEAT -> game over."""
        self.heat = min(self.heat + amount, MAX_HEAT)
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER

    def _update_heat(self, dt: float) -> None:
        """Decay heat over time."""
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY * dt * 60)

    # ── Timer ──

    def _update_timer(self, dt: float) -> None:
        """Decrease game timer. Check time-out -> game over."""
        self.game_timer -= dt
        if self.game_timer <= 0:
            self.game_timer = 0
            self.phase = Phase.GAME_OVER

    # ── Handle Click (main entry point) ──

    def _handle_click(self, peg_index: int) -> str:
        """
        Handle peg click: select source or move to target.
        Returns string describing the action result.
        """
        if self.phase != Phase.PLAYING and self.phase != Phase.ANIM:
            return "no_play"

        # In ANIM phase, ignore clicks
        if self.phase == Phase.ANIM:
            return "no_play"

        if peg_index < 0 or peg_index > 2:
            return "invalid_peg"

        # No peg selected -> select this peg if it has disks
        if self.selected_peg == -1:
            if not self.pegs[peg_index]:
                return "empty_peg"
            self.selected_peg = peg_index
            return "selected"

        # Same peg clicked -> deselect
        if self.selected_peg == peg_index:
            self.selected_peg = -1
            return "deselected"

        # Different peg -> try to move
        from_peg = self.selected_peg
        to_peg = peg_index
        self.selected_peg = -1  # deselect regardless of outcome

        source = self.pegs[from_peg]
        if not source:
            return "no_disk"

        disk = source[-1]

        # Check validity
        valid = self._valid_move(from_peg, to_peg)
        super_available = self._can_super_move()

        # If super move is available and normal move is not valid, use super
        if not valid and not super_available:
            # Invalid move
            cx = PEG_X[from_peg]
            cy = PEG_Y_BOTTOM - len(self.pegs[from_peg]) * DISK_H
            self._spawn_particles(float(cx), float(cy), RED_C, 3, 8)
            self._add_heat(HEAT_INVALID)
            self._spawn_floating_text(float(cx), float(cy - 10), f"+{int(HEAT_INVALID)} HEAT", RED_C, 20)
            return "invalid"

        if not valid and super_available:
            # Use super move
            self._do_super_move(from_peg, to_peg)
            self._update_combo(disk.color)
            cx = PEG_X[to_peg]
            cy = PEG_Y_BOTTOM - len(self.pegs[to_peg]) * DISK_H
            self._spawn_particles(float(cx), float(cy), RAINBOW[0], 20, 20)
            self._spawn_floating_text(
                float(SCREEN_W // 2), float(SCREEN_H // 2), "SUPER MOVE!", YELLOW, 45
            )
            self._anim_timer = ANIM_DURATION
            self.phase = Phase.ANIM
            self._camera_shake = 0.3
            if self._check_victory():
                self._finalize_score()
                self.phase = Phase.GAME_OVER
            return "super_move"

        # Normal valid move
        old_combo = self.combo
        self._move_disk(from_peg, to_peg)
        self._update_combo(disk.color)

        cx = PEG_X[to_peg]
        cy = PEG_Y_BOTTOM - len(self.pegs[to_peg]) * DISK_H
        self._spawn_particles(float(cx), float(cy), disk.color, 5, 10)

        if self.combo > old_combo and self.combo >= 2:
            self._spawn_floating_text(
                float(SCREEN_W // 2), float(SCREEN_H // 2), f"COMBO x{self.combo}!", YELLOW, 30
            )

        if self._has_just_reached_super_threshold(old_combo):
            self._spawn_floating_text(
                float(SCREEN_W // 2), float(SCREEN_H // 2 - 16), "SURGE READY!", ORANGE, 40
            )

        if self._check_victory():
            self._finalize_score()
            self.phase = Phase.GAME_OVER
            self._spawn_floating_text(
                float(SCREEN_W // 2), float(SCREEN_H // 2), "CLEAR!", GREEN_C, 60
            )

        return "moved"

    # ── Score Finalize ──

    def _finalize_score(self) -> None:
        """Compute final score."""
        self.score = self._compute_score()

    # ── Per-frame Update ──

    def update(self) -> None:
        """Per-frame update (called by App). Handles blink timers and ANIM."""
        dt = 1.0 / 60.0  # Fixed timestep assumption
        self._title_blink = (self._title_blink + 1) % 60
        self._go_blink = (self._go_blink + 1) % 60

        if self.phase == Phase.PLAYING:
            self._update_timer(dt)
            self._update_heat(dt)
            self._update_particles()
            self._update_floating_texts()

        elif self.phase == Phase.ANIM:
            self._anim_timer -= dt
            self._update_particles()
            self._update_floating_texts()
            if self._camera_shake > 0:
                self._camera_shake = max(0.0, self._camera_shake - dt)
            if self._anim_timer <= 0:
                self._anim_timer = 0.0
                self.phase = Phase.PLAYING
                # Check victory again in case super move won
                if self._check_victory():
                    self._finalize_score()
                    self.phase = Phase.GAME_OVER
                # Check heat game over
                if self.heat >= MAX_HEAT:
                    self._finalize_score()
                    self.phase = Phase.GAME_OVER

        elif self.phase == Phase.TITLE:
            self._update_particles()
            self._update_floating_texts()

        elif self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floating_texts()

    # ── Particles ──

    def _spawn_particles(self, x: float, y: float, color: int, count: int, life: int) -> None:
        """Spawn burst of particles at position."""
        for _ in range(count):
            angle = self.rng.uniform(0, 2 * math.pi)
            speed = self.rng.uniform(0.5, 3.0)
            self.particles.append(
                Particle(
                    x=x + self.rng.uniform(-6, 6),
                    y=y + self.rng.uniform(-4, 4),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 1.0,
                    color=color,
                    life=self.rng.randint(max(4, life - 2), life + 2),
                )
            )

    def _update_particles(self) -> None:
        """Update particle positions, apply gravity, remove dead."""
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # gravity
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    # ── Floating Texts ──

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        """Spawn floating text."""
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=life, color=color)
        )

    def _update_floating_texts(self) -> None:
        """Update floating text positions and life, remove dead."""
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.8  # float upward
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    # ── Drawing ──

    def draw(self) -> None:
        """Draw the current phase."""
        pyxel.cls(DARK_BLUE)

        self._draw_pegs()
        self._draw_disks()
        self._draw_ghost_trail()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()

        if self.phase == Phase.TITLE:
            self._draw_title_overlay()
        elif self.phase == Phase.ANIM:
            self._draw_anim_effect()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over_overlay()

    def _draw_pegs(self) -> None:
        """Draw 3 pegs as vertical rectangles."""
        for i, px in enumerate(PEG_X):
            color = GRAY
            if i == self.selected_peg:
                color = WHITE
            pyxel.rect(px - 2, PEG_Y_TOP, 4, PEG_Y_BOTTOM - PEG_Y_TOP, color)
        self._draw_peg_base()

    def _draw_peg_base(self) -> None:
        """Draw peg base plates."""
        for px in PEG_X:
            pyxel.rect(px - 12, PEG_Y_BOTTOM, 24, 6, GRAY)

    def _draw_disks(self) -> None:
        """Draw all disks on their pegs."""
        for pi, peg_stack in enumerate(self.pegs):
            for di, disk in enumerate(peg_stack):
                width = disk.size * DISK_W_UNIT
                x = PEG_X[pi] - width // 2
                y = PEG_Y_BOTTOM - (di + 1) * DISK_H
                pyxel.rect(x, y, width, DISK_H - 1, disk.color)
                pyxel.rectb(x, y, width, DISK_H - 1, WHITE)
                # Draw disk size number
                size_str = str(disk.size)
                tx = x + (width - len(size_str) * 4) // 2
                pyxel.text(tx, y + 4, size_str, BLACK)

    def _draw_ghost_trail(self) -> None:
        """Draw ghost trail showing upcoming optimal moves."""
        if self.phase != Phase.PLAYING:
            return
        # Show next 3 optimal moves as faint dots
        start = self.ghost_step
        for i in range(start, min(start + 3, len(self.ghost_moves))):
            frm, to = self.ghost_moves[i]
            alpha = 12 - (i - start) * 3  # fade out
            if alpha <= 0:
                break
            fx = PEG_X[frm]
            tx = PEG_X[to]
            mid_x = (fx + tx) // 2
            mid_y = PEG_Y_BOTTOM - DISK_H * (DISK_COUNT + 1) - (i - start) * 3
            pyxel.circ(mid_x, mid_y, 2, alpha)

    def _draw_hud(self) -> None:
        """Draw HUD: timer, score, combo, heat bar."""
        # Timer (top-left)
        time_s = max(0.0, self.game_timer)
        pyxel.text(4, 4, f"TIME: {time_s:.0f}s", WHITE)

        # Score (top-right)
        if self.phase == Phase.GAME_OVER:
            pyxel.text(SCREEN_W - 100, 4, f"SCORE: {self.score}", YELLOW)
        else:
            pyxel.text(SCREEN_W - 100, 4, "SCORE: ---", GRAY)

        # Combo
        combo_color = YELLOW if self.combo >= 3 else WHITE
        # Pulsing effect for combo >= 3
        if self.combo >= 3 and (pyxel.frame_count % 30) < 15:
            combo_color = ORANGE
        pyxel.text(SCREEN_W - 100, 14, f"COMBO: x{self.combo}", combo_color)

        # Super move indicator
        if self._can_super_move():
            sc = RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
            if self.combo >= SUPER_THRESHOLD:
                pyxel.text(SCREEN_W - 100, 24, "SUPER READY!", sc)

        # Heat bar (bottom)
        bar_x = 10
        bar_y = SCREEN_H - 18
        bar_w = 120
        pyxel.rect(bar_x, bar_y, bar_w, 6, GRAY)
        hw = int(bar_w * self.heat / MAX_HEAT)
        heat_color = GREEN_C
        if self.heat >= 80:
            heat_color = RED_C if (pyxel.frame_count % 20) < 10 else ORANGE  # flash
        elif self.heat >= 50:
            heat_color = ORANGE
        elif self.heat >= 30:
            heat_color = YELLOW
        pyxel.rect(bar_x, bar_y, hw, 6, heat_color)
        pyxel.rectb(bar_x, bar_y, bar_w, 6, WHITE)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, f"HEAT {int(self.heat)}", WHITE)

        # Super charge counter
        pyxel.text(SCREEN_W - 100, SCREEN_H - 14, f"CHARGES: {self.super_moves_left}", ORANGE)

        # Moves count
        pyxel.text(4, 14, f"MOVES: {self.moves}", GRAY)

    def _draw_particles(self) -> None:
        """Draw all particles."""
        for p in self.particles:
            if p.life < 3:
                c = DARK_BLUE if p.life % 2 == 0 else p.color
            else:
                c = p.color
            pyxel.pset(int(p.x), int(p.y), c)

    def _draw_floating_texts(self) -> None:
        """Draw all floating texts."""
        for ft in self.floating_texts:
            # Center the text
            tx = int(ft.x) - len(ft.text) * 2
            pyxel.text(tx, int(ft.y), ft.text, ft.color)

    def _draw_title_overlay(self) -> None:
        """Draw title screen overlay."""
        # Semi-transparent overlay
        pyxel.rect(30, 20, 260, 200, BLACK)
        pyxel.rectb(30, 20, 260, 200, WHITE)
        pyxel.text(100, 35, "HANOI SURGE", YELLOW)
        pyxel.text(112, 47, "Color-Match COMBO", LIGHT_BLUE)
        pyxel.text(72, 70, "CLICK a peg to SELECT/MOVE disks", GRAY)
        pyxel.text(60, 86, "Same-color consecutive moves", GRAY)
        pyxel.text(72, 98, "build a COMBO chain.", GRAY)
        pyxel.text(72, 114, "COMBO 4+ unlocks SUPER MOVE!", YELLOW)
        pyxel.text(72, 130, "Super move ignores size rules.", ORANGE)
        pyxel.text(72, 146, "Invalid size moves build HEAT.", RED_C)
        pyxel.text(72, 162, "HEAT 100 or Time up = GAME OVER.", RED_C)
        pyxel.text(64, 186, "Stack all disks on RIGHT peg to WIN!", GREEN_C)
        if self._title_blink < 30:
            pyxel.text(85, 210, "Press SPACE to start", WHITE)

    def _draw_anim_effect(self) -> None:
        """Draw animation effect for super move."""
        # Flash overlay
        intensity = self._anim_timer / ANIM_DURATION
        flash_alpha = int(intensity * 200)  # 0-200 range for color intensity
        if flash_alpha > 0:
            # Use a bright flash that fades
            flash_color = YELLOW if intensity > 0.5 else WHITE
            # Just draw a rect with low opacity effect via a checker pattern
            if int(self._anim_timer * 120) % 2 == 0:
                pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, flash_color)
                pyxel.rectb(2, 2, SCREEN_W - 4, SCREEN_H - 4, flash_color)

        # Screen shake
        if self._camera_shake > 0:
            sx = self.rng.randint(-3, 3) if self._camera_shake > 0.1 else 0
            sy = self.rng.randint(-3, 3) if self._camera_shake > 0.1 else 0
            pyxel.camera(sx, sy)

    def _draw_game_over_overlay(self) -> None:
        """Draw game over overlay."""
        pyxel.rect(35, 35, 250, 170, BLACK)
        pyxel.rectb(35, 35, 250, 170, WHITE)
        pyxel.text(110, 44, "GAME OVER", RED_C)

        # Score
        pyxel.text(55, 70, f"SCORE:        {self.score}", WHITE)
        pyxel.text(55, 86, f"MOVES:        {self.moves}", GRAY)
        pyxel.text(55, 102, f"MAX COMBO:    x{self.max_combo}", YELLOW)
        pyxel.text(55, 118, f"SUPER USED:   {self.super_moves_left} left", ORANGE)
        pyxel.text(55, 134, f"TIME:         {self.game_timer:.0f}s left", GRAY)

        # Cause of death
        if self.heat >= MAX_HEAT:
            cause = "HEAT OVERLOAD"
            cause_color = RED_C
        elif self.game_timer <= 0:
            cause = "TIME UP"
            cause_color = GRAY
        else:
            cause = "CLEAR!"
            cause_color = GREEN_C
        pyxel.text(55, 150, f"CAUSE:        {cause}", cause_color)

        if self._go_blink < 30:
            pyxel.text(85, 190, "Press SPACE to retry", WHITE)


# ── Pyxel App Layer (input handling only) ──


class App:
    """Pyxel application wrapper. Handles input, delegates logic to Game."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Hanoi Surge", display_scale=2)
        pyxel.mouse(True)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game

        if g.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                g.start_game()
            return

        if g.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                g.start_game()
            g.update()
            return

        if g.phase == Phase.PLAYING:
            # ESC returns to title
            if pyxel.btnp(pyxel.KEY_ESCAPE):
                g.phase = Phase.TITLE
                return

            # Mouse click
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                mx = pyxel.mouse_x
                my = pyxel.mouse_y
                peg = self._find_nearest_peg(mx, my)
                if peg >= 0:
                    g._handle_click(peg)

        g.update()

    def _find_nearest_peg(self, mx: int, my: int) -> int:
        """Find the nearest peg within CLICK_RANGE of (mx, my). Returns -1 if none."""
        best = -1
        best_dist = float("inf")
        for i, px in enumerate(PEG_X):
            dx = mx - px
            dy = my - (PEG_Y_TOP + PEG_Y_BOTTOM) / 2
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < CLICK_RANGE and dist < best_dist:
                best = i
                best_dist = dist
        return best

    def draw(self) -> None:
        pyxel.camera()  # Reset camera
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
