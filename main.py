"""
Magic Kaleido-Pop Studio
========================
A creative, family-friendly Python mobile game built with Kivy for Android & Desktop.
Designed for all ages (Kids, Teens, and Adults) with zero data collection (Google Play Families Policy compliant).

Three Interactive Game Modes:
1. Kaleido-Draw (All Ages / Teens & Adults):
   - Draw mesmerizing glowing neon mandalas with 1x, 4x, 8x, or 12x radial symmetry.
   - Auto-cycling rainbow brush or custom neon palette, adjustable brush sizes, and particle trails.
2. Bubble Pop Blitz (Kids & Arcade Fans):
   - Colourful floating paint bubbles drift upwards with physics.
   - Tap to pop them into vibrant paint splatters and fireworks!
   - Build combo multipliers, pop Golden Star Bubbles, and beat your High Score.
3. Magic Stamps & Fireworks (Toddlers & Creative Play):
   - Every tap or drag launches dazzling firework bursts, geometric stars, and concentric neon rings.

How to Run on Desktop (for testing):
    pip install kivy
    python main.py

How to Package for Android (.aab for Google Play Store):
    See buildozer.spec and PLAY_STORE_LAUNCH_GUIDE.md
     Docs: https://kivy.org/doc/stable/guide/packaging-android.html
"""

import colorsys
import json
import math
import os
import random

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, InstructionGroup, Line, Rectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

# Set a dark cosmic background so neon colors pop vividly
Window.clearcolor = (0.05, 0.05, 0.10, 1)


NEON_PALETTE = [
    ("Rainbow", None),             # Auto-cycling hue
    ("Neon Pink", (1.0, 0.15, 0.55)),
    ("Electric Cyan", (0.0, 0.95, 1.0)),
    ("Laser Lime", (0.25, 1.0, 0.2)),
    ("Solar Gold", (1.0, 0.85, 0.1)),
    ("Violet Glow", (0.7, 0.25, 1.0)),
    ("Coral Sunset", (1.0, 0.4, 0.2)),
]


class Particle:
    """Lightweight animated spark/splatter particle rendered on the Kivy canvas."""

    def __init__(self, x, y, vx, vy, radius, rgb, decay=1.4):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = radius
        self.r, self.g, self.b = rgb
        self.alpha = 1.0
        self.decay = decay

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy -= dp(80) * dt  # Gentle gravity
        self.alpha -= self.decay * dt
        self.radius = max(0.5, self.radius * (1.0 - 0.5 * dt))
        return self.alpha > 0


class FloatingBubble:
    """Interactive floating color bubble for Bubble Pop Blitz mode."""

    def __init__(self, canvas_w, canvas_h):
        self.radius = random.uniform(dp(26), dp(48))
        self.x = random.uniform(self.radius + dp(10), max(self.radius + dp(20), canvas_w - self.radius - dp(10)))
        self.y = -self.radius
        self.vy = random.uniform(dp(75), dp(165))
        self.wobble_speed = random.uniform(2.0, 4.5)
        self.wobble_amp = random.uniform(dp(18), dp(45))
        self.phase = random.uniform(0, math.pi * 2)
        self.is_golden = random.random() < 0.15
        if self.is_golden:
            self.rgb = (1.0, 0.88, 0.15)
            self.points = 50
            self.vy *= 1.25
        else:
            hue = random.random()
            self.rgb = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
            self.points = 10

    def update(self, dt):
        self.y += self.vy * dt
        self.phase += self.wobble_speed * dt
        self.x += math.sin(self.phase) * self.wobble_amp * dt

    def contains(self, tx, ty):
        dx = tx - self.x
        dy = ty - self.y
        # Slightly generous hit-box so young kids can pop bubbles easily
        return (dx * dx + dy * dy) <= (self.radius * 1.2) ** 2


class CreativeCanvas(Widget):
    """Main interactive multi-mode touch canvas."""

    def __init__(self, status_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.status_callback = status_callback

        # Modes: 'kaleido', 'bubbles', 'fireworks'
        self.mode = "kaleido"
        self.symmetry = 8  # 1, 4, 8, 12
        self.brush_size = dp(4.5)
        self.color_index = 0  # 0 = Rainbow auto-cycle
        self.hue = 0.0

        # Persistent drawing layer vs dynamic animated layer
        self.artwork_group = InstructionGroup()
        self.dynamic_group = InstructionGroup()
        self.canvas.add(self.artwork_group)
        self.canvas.add(self.dynamic_group)

        # Active state
        self.particles = []
        self.bubbles = []
        self.bubble_spawn_timer = 0.0
        self.score = 0
        self.combo = 0
        self.combo_timer = 0.0
        self.high_score = self._load_high_score()

        # History of stroke InstructionGroups for Undo
        self.strokes = []
        self._active_touch_strokes = {}

        # 60 FPS update loop
        Clock.schedule_interval(self.update_frame, 1.0 / 60.0)

    def _get_save_path(self):
        app = App.get_running_app()
        base_dir = app.user_data_dir if app else "."
        return os.path.join(base_dir, "kaleido_pop_save.json")

    def _load_high_score(self):
        try:
            path = self._get_save_path()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return int(data.get("high_score", 0))
        except Exception:
            pass
        return 0

    def _save_high_score(self):
        try:
            path = self._get_save_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"high_score": self.high_score}, f)
        except Exception:
            pass

    def get_current_rgb(self, step_hue=True):
        if step_hue:
            self.hue = (self.hue + 0.008) % 1.0
        _, fixed_rgb = NEON_PALETTE[self.color_index]
        if fixed_rgb is None:
            return colorsys.hsv_to_rgb(self.hue, 0.85, 1.0)
        return fixed_rgb

    def clear_canvas(self):
        self.artwork_group.clear()
        self.strokes.clear()
        self.particles.clear()
        self.bubbles.clear()
        self._notify_status()

    def undo_last_stroke(self):
        if self.strokes:
            last_group = self.strokes.pop()
            self.artwork_group.remove(last_group)
            self._notify_status()

    def spawn_burst(self, x, y, rgb=None, count=24, speed_scale=1.0):
        if rgb is None:
            rgb = self.get_current_rgb()
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(dp(40), dp(220)) * speed_scale
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            rad = random.uniform(dp(3), dp(9))
            # Slight hue variation per spark
            jitter_r = min(1.0, max(0.1, rgb[0] + random.uniform(-0.12, 0.12)))
            jitter_g = min(1.0, max(0.1, rgb[1] + random.uniform(-0.12, 0.12)))
            jitter_b = min(1.0, max(0.1, rgb[2] + random.uniform(-0.12, 0.12)))
            self.particles.append(
                Particle(x, y, vx, vy, rad, (jitter_r, jitter_g, jitter_b), decay=random.uniform(1.1, 2.0))
            )

    def stamp_splatter_on_artwork(self, x, y, rgb, radius):
        """Leaves a permanent colorful paint splatter on the background canvas when a bubble pops!"""
        splat = InstructionGroup()
        r, g, b = rgb
        splat.add(Color(r, g, b, 0.35))
        main_d = radius * 1.4
        splat.add(Ellipse(pos=(x - main_d / 2, y - main_d / 2), size=(main_d, main_d)))
        for _ in range(6):
            ang = random.uniform(0, math.pi * 2)
            dist = random.uniform(radius * 0.5, radius * 1.2)
            drop_r = random.uniform(dp(4), dp(12))
            dx = x + math.cos(ang) * dist - drop_r / 2
            dy = y + math.sin(ang) * dist - drop_r / 2
            splat.add(Ellipse(pos=(dx, dy), size=(drop_r, drop_r)))
        self.artwork_group.add(splat)
        self.strokes.append(splat)

    def stamp_star_shape(self, x, y, rgb):
        """Draws a geometric glowing star + concentric ring in Magic Stamps mode."""
        star_group = InstructionGroup()
        r, g, b = rgb
        outer_r = random.uniform(dp(24), dp(52))
        inner_r = outer_r * 0.45
        points = []
        spikes = random.choice([5, 6, 8])
        rot = random.uniform(0, math.pi)
        for i in range(spikes * 2 + 1):
            rad = outer_r if i % 2 == 0 else inner_r
            ang = rot + (i * math.pi / spikes)
            points.extend([x + math.cos(ang) * rad, y + math.sin(ang) * rad])

        # Outer glow
        star_group.add(Color(r, g, b, 0.28))
        star_group.add(Line(points=points, width=dp(6), joint="round", cap="round"))
        # Crisp core
        star_group.add(Color(min(1.0, r + 0.25), min(1.0, g + 0.25), min(1.0, b + 0.25), 0.95))
        star_group.add(Line(points=points, width=dp(2.2), joint="round", cap="round"))

        self.artwork_group.add(star_group)
        self.strokes.append(star_group)

    def _get_symmetry_points(self, x, y):
        cx, cy = self.center_x, self.center_y
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy)
        base_angle = math.atan2(dy, dx)
        pts = []
        n = max(1, self.symmetry)
        for i in range(n):
            ang = base_angle + (2.0 * math.pi * i / n)
            px = cx + math.cos(ang) * dist
            py = cy + math.sin(ang) * dist
            pts.append((px, py))
        return pts

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False

        x, y = touch.pos
        rgb = self.get_current_rgb()

        if self.mode == "bubbles":
            popped_any = False
            for b in list(self.bubbles):
                if b.contains(x, y):
                    self.bubbles.remove(b)
                    popped_any = True
                    self.combo += 1
                    self.combo_timer = 2.0
                    earned = b.points * min(5, max(1, self.combo // 3 + 1))
                    self.score += earned
                    if self.score > self.high_score:
                        self.high_score = self.score
                        self._save_high_score()
                    self.spawn_burst(b.x, b.y, b.rgb, count=28 if b.is_golden else 18, speed_scale=1.2)
                    self.stamp_splatter_on_artwork(b.x, b.y, b.rgb, b.radius)
            if not popped_any:
                # Even tapping empty space gives a playful mini spark for toddlers
                self.spawn_burst(x, y, rgb, count=8, speed_scale=0.6)
            self._notify_status()
            return True

        elif self.mode == "fireworks":
            self.stamp_star_shape(x, y, rgb)
            self.spawn_burst(x, y, rgb, count=30, speed_scale=1.3)
            self._notify_status()
            return True

        # Default: Kaleido-Draw Mode
        stroke_group = InstructionGroup()
        r, g, b = rgb
        sym_pts = self._get_symmetry_points(x, y)
        glow_lines = []
        core_lines = []

        # Outer neon halo
        stroke_group.add(Color(r, g, b, 0.28))
        for px, py in sym_pts:
            gl = Line(points=[px, py], width=self.brush_size * 2.4, cap="round", joint="round")
            stroke_group.add(gl)
            glow_lines.append(gl)

        # Bright inner core
        stroke_group.add(Color(min(1.0, r + 0.2), min(1.0, g + 0.2), min(1.0, b + 0.2), 0.95))
        for px, py in sym_pts:
            cl = Line(points=[px, py], width=self.brush_size, cap="round", joint="round")
            stroke_group.add(cl)
            core_lines.append(cl)

        self.artwork_group.add(stroke_group)
        self.strokes.append(stroke_group)
        self._active_touch_strokes[touch.uid] = (glow_lines, core_lines)
        self.spawn_burst(x, y, rgb, count=5, speed_scale=0.5)
        return True

    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos):
            return False

        x, y = touch.pos
        rgb = self.get_current_rgb()

        if self.mode == "bubbles":
            # Swipe-to-pop! Kids love slicing through bubbles
            for b in list(self.bubbles):
                if b.contains(x, y):
                    self.bubbles.remove(b)
                    self.combo += 1
                    self.combo_timer = 2.0
                    self.score += b.points * min(5, max(1, self.combo // 3 + 1))
                    if self.score > self.high_score:
                        self.high_score = self.score
                        self._save_high_score()
                    self.spawn_burst(b.x, b.y, b.rgb, count=18, speed_scale=1.0)
                    self.stamp_splatter_on_artwork(b.x, b.y, b.rgb, b.radius)
            self._notify_status()
            return True

        elif self.mode == "fireworks":
            if random.random() < 0.35:
                self.stamp_star_shape(x, y, rgb)
                self.spawn_burst(x, y, rgb, count=14, speed_scale=0.9)
            return True

        # Kaleido-Draw continuation
        if touch.uid in self._active_touch_strokes:
            glow_lines, core_lines = self._active_touch_strokes[touch.uid]
            sym_pts = self._get_symmetry_points(x, y)
            for idx, (px, py) in enumerate(sym_pts):
                if idx < len(glow_lines):
                    glow_lines[idx].points += [px, py]
                    core_lines[idx].points += [px, py]
            if random.random() < 0.4:
                self.spawn_burst(x, y, rgb, count=2, speed_scale=0.4)
        return True

    def on_touch_up(self, touch):
        if touch.uid in self._active_touch_strokes:
            del self._active_touch_strokes[touch.uid]
        return True

    def _notify_status(self):
        if self.status_callback:
            self.status_callback()

    def update_frame(self, dt):
        # Update combo decay
        if self.combo > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 0
                self._notify_status()

        # Spawn and move bubbles in Bubble Pop Blitz mode
        if self.mode == "bubbles" and self.width > 50 and self.height > 50:
            self.bubble_spawn_timer -= dt
            if self.bubble_spawn_timer <= 0 and len(self.bubbles) < 18:
                self.bubbles.append(FloatingBubble(self.width, self.height))
                self.bubble_spawn_timer = random.uniform(0.28, 0.65)

            for b in list(self.bubbles):
                b.update(dt)
                if b.y - b.radius > self.height:
                    self.bubbles.remove(b)

        # Update particles
        self.particles = [p for p in self.particles if p.update(dt)]

        # Redraw dynamic layer (bubbles, kaleidoscope guide center, particles)
        self.dynamic_group.clear()

        # Subtle center guide in Kaleido mode
        if self.mode == "kaleido" and self.symmetry > 1:
            self.dynamic_group.add(Color(1, 1, 1, 0.14))
            r = dp(5)
            self.dynamic_group.add(Ellipse(pos=(self.center_x - r, self.center_y - r), size=(r * 2, r * 2)))

        # Draw bubbles
        for b in self.bubbles:
            r, g, bl = b.rgb
            # Outer bubble body
            self.dynamic_group.add(Color(r, g, bl, 0.78))
            d = b.radius * 2
            self.dynamic_group.add(Ellipse(pos=(b.x - b.radius, b.y - b.radius), size=(d, d)))
            # Shiny rim
            self.dynamic_group.add(Color(1, 1, 1, 0.85 if b.is_golden else 0.45))
            self.dynamic_group.add(Line(circle=(b.x, b.y, b.radius), width=dp(2.2 if b.is_golden else 1.3)))
            # Specular highlight dot
            hl_r = b.radius * 0.25
            hx = b.x - b.radius * 0.35 - hl_r
            hy = b.y + b.radius * 0.35 - hl_r
            self.dynamic_group.add(Color(1, 1, 1, 0.65))
            self.dynamic_group.add(Ellipse(pos=(hx, hy), size=(hl_r * 2, hl_r * 2)))

        # Draw particles
        for p in self.particles:
            self.dynamic_group.add(Color(p.r, p.g, p.b, max(0.0, min(1.0, p.alpha))))
            d = p.radius * 2
            self.dynamic_group.add(Ellipse(pos=(p.x - p.radius, p.y - p.radius), size=(d, d)))


class MagicKaleidoPopApp(App):
    """Main Kivy Application."""

    def build(self):
        self.title = "Magic Kaleido-Pop Studio"
        root = BoxLayout(orientation="vertical")

        # --- TOP HEADER BAR ---
        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(54),
            padding=[dp(10), dp(6)],
            spacing=dp(8),
        )
        with header.canvas.before:
            Color(0.10, 0.11, 0.20, 1)
            self.header_bg = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)

        self.title_label = Label(
            text="[b]MAGIC KALEIDO-POP[/b]",
            markup=True,
            font_size=sp(17),
            halign="left",
            valign="middle",
            size_hint_x=0.48,
            color=(0.95, 0.95, 1.0, 1),
        )
        self.title_label.bind(size=self.title_label.setter("text_size"))

        self.score_label = Label(
            text="Mode: [b]Kaleido 8x[/b]  |  Best: 0",
            markup=True,
            font_size=sp(14),
            halign="right",
            valign="middle",
            size_hint_x=0.52,
            color=(0.4, 0.95, 1.0, 1),
        )
        self.score_label.bind(size=self.score_label.setter("text_size"))

        header.add_widget(self.title_label)
        header.add_widget(self.score_label)

        # --- MIDDLE INTERACTIVE CANVAS ---
        canvas_container = FloatLayout()
        self.game_canvas = CreativeCanvas(status_callback=self.refresh_status_bar)
        canvas_container.add_widget(self.game_canvas)

        # --- BOTTOM MODE & TOOL CONTROLS ---
        controls = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(108),
            padding=[dp(8), dp(6)],
            spacing=dp(6),
        )
        with controls.canvas.before:
            Color(0.09, 0.10, 0.18, 1)
            self.controls_bg = Rectangle(pos=controls.pos, size=controls.size)
        controls.bind(pos=self._update_controls_bg, size=self._update_controls_bg)

        # Row 1: Game Modes
        mode_row = BoxLayout(orientation="horizontal", spacing=dp(6))
        self.btn_mode_kaleido = self._make_button(
            "Kaleido-Draw", (0.45, 0.20, 0.85, 1), self.set_mode_kaleido
        )
        self.btn_mode_bubbles = self._make_button(
            "Bubble Blitz", (0.10, 0.65, 0.85, 1), self.set_mode_bubbles
        )
        self.btn_mode_fireworks = self._make_button(
            "Firework Stamps", (0.85, 0.25, 0.55, 1), self.set_mode_fireworks
        )
        mode_row.add_widget(self.btn_mode_kaleido)
        mode_row.add_widget(self.btn_mode_bubbles)
        mode_row.add_widget(self.btn_mode_fireworks)

        # Row 2: Creative Tools (Symmetry, Color, Brush, Undo, Clear)
        tool_row = BoxLayout(orientation="horizontal", spacing=dp(6))
        self.btn_symmetry = self._make_button(
            "Sym: 8x", (0.20, 0.25, 0.42, 1), self.cycle_symmetry
        )
        self.btn_color = self._make_button(
            "Color: Rainbow", (0.22, 0.55, 0.35, 1), self.cycle_color
        )
        self.btn_brush = self._make_button(
            "Size: Med", (0.20, 0.25, 0.42, 1), self.cycle_brush_size
        )
        self.btn_undo = self._make_button(
            "Undo", (0.55, 0.45, 0.15, 1), lambda *_: self.game_canvas.undo_last_stroke()
        )
        self.btn_clear = self._make_button(
            "Clear", (0.75, 0.20, 0.25, 1), lambda *_: self.game_canvas.clear_canvas()
        )

        tool_row.add_widget(self.btn_symmetry)
        tool_row.add_widget(self.btn_color)
        tool_row.add_widget(self.btn_brush)
        tool_row.add_widget(self.btn_undo)
        tool_row.add_widget(self.btn_clear)

        controls.add_widget(mode_row)
        controls.add_widget(tool_row)

        root.add_widget(header)
        root.add_widget(canvas_container)
        root.add_widget(controls)

        self.refresh_status_bar()
        return root

    def _make_button(self, text, bg_color, callback):
        btn = Button(
            text=text,
            bold=True,
            font_size=sp(13),
            background_normal="",
            background_color=bg_color,
            color=(1, 1, 1, 1),
        )
        btn.bind(on_release=callback)
        return btn

    def _update_header_bg(self, instance, _):
        self.header_bg.pos = instance.pos
        self.header_bg.size = instance.size

    def _update_controls_bg(self, instance, _):
        self.controls_bg.pos = instance.pos
        self.controls_bg.size = instance.size

    def set_mode_kaleido(self, *_):
        self.game_canvas.mode = "kaleido"
        self.game_canvas.bubbles.clear()
        self.refresh_status_bar()

    def set_mode_bubbles(self, *_):
        self.game_canvas.mode = "bubbles"
        self.refresh_status_bar()

    def set_mode_fireworks(self, *_):
        self.game_canvas.mode = "fireworks"
        self.game_canvas.bubbles.clear()
        self.refresh_status_bar()

    def cycle_symmetry(self, *_):
        options = [1, 4, 8, 12]
        idx = (options.index(self.game_canvas.symmetry) + 1) % len(options)
        self.game_canvas.symmetry = options[idx]
        self.btn_symmetry.text = f"Sym: {self.game_canvas.symmetry}x"
        self.refresh_status_bar()

    def cycle_color(self, *_):
        self.game_canvas.color_index = (self.game_canvas.color_index + 1) % len(NEON_PALETTE)
        name, rgb = NEON_PALETTE[self.game_canvas.color_index]
        self.btn_color.text = f"Color: {name.split()[0]}"
        if rgb is not None:
            self.btn_color.background_color = (rgb[0] * 0.7, rgb[1] * 0.7, rgb[2] * 0.7, 1)
        else:
            self.btn_color.background_color = (0.22, 0.55, 0.35, 1)

    def cycle_brush_size(self, *_):
        sizes = [("Thin", dp(2.5)), ("Med", dp(4.5)), ("Thick", dp(8.0)), ("Mega", dp(12.0))]
        current_label = self.btn_brush.text.replace("Size: ", "")
        labels = [s[0] for s in sizes]
        next_idx = (labels.index(current_label) + 1) % len(sizes) if current_label in labels else 0
        label, val = sizes[next_idx]
        self.game_canvas.brush_size = val
        self.btn_brush.text = f"Size: {label}"

    def refresh_status_bar(self):
        c = self.game_canvas
        if c.mode == "bubbles":
            combo_txt = f" (x{min(5, max(1, c.combo // 3 + 1))}!)" if c.combo >= 3 else ""
            self.score_label.text = f"[b]Score: {c.score}{combo_txt}[/b]  |  Best: {c.high_score}"
        elif c.mode == "fireworks":
            self.score_label.text = f"Mode: [b]Firework Stamps[/b]  |  Best: {c.high_score}"
        else:
            self.score_label.text = f"Mode: [b]Kaleido {c.symmetry}x[/b]  |  Best: {c.high_score}"


if __name__ == "__main__":
    MagicKaleidoPopApp().run()