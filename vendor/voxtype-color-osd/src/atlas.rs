//! Offline Three.js geometry renders; playback remains native and audio-driven.
use cairo::{Context, Filter, ImageSurface};
use std::{cell::RefCell, collections::VecDeque, io::Cursor};

const FRAMES: usize = 96;
const TILE_W: f64 = 696.0;
const TILE_H: f64 = 112.0;
const IMAGES: [&[u8]; 10] = [
    include_bytes!("../assets/style-0.png"),
    include_bytes!("../assets/style-1.png"),
    include_bytes!("../assets/style-2.png"),
    include_bytes!("../assets/style-3.png"),
    include_bytes!("../assets/style-4.png"),
    include_bytes!("../assets/style-5.png"),
    include_bytes!("../assets/style-6.png"),
    include_bytes!("../assets/style-7.png"),
    include_bytes!("../assets/style-8.png"),
    include_bytes!("../assets/style-9.png"),
];

thread_local! {
    // A transition needs only its outgoing and incoming atlases, not all ten.
    static CACHE: RefCell<VecDeque<(usize, ImageSurface)>> = const { RefCell::new(VecDeque::new()) };
}

fn atlas(style: usize) -> ImageSurface {
    CACHE.with_borrow_mut(|cache| {
        if let Some(index) = cache.iter().position(|(id, _)| *id == style) {
            let entry = cache.remove(index).unwrap();
            let image = entry.1.clone();
            cache.push_back(entry);
            return image;
        }
        let image = ImageSurface::create_from_png(&mut Cursor::new(IMAGES[style]))
            .expect("verified embedded DNA animation atlas");
        assert_eq!((image.width(), image.height()), (8352, 896));
        if cache.len() == 2 {
            cache.pop_front();
        }
        cache.push_back((style, image.clone()));
        image
    })
}

pub fn draw(cr: &Context, w: f64, h: f64, style: usize, phase: f64, energy: f64, compact: f64) {
    let image = atlas(style % IMAGES.len());
    let phase = if phase.is_finite() { phase } else { 0.0 };
    let position = phase.rem_euclid(std::f64::consts::TAU) / std::f64::consts::TAU * FRAMES as f64;
    let frame = position.floor() as usize;
    let blend = position.fract();
    let compact = compact.clamp(0.0, 1.0);
    let width = (w - 48.0).max(w * 0.6) * (1.0 - compact * 0.24);
    let height =
        (h - 12.0).max(h * 0.4) * (0.93 + energy.clamp(0.0, 1.0) * 0.07) * (1.0 - compact * 0.12);
    let _ = cr.save();
    let scale = (width / 640.0).min(height / 88.0);
    // The same two-pixel effect margin applies to bloom, particles and solid styles.
    cr.rectangle(
        w * 0.5 - 320.0 * scale - 2.0,
        h * 0.5 - 44.0 * scale - 2.0,
        640.0 * scale + 4.0,
        88.0 * scale + 4.0,
    );
    cr.clip();
    cr.translate(w * 0.5, h * 0.5);
    cr.scale(scale, scale);
    cr.translate(-TILE_W * 0.5, -TILE_H * 0.5);
    cr.rectangle(0.0, 0.0, TILE_W, TILE_H);
    cr.clip();
    for (sample, alpha) in [(frame, 1.0), ((frame + 1) % FRAMES, blend)] {
        if alpha == 0.0 {
            continue;
        }
        let x = (sample % 12) as f64 * TILE_W;
        let y = (sample / 12) as f64 * TILE_H;
        let _ = cr.set_source_surface(&image, -x, -y);
        cr.source().set_filter(Filter::Bilinear);
        let _ = cr.paint_with_alpha(alpha);
    }
    let _ = cr.restore();
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn all_atlases_are_complete_and_cache_is_bounded() {
        for style in 0..10 {
            let _ = atlas(style);
        }
        CACHE.with_borrow(|cache| assert_eq!(cache.len(), 2));
    }

    #[test]
    fn full_turn_wraps_without_a_visual_jump() {
        let render = |phase| {
            let mut surface = ImageSurface::create(cairo::Format::ARgb32, 348, 56).unwrap();
            {
                let cr = Context::new(&surface).unwrap();
                draw(&cr, 348.0, 56.0, 0, phase, 0.65, 0.3);
            }
            let pixels = surface.data().unwrap().to_vec();
            pixels
        };
        assert_eq!(render(0.0), render(std::f64::consts::TAU));
    }
}
