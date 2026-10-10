#[derive(Default)]
pub struct VoiceMotion {
    pub phase: f64,
    pub energy: f64,
    pub compact: f64,
    pub angular_speed: f64,
    time: f64,
    fast_envelope: f64,
    slow_envelope: f64,
    last_onset: Option<f64>,
    cadence: f64,
    armed: bool,
}

pub fn voice_level(peak: f64) -> f64 {
    if peak.is_finite() && peak > 0.0 {
        ((20.0 * peak.log10() + 50.0) / 38.0).clamp(0.0, 1.0)
    } else {
        0.0
    }
}

impl VoiceMotion {
    pub fn advance(&mut self, peak: f64, dt: f64) {
        if !dt.is_finite() || dt <= 0.0 {
            return;
        }
        let target = voice_level(peak);
        let dt = dt.clamp(0.0, 0.05);
        self.time += dt;
        let response = if target > self.energy { 0.045 } else { 0.20 };
        self.energy += (target - self.energy) * (1.0 - (-dt / response).exp());

        let amplitude = if peak.is_finite() {
            peak.clamp(0.0, 1.0)
        } else {
            0.0
        };
        self.fast_envelope += (amplitude - self.fast_envelope) * (1.0 - (-dt / 0.018).exp());
        self.slow_envelope += (amplitude - self.slow_envelope) * (1.0 - (-dt / 0.25).exp());
        if self.fast_envelope < self.slow_envelope * 0.88 || amplitude < 0.003 {
            self.armed = true;
        }
        // Relative envelope onsets estimate syllabic cadence, not word count or volume.
        let since = self
            .last_onset
            .map(|t| self.time - t)
            .unwrap_or(f64::INFINITY);
        if amplitude > 0.006
            && self.fast_envelope > self.slow_envelope * 1.20
            && since > 0.12
            && (self.armed || self.last_onset.is_none())
        {
            if (0.12..1.5).contains(&since) {
                let rate = (1.0 / since).clamp(0.0, 7.0);
                self.cadence += (rate - self.cadence) * 0.55;
            }
            self.last_onset = Some(self.time);
            self.armed = false;
        }
        if since > 0.65 || amplitude < 0.003 {
            self.cadence *= (-dt / 0.9).exp();
        }
        let compact_target = (self.cadence / 6.0).clamp(0.0, 1.0);
        self.compact += (compact_target - self.compact) * (1.0 - (-dt / 0.3).exp());
        let speed_target = 0.12 + self.energy * 0.45 + self.cadence * 1.35;
        self.angular_speed += (speed_target - self.angular_speed) * (1.0 - (-dt / 0.18).exp());
        self.phase = (self.phase + dt * self.angular_speed).rem_euclid(std::f64::consts::TAU);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cadence_sample(hz: f64, amplitude: f64) -> VoiceMotion {
        let mut motion = VoiceMotion::default();
        for i in 0..1000 {
            let t = i as f64 / 60.0;
            let peak = if (t * hz).fract() < 0.45 {
                amplitude
            } else {
                amplitude * 0.08
            };
            motion.advance(peak, 1.0 / 60.0);
        }
        motion
    }

    #[test]
    fn faster_speech_condenses_and_spins_faster_at_equal_volume() {
        let slow = cadence_sample(2.0, 0.15);
        let fast = cadence_sample(5.0, 0.15);
        assert!(fast.angular_speed > slow.angular_speed * 1.4);
        assert!(fast.compact > slow.compact + 0.15);
    }

    #[test]
    fn loud_slow_speech_is_not_mistaken_for_fast_speech() {
        let loud_slow = cadence_sample(2.0, 0.45);
        let quiet_fast = cadence_sample(5.0, 0.06);
        assert!(quiet_fast.angular_speed > loud_slow.angular_speed);
    }

    #[test]
    fn steady_sound_has_no_sustained_cadence_and_pause_releases_compression() {
        let mut steady = VoiceMotion::default();
        for _ in 0..1000 {
            steady.advance(0.2, 0.01);
        }
        assert!(steady.compact < 0.05);
        let mut fast = cadence_sample(5.0, 0.15);
        for _ in 0..400 {
            fast.advance(0.0, 0.01);
        }
        assert!(fast.compact < 0.05);
        assert!(fast.angular_speed < 0.5);
    }

    #[test]
    fn grain_profile_is_thin_for_silence_and_expands_with_speech() {
        assert_eq!(voice_level(0.001), 0.0);
        assert!(voice_level(0.02) > voice_level(0.005));
        assert!(voice_level(0.2) > voice_level(0.02));
        assert_eq!(voice_level(1.0), 1.0);
    }

    #[test]
    fn speech_rotates_faster_than_silence_without_volume_dominating() {
        let mut silent = VoiceMotion::default();
        let mut quiet = VoiceMotion::default();
        let mut loud = VoiceMotion::default();
        for _ in 0..20 {
            silent.advance(0.001, 0.02);
            quiet.advance(0.01, 0.02);
            loud.advance(0.20, 0.02);
        }
        assert!(loud.phase > quiet.phase);
        assert!(loud.angular_speed < 0.7);
        assert!(quiet.phase > silent.phase * 1.5);
        assert_eq!(silent.energy, 0.0);
    }

    #[test]
    fn attack_is_fast_and_pause_decays_smoothly() {
        let mut motion = VoiceMotion::default();
        for _ in 0..5 {
            motion.advance(0.3, 0.02);
        }
        assert!(motion.energy > 0.85);
        let before = motion.energy;
        motion.advance(0.0, 0.02);
        assert!(motion.energy < before && motion.energy > before * 0.8);
        for _ in 0..50 {
            motion.advance(0.0, 0.02);
        }
        assert!(motion.energy < 0.01);
    }

    #[test]
    fn invalid_input_and_long_idle_do_not_jump() {
        let mut motion = VoiceMotion::default();
        motion.advance(f64::NAN, 100.0);
        assert!(motion.phase.is_finite() && motion.phase < 0.01);
    }
}
