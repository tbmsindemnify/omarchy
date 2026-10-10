#[path = "../src/molecule.rs"]
mod molecule;
fn main() {
    let m = molecule::model();
    let data = serde_json::json!({"atoms":m.atoms.iter().map(|a|
        serde_json::json!([a.point.0,a.point.1,a.point.2,a.element.to_string()])).collect::<Vec<_>>(),
        "bonds":m.bonds,"halfLength":m.half_length,"radius":m.radius});
    let output = std::env::args().nth(1).expect("output JSON path");
    std::fs::write(output, serde_json::to_vec(&data).unwrap()).unwrap();
}
