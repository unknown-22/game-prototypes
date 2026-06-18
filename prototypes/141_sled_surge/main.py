"""
SLED SURGE - Side-scrolling bobsled game.
Steer through color-coded gates, build combos, trigger SUPER BOOST,
avoid walls and manage heat. Ghost sled shows best previous run.

Most Fun Moment: Chaining same-color gates to trigger SUPER BOOST
and racking up 3x score in invincible rainbow mode.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

import pyxel

if not TYPE_CHECKING:
    pass

# ── Constants ─────────────────────────────────────────────────────────────────
SCREEN_W: int = 320
SCREEN_H: int = 240
SLED_X: float = 60.0
SLED_W: int = 20
SLED_H: int = 12
SLED_HALF_W: int = SLED_W // 2
SLED_HALF_H: int = SLED_H // 2
WALL_TOP: float = 20.0
WALL_BOTTOM: float = 220.0
SLED_MIN_Y: float = WALL_TOP + SLED_HALF_H + 2
SLED_MAX_Y: float = WALL_BOTTOM - SLED_HALF_H - 2
GATE_WIDTH: int = 40
GATE_OPENING: int = 100
GATE_HALF_OPENING: int = GATE_OPENING // 2
GATE_THICKNESS: int = 4
SUPER_DURATION: int = 300
MAX_HEAT: float = 100.0
HEAT_PER_MISS: float = 20.0
COMBO_FOR_SUPER: int = 5
TRACK_SPEED_BASE: float = 1.0
TRACK_SPEED_MAX: float = 4.0
MAX_SLED_SPEED: float = 4.0
PARTICLE_GRAVITY: float = 0.05

# ── Colors ────────────────────────────────────────────────────────────────────
BLACK: int = 0
NAVY: int = 1
PURPLE: int = 2
GREEN: int = 3
BROWN: int = 4
DARK_BLUE: int = 5
LIGHT_BLUE: int = 6
WHITE: int = 7
RED: int = 8
ORANGE: int = 9
YELLOW: int = 10
LIME: int = 11
CYAN: int = 12
GRAY: int = 13
PINK: int = 14
PEACH: int = 15

GATE_COLORS: tuple[int, ...] = (RED, GREEN, DARK_BLUE, YELLOW)
RAINBOW_COLORS: tuple[int, ...] = (RED, ORANGE, YELLOW, GREEN, LIGHT_BLUE, PURPLE, PINK)

# ── Enums ─────────────────────────────────────────────────────────────────────
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()

# ── Data Classes ──────────────────────────────────────────────────────────────
@dataclass
class Gate:
    x: float
    opening_y: float
    color: int
    collected: bool = False

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int

@dataclass
class GhostPoint:
    x: float  # distance
    y: float  # sled_y

# ── Game ──────────────────────────────────────────────────────────────────────
class Game:
    """Main game class. Phase-driven state machine with core logic separated from pyxel I/O."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, "SLED SURGE", display_scale=2)
        # Pre-init all state attributes for headless testing compatibility
        self.phase: Phase = Phase.TITLE
        self.sled_y: float = 120.0
        self.score: int = 0
        self.best_score: int = 0
        self.distance: float = 0.0
        self.combo: int = 0
        self.max_combo: int = 0
        self.combo_color: int = -1
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.gates: list[Gate] = []
        self.particles: list[Particle] = []
        self.best_ghost: list[GhostPoint] = []
        self.track_speed: float = TRACK_SPEED_BASE
        self.spawn_timer: int = 0
        self.game_timer: int = 0
        self.shake_frames: int = 0
        self._ghost_record: list[GhostPoint] = []
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State Management ──────────────────────────────────────────────────
    def reset(self) -> None:
        """Reset all game state to initial values."""
        self.phase = Phase.TITLE
        self.sled_y = 120.0
        self.score = 0
        self.distance = 0.0
        self.combo = 0
        self.max_combo = 0
        self.combo_color = -1
        self.heat = 0.0
        self.super_timer = 0
        self.gates.clear()
        self.particles.clear()
        self._ghost_record.clear()
        self.track_speed = TRACK_SPEED_BASE
        self.spawn_timer = 60
        self.game_timer = 0
        self.shake_frames = 0

    # ── Update Dispatch ───────────────────────────────────────────────────
    def update(self) -> None:
        """Global update — dispatch to phase handler."""
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_gameover()

    # ── Draw Dispatch ─────────────────────────────────────────────────────
    def draw(self) -> None:
        """Global draw — apply screen shake, clear, dispatch to phase renderer."""
        pyxel.cls(BLACK)
        if self.shake_frames > 0 and self.phase == Phase.PLAYING:
            shake_x: int = self._rng.randint(-2, 2)
            pyxel.camera(shake_x, 0)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_gameover()

    # ── TITLE ─────────────────────────────────────────────────────────────
    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.PLAYING

    def _draw_title(self) -> None:
        # Title text
        title: str = "SLED SURGE"
        title_w: int = len(title) * 4
        pyxel.text(SCREEN_W // 2 - title_w // 2, 60, title, WHITE)

        # Subtitle
        sub: str = "SIDE-SCROLLING BOBSLED GAME"
        sub_w: int = len(sub) * 4
        pyxel.text(SCREEN_W // 2 - sub_w // 2, 76, sub, LIGHT_BLUE)

        # Controls
        controls: list[str] = [
            "STEER: UP/DOWN or W/S",
            "START: ENTER or SPACE",
        ]
        for i, line in enumerate(controls):
            lw: int = len(line) * 4
            pyxel.text(SCREEN_W // 2 - lw // 2, 110 + i * 12, line, GRAY)

        # Best score display
        if self.best_score > 0:
            best_text: str = f"BEST SCORE: {self.best_score}"
            bw: int = len(best_text) * 4
            pyxel.text(SCREEN_W // 2 - bw // 2, 150, best_text, YELLOW)

        # Decorative sled silhouette
        pyxel.rectb(SLED_X - SLED_HALF_W, 120 - SLED_HALF_H, SLED_W, SLED_H, GRAY)

        # Draw best ghost motion trail if available
        if self.best_ghost:
            ghost_len: int = min(len(self.best_ghost), 60)
            for i in range(0, ghost_len, 4):
                gp: GhostPoint = self.best_ghost[-(i + 1)]
                alpha_color: int = GRAY if i < 40 else NAVY
                gy: float = gp.y
                if WALL_TOP < gy < WALL_BOTTOM:
                    pyxel.pset(SLED_X, int(gy), alpha_color)

    # ── PLAYING ───────────────────────────────────────────────────────────
    def _update_playing(self) -> None:
        self.game_timer += 1

        # ── Input ──
        dy: float = 0.0
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -MAX_SLED_SPEED
        elif pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = MAX_SLED_SPEED

        # ── Target Y computation ──
        target_y: float = self.sled_y
        if dy != 0.0:
            target_y = self.sled_y + dy * 100.0  # far in desired direction = full-speed move
        elif self.super_timer > 0:
            nearest: Gate | None = self._find_nearest_gate()
            if nearest is not None:
                target_y = nearest.opening_y

        # ── Move sled ──
        self.sled_y = self._move_sled(target_y)

        # ── Update track speed ──
        self.track_speed = min(TRACK_SPEED_MAX, TRACK_SPEED_BASE + self.distance * 0.001)
        self.distance += self.track_speed

        # ── Update SUPER timer ──
        self._update_super()

        # ── Spawn gates ──
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.gates.append(self._spawn_gate())
            base_interval: int = 90 - int(self.distance * 0.1)
            self.spawn_timer = self._rng.randint(max(25, base_interval - 15), max(35, base_interval + 15))

        # ── Update gates ──
        collected: int = self._update_gates()
        if collected > 0:
            if self.super_timer > 0:
                pyxel.play(0, 2)
            else:
                pyxel.play(0, 0)

        # ── Update particles ──
        self._update_particles()

        # ── Record ghost ──
        self._update_ghost()

        # ── Check wall collision ──
        if not (self.super_timer > 0) and self._check_wall_collision(self.sled_y):
            self._spawn_particles(SLED_X, self.sled_y, RED, 20)
            self.shake_frames = 15
            self.phase = Phase.GAME_OVER
            self._save_ghost()
            return

        # ── Check heat ──
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            self._save_ghost()
            return

        # ── Shake decay ──
        if self.shake_frames > 0:
            self.shake_frames -= 1

    def _draw_playing(self) -> None:
        # ── Walls ──
        pyxel.rect(0, 0, SCREEN_W, int(WALL_TOP), BROWN)
        pyxel.rect(0, int(WALL_BOTTOM), SCREEN_W, int(SCREEN_H - WALL_BOTTOM), BROWN)

        # ── Gates ──
        for gate in self.gates:
            gx: int = int(gate.x)
            # Gate occupies [gx, gx + GATE_WIDTH]
            gate_top: float = gate.opening_y - GATE_HALF_OPENING
            gate_bottom: float = gate.opening_y + GATE_HALF_OPENING
            gate_color: int = gate.color

            # Top bar of gate
            top_bottom: int = int(gate_top)
            if top_bottom > int(WALL_TOP):
                pyxel.rect(gx, int(WALL_TOP), GATE_WIDTH, top_bottom - int(WALL_TOP), gate_color)
            # Bottom bar of gate
            bot_top: int = int(gate_bottom)
            if bot_top < int(WALL_BOTTOM):
                pyxel.rect(gx, bot_top, GATE_WIDTH, int(WALL_BOTTOM) - bot_top, gate_color)

            # Gate edge highlights (inner edges of the opening)
            pyxel.rect(gx, top_bottom - GATE_THICKNESS, GATE_WIDTH, GATE_THICKNESS, WHITE)
            pyxel.rect(gx, bot_top, GATE_WIDTH, GATE_THICKNESS, WHITE)

        # ── Ghost sled ──
        ghost_y: float | None = self._get_ghost_y()
        if ghost_y is not None:
            gsx: int = int(SLED_X) - SLED_HALF_W
            gsy: int = int(ghost_y) - SLED_HALF_H
            # Dotted outline using multiple small rects
            for ox in range(0, SLED_W, 4):
                pyxel.rect(gsx + ox, gsy, 2, 1, GRAY)
                pyxel.rect(gsx + ox, gsy + SLED_H - 1, 2, 1, GRAY)
            for oy in range(0, SLED_H, 4):
                pyxel.rect(gsx, gsy + oy, 1, 2, GRAY)
                pyxel.rect(gsx + SLED_W - 1, gsy + oy, 1, 2, GRAY)

        # ── Sled ──
        s_color: int = WHITE
        if self.super_timer > 0:
            s_color = RAINBOW_COLORS[(pyxel.frame_count // 4) % len(RAINBOW_COLORS)]
        sx: int = int(SLED_X) - SLED_HALF_W
        sy: int = int(self.sled_y) - SLED_HALF_H
        pyxel.rect(sx, sy, SLED_W, SLED_H, s_color)
        # Sled highlight
        pyxel.rect(sx + 2, sy + 1, SLED_W - 4, 2, WHITE if self.super_timer == 0 else BLACK)

        # ── Particles ──
        for p in self.particles:
            pcolor: int = p.color if p.life > 5 else (p.color + 1) % 16
            if 2 <= p.life:
                pyxel.circ(int(p.x), int(p.y), 1, pcolor)

        # ── HUD ──
        pyxel.text(4, 2, f"SCORE: {self.score}", WHITE)
        if self.combo > 1:
            combo_text: str = f"COMBO x{self.combo}"
            combo_color_display: int = self.combo_color if self.combo_color >= 0 else WHITE
            pyxel.text(4, 10, combo_text, combo_color_display)
        dist_text: str = f"{int(self.distance)}m"
        pyxel.text(SCREEN_W - len(dist_text) * 4 - 4, 2, dist_text, LIGHT_BLUE)

        # Heat bar at bottom
        heat_bar_y: int = SCREEN_H - 4
        heat_width: int = int((self.heat / MAX_HEAT) * SCREEN_W)
        pyxel.rect(0, heat_bar_y, SCREEN_W, 4, NAVY)
        if heat_width > 0:
            heat_color: int = RED if self.heat < 60 else ORANGE if self.heat < 90 else (RED if pyxel.frame_count % 8 < 4 else ORANGE)
            pyxel.rect(0, heat_bar_y, heat_width, 4, heat_color)

        # SUPER timer bar
        if self.super_timer > 0:
            super_width: int = int((self.super_timer / SUPER_DURATION) * SCREEN_W)
            bar_y: int = SCREEN_H - 8
            pyxel.rect(0, bar_y, super_width, 3, RAINBOW_COLORS[(pyxel.frame_count // 8) % len(RAINBOW_COLORS)])

    # ── GAME OVER ─────────────────────────────────────────────────────────
    def _update_gameover(self) -> None:
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.TITLE

    def _draw_gameover(self) -> None:
        # GAME OVER title
        go_text: str = "GAME OVER"
        go_w: int = len(go_text) * 4
        pyxel.text(SCREEN_W // 2 - go_w // 2, 70, go_text, RED)

        # Stats
        lines: list[str] = [
            f"SCORE: {self.score}",
            f"BEST: {self.best_score}",
            f"MAX COMBO: {self.max_combo}",
            f"DISTANCE: {int(self.distance)}m",
        ]
        for i, line in enumerate(lines):
            lw: int = len(line) * 4
            pyxel.text(SCREEN_W // 2 - lw // 2, 100 + i * 14, line, WHITE)

        # Failure reason
        if self.heat >= MAX_HEAT:
            reason: str = "OVERHEATED!"
            reason_color: int = ORANGE
        else:
            reason = "WALL CRASH!"
            reason_color = RED

        # Only show reason if it was a crash (not heat game over),
        # or show heat in both cases
        if self.heat >= MAX_HEAT:
            rw: int = len(reason) * 4
            pyxel.text(SCREEN_W // 2 - rw // 2, 170, reason, reason_color)
        elif self.shake_frames <= 0:
            # wall crash
            rw = len(reason) * 4
            pyxel.text(SCREEN_W // 2 - rw // 2, 170, reason, reason_color)

        # Retry prompt
        retry: str = "RETRY: ENTER or SPACE"
        rw2: int = len(retry) * 4
        pyxel.text(SCREEN_W // 2 - rw2 // 2, 200, retry, LIGHT_BLUE)

    # ── Core Logic: Gate Spawning ─────────────────────────────────────────
    def _spawn_gate(self) -> Gate:
        """Create a random gate at the right edge of the screen. Pure logic, no pyxel."""
        color: int = self._rng.choice(GATE_COLORS)
        # Opening center Y: clamp so the opening fits between walls
        min_y: float = WALL_TOP + GATE_HALF_OPENING + 4
        max_y: float = WALL_BOTTOM - GATE_HALF_OPENING - 4
        opening_y: float = self._rng.uniform(min_y, max_y)
        return Gate(x=float(SCREEN_W), opening_y=opening_y, color=color)

    # ── Core Logic: Gate Collision ────────────────────────────────────────
    def _check_gate_collision(self, sled_x: float, sled_y: float, gate: Gate) -> bool:
        """Check if the sled passes through a gate's opening. Pure logic."""
        # X overlap: sled's X range must overlap gate's X range
        sled_left: float = sled_x - SLED_HALF_W
        sled_right: float = sled_x + SLED_HALF_W
        gate_left: float = gate.x
        gate_right: float = gate.x + GATE_WIDTH
        if sled_right < gate_left or sled_left > gate_right:
            return False

        # Y overlap: sled must be fully within the gate opening
        gate_top: float = gate.opening_y - GATE_HALF_OPENING
        gate_bottom: float = gate.opening_y + GATE_HALF_OPENING
        return gate_top <= sled_y - SLED_HALF_H and sled_y + SLED_HALF_H <= gate_bottom

    # ── Core Logic: Gate Collection ───────────────────────────────────────
    def _collect_gate(self, gate: Gate) -> None:
        """Process gate collection: update combo, score, SUPER trigger. Pure logic."""
        gate.collected = True

        multiplier: int = 3 if self.super_timer > 0 else 1
        base_score: int = 10

        # Combo logic
        if self.combo == 0:
            self.combo = 1
            self.combo_color = gate.color
            self.score += base_score * multiplier
        elif gate.color == self.combo_color:
            self.combo += 1
            self.score += base_score * multiplier * self.combo
        else:
            self.combo = 1
            self.combo_color = gate.color
            self.score += base_score * multiplier

        # Track max combo
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        # SUPER BOOST trigger
        if self.combo >= COMBO_FOR_SUPER and self.super_timer == 0:
            self.super_timer = SUPER_DURATION
            self._spawn_particles(SLED_X, self.sled_y, YELLOW, 8)

        # Spawn collection particles
        if self.super_timer > 0:
            for c in RAINBOW_COLORS:
                self._spawn_particles(gate.x + GATE_WIDTH / 2, gate.opening_y, c, 2)
        else:
            self._spawn_particles(gate.x + GATE_WIDTH / 2, self.sled_y, gate.color, 10)

    # ── Core Logic: Update Gates ──────────────────────────────────────────
    def _update_gates(self) -> int:
        """Move gates left, detect collections, handle missed gates. Returns count collected. Pure logic."""
        gates_to_remove: list[int] = []
        collected_count: int = 0

        for i, gate in enumerate(self.gates):
            gate.x -= self.track_speed

            # Collection check
            if not gate.collected:
                if self.super_timer > 0:
                    # SUPER: auto-collect all gates whose X overlaps with sled
                    sled_left_check: float = SLED_X - SLED_HALF_W
                    sled_right_check: float = SLED_X + SLED_HALF_W
                    gate_left_check: float = gate.x
                    gate_right_check: float = gate.x + GATE_WIDTH
                    if sled_right_check >= gate_left_check and sled_left_check <= gate_right_check:
                        self._collect_gate(gate)
                        collected_count += 1
                elif self._check_gate_collision(SLED_X, self.sled_y, gate):
                    self._collect_gate(gate)
                    collected_count += 1

            # Missed gate: off-screen left without being collected
            if gate.x + GATE_WIDTH < 0:
                if not gate.collected and self.super_timer == 0:
                    self.heat += HEAT_PER_MISS
                    self._spawn_particles(20.0, self.sled_y, ORANGE, 5)
                gates_to_remove.append(i)

        # Remove off-screen gates in reverse order
        for i in reversed(gates_to_remove):
            del self.gates[i]

        return collected_count

    # ── Core Logic: Sled Movement ─────────────────────────────────────────
    def _move_sled(self, target_y: float) -> float:
        """Move sled toward target_y at max_speed, clamped to walls. Pure logic."""
        dy: float = target_y - self.sled_y
        clamped_dy: float = max(-MAX_SLED_SPEED, min(MAX_SLED_SPEED, dy))
        new_y: float = self.sled_y + clamped_dy
        return max(SLED_MIN_Y, min(SLED_MAX_Y, new_y))

    # ── Core Logic: Particles ─────────────────────────────────────────────
    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        """Create particles at a position with random velocity. Pure logic."""
        for _ in range(count):
            vx: float = self._rng.uniform(-2.0, 1.0)
            vy: float = self._rng.uniform(-3.0, 0.0)
            life: int = self._rng.randint(15, 30)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _update_particles(self) -> None:
        """Update particle positions, apply gravity, remove dead particles. Pure logic."""
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += PARTICLE_GRAVITY
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    # ── Core Logic: Wall Collision ────────────────────────────────────────
    def _check_wall_collision(self, sled_y: float) -> bool:
        """Check if sled has collided with top or bottom wall. Pure logic."""
        return sled_y - SLED_HALF_H <= WALL_TOP or sled_y + SLED_HALF_H >= WALL_BOTTOM

    # ── Core Logic: SUPER BOOST ───────────────────────────────────────────
    def _update_super(self) -> None:
        """Decrement super_timer, handle expiry effects. Pure logic."""
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                # SUPER expired - reset combo
                self.combo = 0
                self.combo_color = -1
                self._spawn_particles(SLED_X, self.sled_y, WHITE, 5)

    # ── Core Logic: Ghost Recording ───────────────────────────────────────
    def _update_ghost(self) -> None:
        """Record current sled position for this run. Pure logic."""
        # Record every 2 frames to keep data manageable
        if self.game_timer % 2 == 0:
            self._ghost_record.append(GhostPoint(x=self.distance, y=self.sled_y))

    def _save_ghost(self) -> None:
        """On game over, promote current run ghost to best_ghost if score is higher."""
        if self.score > self.best_score:
            self.best_score = self.score
            self.best_ghost = list(self._ghost_record)

    def _get_ghost_y(self) -> float | None:
        """Get the ghost sled Y at the current distance. Binary search in best_ghost list."""
        if not self.best_ghost:
            return None
        # Find the GhostPoint with distance closest to current distance
        best_idx: int = 0
        best_dist_diff: float = abs(self.best_ghost[0].x - self.distance)
        for i, gp in enumerate(self.best_ghost):
            diff: float = abs(gp.x - self.distance)
            if diff < best_dist_diff:
                best_dist_diff = diff
                best_idx = i
            elif gp.x > self.distance + 20.0:
                # Early exit: distances are sorted, far ahead
                break
        result: GhostPoint = self.best_ghost[best_idx]
        if best_dist_diff > 30.0:
            return None
        return result.y

    def _find_nearest_gate(self) -> Gate | None:
        """Find the nearest uncollected gate to the sled (for SUPER auto-steer). Pure logic."""
        nearest: Gate | None = None
        nearest_dist: float = float("inf")
        for gate in self.gates:
            if gate.collected:
                continue
            dist: float = abs(gate.x + GATE_WIDTH / 2 - SLED_X)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = gate
        return nearest


if __name__ == "__main__":
    Game()
