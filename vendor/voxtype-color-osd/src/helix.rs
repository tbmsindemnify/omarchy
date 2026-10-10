use cairo::{Context, LineCap, RadialGradient};
use std::f64::consts::{PI, TAU};
#[path = "molecule.rs"]
mod molecule;
#[path = "atlas.rs"]
mod atlas;

pub const STYLE_NAMES: [&str; 10] = [
    "Prismatic sculpted double helix",
    "Polished twin-ribbon spiral",
    "Measured molecular ball-and-stick DNA",
    "Illuminated engineering blueprint helix",
    "Dual-color luminous glass helix",
    "Architectural wire-mesh double helix",
    "Faceted isometric DNA sculpture",
    "Volumetric suspended-particle helix",
    "Mercury-and-opal liquid morph helix",
    "Layered spectral holographic helix",
];

pub const STYLE_IDS: [&str; 10] = ["chromatic","spiral","molecular","blueprint","neon","wireframe","isometric","particles","liquid","hologram"];

#[derive(Clone, Copy, Debug)]
pub struct Frame {
    pub time: f64,
    pub phase: f64,
    pub energy: f64,
    pub compact: f64,
}

#[derive(Default)]
pub struct PhraseCycle {
    elapsed: f64,
    current: usize,
    fade: Option<f64>,
    voiced: f64,
    silence: f64,
    since_change: f64,
    was_visible: bool,
    pending_phrase: bool,
}

impl PhraseCycle {
    pub fn tick(&mut self, visible: bool, speaking: bool, dt: f64) {
        if !dt.is_finite() {
            return;
        }
        let dt = dt.clamp(0.0, 0.1);
        if !visible {
            if self.was_visible && self.voiced >= 0.7 {
                self.pending_phrase = true;
            }
            self.was_visible = false;
            return;
        }
        self.elapsed += dt;
        self.since_change += dt;
        if speaking {
            self.voiced += dt;
            self.silence = 0.0;
        } else {
            self.silence += dt;
        }
        let boundary = self.pending_phrase
            || (self.voiced >= 0.7 && (self.silence >= 0.65 || self.since_change >= 12.0));
        if self.fade.is_none() && boundary && self.since_change >= 2.0 {
            self.fade = Some(0.0);
            self.voiced = 0.0;
            self.pending_phrase = false;
            self.since_change = 0.0;
        }
        if let Some(progress) = &mut self.fade {
            *progress += dt / 1.2;
            if *progress >= 1.0 {
                self.current = (self.current + 1) % STYLE_NAMES.len();
                self.fade = None;
            }
        }
        self.was_visible = true;
    }

    pub fn selection(&self) -> (usize, usize, f64) {
        let t = self.fade.unwrap_or(0.0);
        (
            self.current,
            (self.current + 1) % STYLE_NAMES.len(),
            t * t * (3.0 - 2.0 * t),
        )
    }

    pub fn elapsed(&self) -> f64 {
        self.elapsed
    }
}

pub fn draw_mix(cr: &Context, w: f64, h: f64, from: usize, to: usize, blend: f64, frame: Frame) {
    draw_style(cr, w, h, from, frame);
    if blend > 0.0 {
        cr.push_group();
        cr.set_source_rgb(0.0, 0.0, 0.0);
        let _ = cr.paint();
        draw_style(cr, w, h, to, frame);
        if let Ok(layer) = cr.pop_group() {
            let _ = cr.set_source(&layer);
            let _ = cr.paint_with_alpha(blend.clamp(0.0, 1.0));
        }
    }
}

#[derive(Clone, Copy)]
struct Point {
    x: f64,
    y: f64,
    z: f64,
}
type Color = (f64, f64, f64);

enum Shape {
    Line(Point, Point, f64, Color, f64),
    Dot(Point, f64, Color, f64, bool),
}

#[derive(Clone, Copy)]
struct StrandBounds {
    left: f64,
    top: f64,
    width: f64,
    height: f64,
}

impl StrandBounds {
    fn new(w: f64, h: f64, frame: Frame) -> Self {
        let compact = frame.compact.clamp(0.0, 1.0);
        let width = (w - 48.0).max(w * 0.6) * (1.0 - compact * 0.24);
        let height = (h - 12.0).max(h * 0.4)
            * (0.93 + frame.energy.clamp(0.0, 1.0) * 0.07)
            * (1.0 - compact * 0.12);
        let scale = (width / 640.0).min(height / 88.0);
        let (width, height) = (640.0 * scale, 88.0 * scale);
        Self {
            left: (w - width) * 0.5,
            top: (h - height) * 0.5,
            width,
            height,
        }
    }
}

// All designs share a centered horizontal silhouette; effects cannot resize the popup.
fn fit_shapes(shapes: &mut [Shape], bounds: StrandBounds) {
    let mut left = f64::INFINITY;
    let mut right = f64::NEG_INFINITY;
    let mut top = f64::INFINITY;
    let mut bottom = f64::NEG_INFINITY;
    let mut padding: f64 = 0.0;
    for shape in shapes.iter() {
        let (a, b, r) = match *shape {
            Shape::Line(a, b, width, ..) => (a, b, width * 0.5),
            Shape::Dot(p, r, ..) => (p, p, r),
        };
        left = left.min(a.x).min(b.x);
        right = right.max(a.x).max(b.x);
        top = top.min(a.y).min(b.y);
        bottom = bottom.max(a.y).max(b.y);
        padding = padding.max(r);
    }
    padding = padding.min(bounds.height * 0.2);
    let project = |p: &mut Point| {
        p.x = bounds.left
            + padding
            + (p.x - left) / (right - left).max(1.0) * (bounds.width - padding * 2.0);
        p.y = bounds.top
            + padding
            + (p.y - top) / (bottom - top).max(1.0) * (bounds.height - padding * 2.0);
    };
    for shape in shapes {
        match shape {
            Shape::Line(a, b, ..) => {
                project(a);
                project(b);
            }
            Shape::Dot(p, ..) => project(p),
        }
    }
}

impl Shape {
    fn depth(&self) -> f64 {
        match self {
            Self::Line(a, b, ..) => (a.z + b.z) * 0.5,
            Self::Dot(p, ..) => p.z,
        }
    }
}

fn spectrum(t: f64) -> Color {
    let channel = |offset: f64| 0.24 + 0.76 * (0.5 + 0.5 * (TAU * (t + offset)).cos());
    (channel(0.0), channel(0.67), channel(0.33))
}

fn noise(seed: u32) -> f64 {
    let mut v = seed.wrapping_mul(747796405).wrapping_add(2891336453);
    v = ((v >> ((v >> 28) + 4)) ^ v).wrapping_mul(277803737);
    ((v >> 22) ^ v) as f64 / u32::MAX as f64
}

fn paint(cr: &Context, color: Color, alpha: f64) {
    cr.set_source_rgba(color.0, color.1, color.2, alpha.clamp(0.0, 1.0));
}

fn line(cr: &Context, a: Point, b: Point, width: f64, color: Color, alpha: f64) {
    paint(cr, color, alpha);
    cr.set_line_width(width);
    cr.move_to(a.x, a.y);
    cr.line_to(b.x, b.y);
    let _ = cr.stroke();
}

fn ball(cr: &Context, p: Point, radius: f64, color: Color, alpha: f64, solid: bool) {
    cr.new_sub_path();
    cr.arc(p.x, p.y, radius, 0.0, TAU);
    if solid {
        let g = RadialGradient::new(
            p.x - radius * 0.3,
            p.y - radius * 0.35,
            radius * 0.04,
            p.x,
            p.y,
            radius,
        );
        g.add_color_stop_rgba(
            0.0,
            color.0 * 0.45 + 0.55,
            color.1 * 0.45 + 0.55,
            color.2 * 0.45 + 0.55,
            alpha,
        );
        g.add_color_stop_rgba(0.45, color.0, color.1, color.2, alpha);
        g.add_color_stop_rgba(1.0, color.0 * 0.22, color.1 * 0.22, color.2 * 0.22, alpha);
        let _ = cr.set_source(&g);
    } else {
        paint(cr, color, alpha);
    }
    let _ = cr.fill();
}

fn backdrop(cr: &Context, w: f64, h: f64, style: usize, frame: Frame) {
    if style == 3 {
        paint(cr, (0.06, 0.27, 0.40), 0.8);
        for x in (0..w as usize).step_by(12) {
            cr.move_to(x as f64, 0.0);
            cr.line_to(x as f64, h);
        }
        for y in (0..h as usize).step_by(12) {
            cr.move_to(0.0, y as f64);
            cr.line_to(w, y as f64);
        }
        cr.set_line_width(0.35);
        let _ = cr.stroke();
        cr.set_dash(&[2.0, 4.0], 0.0);
        line(
            cr,
            Point {
                x: 6.0,
                y: h * 0.5,
                z: 0.0,
            },
            Point {
                x: w - 6.0,
                y: h * 0.5,
                z: 0.0,
            },
            0.6,
            (0.5, 0.8, 0.95),
            0.6,
        );
        cr.set_dash(&[], 0.0);
        for x in (12..w as usize - 6).step_by(12) {
            line(
                cr,
                Point {
                    x: x as f64,
                    y: h - 6.0,
                    z: 0.0,
                },
                Point {
                    x: x as f64,
                    y: h - 3.0,
                    z: 0.0,
                },
                0.6,
                (0.5, 0.8, 0.95),
                0.6,
            );
        }
    }
    if style == 9 {
        let scan = 6.0 + (frame.time * 0.32).fract() * (w - 12.0);
        for offset in 0..14 {
            line(
                cr,
                Point {
                    x: scan - offset as f64,
                    y: 5.0,
                    z: 0.0,
                },
                Point {
                    x: scan - offset as f64,
                    y: h - 5.0,
                    z: 0.0,
                },
                1.0,
                (0.12, 0.85, 0.9),
                0.13 * (1.0 - offset as f64 / 14.0),
            );
        }
    }
}

fn draw_molecular(cr: &Context, w: f64, h: f64, frame: Frame) {
    let model = molecule::model();
    let bounds = StrandBounds::new(w, h, frame);
    let angle = frame.phase;
    let mut min_y = f64::INFINITY;
    let mut max_y = f64::NEG_INFINITY;
    for atom in &model.atoms {
        let y = atom.point.1 * angle.cos() - atom.point.2 * angle.sin();
        min_y = min_y.min(y - 0.9);
        max_y = max_y.max(y + 0.9);
    }
    // Uniform scale keeps each measured fragment's atom geometry intact.
    // Repeat the fragment horizontally instead of stretching a short molecule.
    let scale = bounds.height / (max_y - min_y);
    let spacing = model.half_length * 2.0 * scale;
    let copies = (bounds.width / spacing * 0.5).ceil() as i32;
    let project = |p: molecule::Vec3| {
        let y = p.1 * angle.cos() - p.2 * angle.sin();
        let z = p.1 * angle.sin() + p.2 * angle.cos();
        Point {
            x: w * 0.5 + p.0 * scale,
            y: bounds.top + (y - min_y) * scale,
            z,
        }
    };
    let color = |element| match element {
        'O' => (1.0, 0.25, 0.25),
        'N' => (0.25, 0.5, 1.0),
        'P' => (1.0, 0.7, 0.19),
        _ => (0.72, 0.85, 0.83),
    };
    let points: Vec<_> = model.atoms.iter().map(|a| project(a.point)).collect();
    let mut shapes = Vec::with_capacity(model.atoms.len() + model.bonds.len() * 2);
    for &(i, j) in &model.bonds {
        let (a, b) = (points[i], points[j]);
        let mid = Point {
            x: (a.x + b.x) * 0.5,
            y: (a.y + b.y) * 0.5,
            z: (a.z + b.z) * 0.5,
        };
        shapes.push(Shape::Line(
            a,
            mid,
            (scale * 0.26).max(0.5),
            color(model.atoms[i].element),
            0.8,
        ));
        shapes.push(Shape::Line(
            mid,
            b,
            (scale * 0.26).max(0.5),
            color(model.atoms[j].element),
            0.8,
        ));
    }
    for (atom, p) in model.atoms.iter().zip(points) {
        let radius = if atom.element == 'P' { 0.9 } else { 0.65 };
        let light = 0.65 + 0.35 * (p.z / model.radius + 1.0) * 0.5;
        let c = color(atom.element);
        shapes.push(Shape::Dot(
            p,
            (scale * radius).max(0.55),
            (c.0 * light, c.1 * light, c.2 * light),
            1.0,
            true,
        ));
    }
    shapes.sort_by(|a, b| a.depth().total_cmp(&b.depth()));
    // Rasterize the measured fragment once per frame, then reuse it across the strand.
    cr.push_group();
    for shape in &shapes {
        match *shape {
            Shape::Line(a, b, width, c, alpha) => line(cr, a, b, width, c, alpha),
            Shape::Dot(p, r, c, alpha, solid) => ball(cr, p, r, c, alpha, solid),
        }
    }
    let Ok(fragment) = cr.pop_group() else {
        return;
    };
    let _ = cr.save();
    cr.rectangle(bounds.left, bounds.top, bounds.width, bounds.height);
    cr.clip();
    for copy in -copies..=copies {
        let _ = cr.save();
        cr.translate(copy as f64 * spacing, 0.0);
        let _ = cr.set_source(&fragment);
        let _ = cr.paint();
        let _ = cr.restore();
    }
    let _ = cr.restore();
}

pub fn draw_style(cr: &Context, w: f64, h: f64, style: usize, frame: Frame) {
    if w < 24.0 || h < 20.0 { return; }
    atlas::draw(cr,w,h,style,frame.phase,frame.energy,frame.compact);
}

#[allow(dead_code)]
pub fn draw_legacy_style(cr: &Context, w: f64, h: f64, style: usize, frame: Frame) {
    if w < 24.0 || h < 20.0 {
        return;
    }
    let _ = cr.save();
    cr.rectangle(0.0, 0.0, w, h);
    cr.clip();
    cr.set_line_cap(LineCap::Round);
    if style == 2 {
        draw_molecular(cr, w, h, frame);
        let _ = cr.restore();
        return;
    }
    let bounds = StrandBounds::new(w, h, frame);
    // Blueprint grids and holographic scan lines use the same frame too.
    let _ = cr.save();
    cr.rectangle(
        bounds.left - 3.0,
        bounds.top - 3.0,
        bounds.width + 6.0,
        bounds.height + 6.0,
    );
    cr.clip();
    backdrop(cr, w, h, style, frame);
    let _ = cr.restore();
    let e = frame.energy.clamp(0.0, 1.0);
    let compact = frame.compact.clamp(0.0, 1.0);
    let radius = (h * 0.5 - 9.0) * (0.72 + e * 0.19) * (1.0 - compact * 0.12);
    let projection = |u: f64, radial: f64, theta: f64| {
        let world_x = (u - 0.5) * (w - 48.0) * (1.0 - compact * 0.24) / radius;
        let world_y = theta.sin() * radial;
        let world_z = theta.cos() * radial;
        let yaw = if style == 6 {
            0.42
        } else {
            0.12 + (frame.time * 0.18).sin() * 0.10
        };
        let x = world_x * yaw.cos() + world_z * yaw.sin();
        let z = -world_x * yaw.sin() + world_z * yaw.cos();
        let focal = 24.0;
        let perspective = if style == 6 { 1.0 } else { focal / (focal - z) };
        Point {
            x: w * 0.5 + x * radius * perspective,
            y: h * 0.5 + world_y * radius * perspective,
            z,
        }
    };
    let phase_at = |u: f64| u * TAU * (2.1 + compact * 1.0) + frame.phase;
    let tint = |u: f64, strand: usize| -> Color {
        match style {
            3 => (0.64, 0.89, 1.0),
            4 => {
                if strand == 0 {
                    (0.08, 0.95, 0.94)
                } else {
                    (1.0, 0.15, 0.56)
                }
            }
            5 => {
                if strand == 0 {
                    (0.24, 0.82, 1.0)
                } else {
                    (1.0, 0.66, 0.2)
                }
            }
            6 => {
                if strand == 0 {
                    (0.32, 0.85, 0.70)
                } else {
                    (1.0, 0.48, 0.45)
                }
            }
            9 => {
                if strand == 0 {
                    (0.14, 0.9, 1.0)
                } else {
                    (0.52, 1.0, 0.77)
                }
            }
            _ => spectrum(u * 0.6 + strand as f64 * 0.34 + frame.time * 0.025),
        }
    };
    let mut shapes = Vec::with_capacity(3000);
    if style == 7 {
        for i in 0..2200_u32 {
            let u = noise(i * 7 + 1);
            let strand = (i % 2) as usize;
            let theta = phase_at(u) + strand as f64 * PI;
            let across = if i > 1850 {
                noise(i * 7 + 2) * 2.0 - 1.0
            } else {
                1.0
            };
            let mut p = projection(u, across, theta);
            let spread = 0.65 + e * 2.6;
            p.x += (noise(i * 7 + 3) - 0.5) * spread * 2.0;
            p.y += (noise(i * 7 + 4) - 0.5) * spread * 2.0
                + (frame.time * 2.0 + noise(i * 7 + 5) * TAU).sin() * e;
            shapes.push(Shape::Dot(
                p,
                0.35 + noise(i * 7 + 6) * 0.52,
                tint(u, strand),
                0.5 + p.z * 0.25,
                false,
            ));
        }
    } else {
        let samples = 180;
        for strand in 0..2 {
            for i in 0..samples {
                let u = i as f64 / samples as f64;
                let v = (i + 1) as f64 / samples as f64;
                let morph = |t: f64| {
                    if style == 8 {
                        1.0 + 0.11 * (t * 25.0 - frame.time * 2.7).sin() * (0.3 + e)
                    } else {
                        1.0
                    }
                };
                let theta = phase_at(u) + strand as f64 * PI;
                let a = projection(u, morph(u), theta);
                let b = projection(v, morph(v), phase_at(v) + strand as f64 * PI);
                let width = match style {
                    3 | 5 | 9 => 0.8,
                    1 => 3.0,
                    8 => 3.4 + (u * 30.0 - frame.time * 3.0).sin() * 0.9,
                    _ => 2.0,
                };
                let alpha = 0.60 + (a.z + 1.0) * 0.20;
                shapes.push(Shape::Line(a, b, width, tint(u, strand), alpha));
                if style == 5 {
                    for rail in [-0.07, 0.07] {
                        let c = projection(u, 1.0 + rail, theta);
                        let d = projection(v, 1.0 + rail, phase_at(v) + strand as f64 * PI);
                        shapes.push(Shape::Line(c, d, 0.4, tint(u, strand), 0.55));
                    }
                }
                if style == 1 || style == 8 {
                    let mut c = a;
                    let mut d = b;
                    c.y -= 0.6;
                    d.y -= 0.6;
                    shapes.push(Shape::Line(c, d, 0.6, (0.9, 1.0, 1.0), 0.6));
                }
            }
        }
        for i in 0..=28 {
            let u = i as f64 / 28.0;
            let theta = phase_at(u);
            let a = projection(u, 1.0, theta);
            let b = projection(u, 1.0, theta + PI);
            if style != 1 {
                // Split each base-pair rung so depth sorting keeps it inside the backbones.
                for j in 0..10 {
                    let radial = 1.0 - j as f64 * 0.2;
                    shapes.push(Shape::Line(
                        projection(u, radial, theta),
                        projection(u, radial - 0.2, theta),
                        if style == 8 { 1.4 } else { 0.7 },
                        tint(u, if j < 5 { 0 } else { 1 }),
                        if style == 9 { 0.35 } else { 0.65 },
                    ));
                }
            }
            for (strand, p) in [(0, a), (1, b)] {
                if style == 0 || style == 6 {
                    shapes.push(Shape::Dot(
                        p,
                        if style == 6 { 2.2 } else { 1.7 },
                        tint(u, strand),
                        1.0,
                        true,
                    ));
                }
                if style == 5 {
                    let inner = projection(u, 0.93, theta + strand as f64 * PI);
                    let outer = projection(u, 1.07, theta + strand as f64 * PI);
                    shapes.push(Shape::Line(inner, outer, 0.6, tint(u, strand), 0.85));
                }
            }
        }
        if style == 8 || style == 9 {
            for i in 0..72_u32 {
                let u = noise(i * 9 + 1);
                let theta = phase_at(u) + (i % 2) as f64 * PI;
                let mut p = projection(u, 0.7 + 0.35 * noise(i * 9 + 2), theta);
                p.y += (frame.time * 1.4 + noise(i * 9 + 3) * TAU).sin() * 2.0;
                shapes.push(Shape::Dot(
                    p,
                    if style == 8 { 1.2 } else { 0.55 },
                    tint(u, (i % 2) as usize),
                    0.75,
                    style == 8,
                ));
            }
        }
    }
    fit_shapes(&mut shapes, bounds);
    shapes.sort_by(|a, b| a.depth().total_cmp(&b.depth()));
    if style == 4 || style == 9 {
        for shape in &shapes {
            if let Shape::Line(a, b, width, c, _) = shape {
                line(cr, *a, *b, width + 5.0, *c, 0.035);
                line(cr, *a, *b, width + 2.4, *c, 0.08);
            }
        }
    }
    for shape in shapes {
        match shape {
            Shape::Line(a, b, width, c, alpha) => line(cr, a, b, width, c, alpha),
            Shape::Dot(p, r, c, alpha, solid) => ball(cr, p, r, c, alpha, solid),
        }
    }
    if style == 9 {
        paint(cr, (0.0, 0.05, 0.08), 0.4);
        for y in (0..h as usize).step_by(3) {
            cr.rectangle(0.0, y as f64, w, 0.7);
        }
        let _ = cr.fill();
    }
    let _ = cr.restore();
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn detailed_style_names_match_the_design_catalog() {
        let catalog: serde_json::Value = serde_json::from_str(include_str!("../web/styles.json")).unwrap();
        for (i, entry) in catalog.as_array().unwrap().iter().enumerate() {
            assert_eq!(entry["id"], STYLE_IDS[i]);
            assert_eq!(entry["name"], STYLE_NAMES[i]);
            assert!(entry["description"].as_str().unwrap().len() > 140);
            for key in ["material", "depth", "motion"] {
                assert!(entry[key].as_str().unwrap().len() > 20);
            }
        }
    }
    #[test]
    fn long_unbroken_dictation_does_not_stall_the_style_rotation() {
        let mut cycle = PhraseCycle::default();
        for _ in 0..1400 {
            cycle.tick(true, true, 0.01);
        }
        assert_eq!(cycle.selection().0, 1);
    }
    #[test]
    fn molecular_uses_the_same_horizontal_footprint_as_other_strands() {
        use cairo::{Format, ImageSurface};
        let mut surface = ImageSurface::create(Format::ARgb32, 348, 56).unwrap();
        {
            let cr = Context::new(&surface).unwrap();
            draw_style(
                &cr,
                348.0,
                56.0,
                2,
                Frame {
                    time: 1.0,
                    phase: 0.7,
                    energy: 0.65,
                    compact: 0.0,
                },
            );
        }
        let data = surface.data().unwrap();
        let xs: Vec<_> = data
            .chunks_exact(4)
            .enumerate()
            .filter(|(_, p)| p[0].max(p[1]).max(p[2]) > 120)
            .map(|(i, _)| i % 348)
            .collect();
        let width = xs.iter().max().unwrap() - xs.iter().min().unwrap();
        assert!(
            width >= 285 && width <= 305,
            "molecular width was {width}, expected about 300"
        );
    }

    #[test]
    fn all_designs_share_bounds_at_every_rotation_and_response_extreme() {
        use cairo::{Format, ImageSurface};
        for (w, h) in [(180, 40), (348, 56), (468, 100)] {
            for (energy, compact) in [(0.0, 0.0), (0.65, 0.4), (1.0, 1.0)] {
                for phase in [0.0, 1.5, 3.0, 4.5] {
                    let frame = Frame {
                        time: 2.0,
                        phase,
                        energy,
                        compact,
                    };
                    let target = StrandBounds::new(w as f64, h as f64, frame);
                    for style in 0..STYLE_NAMES.len() {
                        let mut surface = ImageSurface::create(Format::ARgb32, w, h).unwrap();
                        {
                            let cr = Context::new(&surface).unwrap();
                            draw_style(&cr, w as f64, h as f64, style, frame);
                        }
                        let data = surface.data().unwrap();
                        let mut left = w;
                        let mut right = 0;
                        let mut top = h;
                        let mut bottom = 0;
                        for (i, p) in data.chunks_exact(4).enumerate() {
                            if p[0].max(p[1]).max(p[2]) > 100 {
                                let (x, y) = ((i % w as usize) as i32, (i / w as usize) as i32);
                                left = left.min(x);
                                right = right.max(x);
                                top = top.min(y);
                                bottom = bottom.max(y);
                            }
                        }
                        let name = STYLE_NAMES[style];
                        assert!(
                            left > 0 && right < w - 1 && top > 0 && bottom < h - 1,
                            "{name} clips {w}x{h}: {left},{top}..{right},{bottom}"
                        );
                        assert!(
                            ((right - left + 1) as f64 - target.width).abs()
                                < target.width * 0.07 + 2.0,
                            "{name} width {} != {} at phase {phase}",
                            right - left + 1,
                            target.width
                        );
                        assert!(
                            ((bottom - top + 1) as f64 - target.height).abs() < 6.0,
                            "{name} height {} != {}",
                            bottom - top + 1,
                            target.height
                        );
                        assert!(
                            ((left + right) as f64 * 0.5 - w as f64 * 0.5).abs() < 4.0,
                            "{name} off center: {left}..{right}, {w}x{h}, phase {phase}"
                        );
                    }
                }
            }
        }
    }
    #[test]
    fn phrase_pauses_advance_once_and_wrap_all_styles() {
        let mut cycle = PhraseCycle::default();
        for style in 0..10 {
            assert_eq!(cycle.selection().0, style);
            for _ in 0..200 {
                cycle.tick(true, true, 0.01);
            }
            assert_eq!(cycle.selection().0, style);
            for _ in 0..100 {
                cycle.tick(true, false, 0.01);
            }
            assert!(cycle.selection().2 > 0.0 && cycle.selection().2 < 1.0);
            for _ in 0..300 {
                cycle.tick(true, false, 0.01);
            }
            assert_eq!(cycle.selection().0, (style + 1) % 10);
            for _ in 0..200 {
                cycle.tick(true, false, 0.01);
            }
            assert_eq!(cycle.selection().0, (style + 1) % 10);
        }
    }

    #[test]
    fn idle_does_not_skip_styles_and_recordings_continue_the_sequence() {
        let mut clock = PhraseCycle::default();
        for _ in 0..200 {
            clock.tick(true, true, 0.02);
        }
        assert_eq!(clock.selection().0, 0);
        let elapsed = clock.elapsed();
        clock.tick(false, false, 1000.0);
        clock.tick(false, false, 1000.0);
        assert_eq!(clock.elapsed(), elapsed);
        clock.tick(true, true, 0.02);
        assert!(clock.selection().2 > 0.0);
        for _ in 0..65 {
            clock.tick(true, true, 0.02);
        }
        assert_eq!(clock.selection().0, 1);
    }

    #[test]
    fn short_breaths_do_not_switch_styles() {
        let mut cycle = PhraseCycle::default();
        for _ in 0..5 {
            for _ in 0..80 {
                cycle.tick(true, true, 0.01);
            }
            for _ in 0..30 {
                cycle.tick(true, false, 0.01);
            }
        }
        assert_eq!(cycle.selection(), (0, 1, 0.0));
    }

    #[test]
    fn syllabic_phrases_advance_even_with_brief_startup_delay() {
        let mut cycle = PhraseCycle::default();
        for style in 0..10 {
            for i in 20..300 {
                let time = i as f64 * 0.01;
                cycle.tick(true, (time * 5.0).fract() < 0.40, 0.01);
            }
            for _ in 0..220 {
                cycle.tick(true, false, 0.01);
            }
            assert_eq!(cycle.selection().0, (style + 1) % 10);
        }
    }

    #[test]
    fn all_modes_render_move_and_remain_distinct_at_both_sizes() {
        use cairo::{Format, ImageSurface};
        for (w, h) in [(360, 56), (480, 100)] {
            let mut hashes = std::collections::HashSet::new();
            for style in 0..STYLE_NAMES.len() {
                let mut prior = None;
                for sample in 0..2 {
                    let mut surface = ImageSurface::create(Format::ARgb32, w, h).unwrap();
                    {
                        let cr = Context::new(&surface).unwrap();
                        cr.set_source_rgb(0.0, 0.0, 0.0);
                        cr.paint().unwrap();
                        draw_style(
                            &cr,
                            w as f64,
                            h as f64,
                            style,
                            Frame {
                                time: sample as f64,
                                phase: sample as f64 * 0.9,
                                energy: 0.65,
                                compact: 0.4,
                            },
                        );
                    }
                    surface.flush();
                    let data = surface.data().unwrap();
                    let hash = data
                        .iter()
                        .fold(0_u64, |a, &b| a.wrapping_mul(31).wrapping_add(b as u64));
                    let lit = data
                        .chunks_exact(4)
                        .filter(|p| p[0].max(p[1]).max(p[2]) > 30)
                        .count();
                    assert!(lit > 100, "blank {}", STYLE_NAMES[style]);
                    if let Some(last) = prior {
                        assert_ne!(last, hash, "frozen {}", STYLE_NAMES[style]);
                    } else {
                        assert!(hashes.insert(hash), "duplicate {}", STYLE_NAMES[style]);
                    }
                    prior = Some(hash);
                }
            }
        }
    }

    #[test]
    fn transition_endpoint_matches_next_style() {
        use cairo::{Format, ImageSurface};
        let render = |mix: bool| {
            let mut surface = ImageSurface::create(Format::ARgb32, 360, 56).unwrap();
            {
                let cr = Context::new(&surface).unwrap();
                cr.set_source_rgb(0.0, 0.0, 0.0);
                cr.paint().unwrap();
                let frame = Frame {
                    time: 1.0,
                    phase: 0.4,
                    energy: 0.5,
                    compact: 0.4,
                };
                if mix {
                    draw_mix(&cr, 360.0, 56.0, 3, 4, 1.0, frame);
                } else {
                    draw_style(&cr, 360.0, 56.0, 4, frame);
                }
            }
            surface.flush();
            let data = surface.data().unwrap().to_vec();
            data
        };
        assert_eq!(render(true), render(false));
    }
}
