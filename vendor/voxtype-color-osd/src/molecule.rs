//! Measured 1BNA heavy-atom coordinates. Only rigid alignment is applied.
use std::sync::OnceLock;

#[derive(Clone, Copy, Debug)]
pub struct Vec3(pub f64, pub f64, pub f64);
impl Vec3 {
    pub fn dot(self, b: Self) -> f64 {
        self.0 * b.0 + self.1 * b.1 + self.2 * b.2
    }
    fn sub(self, b: Self) -> Self {
        Self(self.0 - b.0, self.1 - b.1, self.2 - b.2)
    }
    fn unit(self) -> Self {
        let l = self.dot(self).sqrt();
        Self(self.0 / l, self.1 / l, self.2 / l)
    }
    fn cross(self, b: Self) -> Self {
        Self(
            self.1 * b.2 - self.2 * b.1,
            self.2 * b.0 - self.0 * b.2,
            self.0 * b.1 - self.1 * b.0,
        )
    }
}

pub struct Atom {
    pub point: Vec3,
    pub element: char,
    chain: char,
    residue: i32,
    name: String,
}

pub struct Molecule {
    pub atoms: Vec<Atom>,
    pub bonds: Vec<(usize, usize)>,
    pub half_length: f64,
    pub radius: f64,
}

fn atoms(source: &str) -> Vec<Atom> {
    source
        .lines()
        .filter(|line| line.starts_with("ATOM  "))
        .map(|line| Atom {
            point: Vec3(
                line[30..38].trim().parse().expect("PDB x"),
                line[38..46].trim().parse().expect("PDB y"),
                line[46..54].trim().parse().expect("PDB z"),
            ),
            element: line[76..78].trim().chars().next().expect("PDB element"),
            chain: line.as_bytes()[21] as char,
            residue: line[22..26].trim().parse().expect("PDB residue"),
            name: line[12..16].trim().to_owned(),
        })
        .collect()
}

impl Molecule {
    fn load() -> Self {
        let mut atoms = atoms(include_str!("dna_1bna.pdb"));
        let n = atoms.len() as f64;
        let centroid = Vec3(
            atoms.iter().map(|a| a.point.0).sum::<f64>() / n,
            atoms.iter().map(|a| a.point.1).sum::<f64>() / n,
            atoms.iter().map(|a| a.point.2).sum::<f64>() / n,
        );
        let mut cov = [[0.0; 3]; 3];
        for atom in &atoms {
            let p = atom.point.sub(centroid);
            let v = [p.0, p.1, p.2];
            for i in 0..3 {
                for j in 0..3 {
                    cov[i][j] += v[i] * v[j];
                }
            }
        }
        let mut x = Vec3(1.0, 2.0, 3.0).unit();
        for _ in 0..80 {
            x = Vec3(
                Vec3(cov[0][0], cov[0][1], cov[0][2]).dot(x),
                Vec3(cov[1][0], cov[1][1], cov[1][2]).dot(x),
                Vec3(cov[2][0], cov[2][1], cov[2][2]).dot(x),
            )
            .unit();
        }
        let reference = if x.2.abs() < 0.9 {
            Vec3(0.0, 0.0, 1.0)
        } else {
            Vec3(0.0, 1.0, 0.0)
        };
        let y = x.cross(reference).unit();
        let z = x.cross(y).unit();
        for atom in &mut atoms {
            let p = atom.point.sub(centroid);
            atom.point = Vec3(p.dot(x), p.dot(y), p.dot(z));
        }
        // Infer covalent display sticks by distance, within residues or the O3'-P link.
        let covalent = |element| match element {
            'C' => 0.76,
            'N' => 0.71,
            'O' => 0.66,
            'P' => 1.07,
            _ => 0.31,
        };
        let mut bonds = Vec::new();
        for i in 0..atoms.len() {
            for j in i + 1..atoms.len() {
                let (a, b) = (&atoms[i], &atoms[j]);
                if a.chain != b.chain {
                    continue;
                }
                if a.residue != b.residue
                    && !((a.residue - b.residue).abs() == 1
                        && ((a.name == "O3'" && b.name == "P")
                            || (b.name == "O3'" && a.name == "P")))
                {
                    continue;
                }
                let d = a.point.sub(b.point);
                let distance = d.dot(d).sqrt();
                if distance > 0.5 && distance < covalent(a.element) + covalent(b.element) + 0.38 {
                    bonds.push((i, j));
                }
            }
        }
        let half_length = atoms.iter().map(|a| a.point.0.abs()).fold(0.0, f64::max);
        let radius = atoms
            .iter()
            .map(|a| (a.point.1 * a.point.1 + a.point.2 * a.point.2).sqrt())
            .fold(0.0, f64::max);
        Self {
            atoms,
            bonds,
            half_length,
            radius,
        }
    }
}

pub fn model() -> &'static Molecule {
    static MODEL: OnceLock<Molecule> = OnceLock::new();
    MODEL.get_or_init(Molecule::load)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn measured_coordinates_keep_all_distances_after_alignment() {
        let original = atoms(include_str!("dna_1bna.pdb"));
        let m = model();
        assert_eq!(m.atoms.len(), 486);
        assert!(m.bonds.len() > 450 && m.bonds.len() < 600);
        for i in 0..original.len() {
            for j in (i + 1..original.len()).step_by(29) {
                let a = original[i].point.sub(original[j].point);
                let b = m.atoms[i].point.sub(m.atoms[j].point);
                assert!((a.dot(a) - b.dot(b)).abs() < 1e-8);
            }
        }
        assert!(m.half_length > m.radius);
    }
}
