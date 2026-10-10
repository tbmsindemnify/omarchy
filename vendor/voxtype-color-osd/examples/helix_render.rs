#[path = "../src/helix.rs"]
mod helix;

use cairo::{Context, Format, ImageSurface};
use std::io::Write;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let dir = std::env::args().nth(1).expect("output directory");
    std::fs::create_dir_all(&dir)?;
    for (w, h) in [(360, 56), (480, 100)] {
        for style in 0..helix::STYLE_NAMES.len() {
            for sample in 0..2 {
                let mut surface = ImageSurface::create(Format::ARgb32, w, h)?;
                let start = std::time::Instant::now();
                {
                    let cr = Context::new(&surface)?;
                    cr.set_source_rgb(0.0, 0.0, 0.0);
                    cr.paint()?;
                    helix::draw_style(
                        &cr,
                        w as f64,
                        h as f64,
                        style,
                        helix::Frame {
                            time: 2.0 + sample as f64,
                            phase: 0.7 + sample as f64 * 0.8,
                            energy: 0.65,
                            compact: 0.4,
                        },
                    );
                }
                surface.flush();
                let stride = surface.stride() as usize;
                let data = surface.data()?;
                let mut rgb = Vec::with_capacity((w * h * 3) as usize);
                let mut bright = 0;
                for y in 0..h as usize {
                    for x in 0..w as usize {
                        let idx = y * stride + x * 4;
                        let pixel = u32::from_ne_bytes(data[idx..idx + 4].try_into()?);
                        let (r, g, b) = ((pixel >> 16) as u8, (pixel >> 8) as u8, pixel as u8);
                        if r.max(g).max(b) > 30 {
                            bright += 1;
                        }
                        rgb.extend_from_slice(&[r, g, b]);
                    }
                }
                assert!(bright > 100, "blank render {}", helix::STYLE_NAMES[style]);
                let path = format!("{dir}/{}-{w}-{sample}.ppm", helix::STYLE_NAMES[style]);
                let mut file = std::fs::File::create(path)?;
                write!(file, "P6\n{w} {h}\n255\n")?;
                file.write_all(&rgb)?;
                println!(
                    "{} {w}x{h} frame {sample}: {bright} visible pixels, {:?}",
                    helix::STYLE_NAMES[style],
                    start.elapsed()
                );
            }
        }
    }
    Ok(())
}
