pub mod audio { pub mod levels; }
pub mod osd { pub mod config; pub mod ipc; pub mod visual; pub mod theme; }
pub mod config {
use std::path::PathBuf;
pub struct Config;
impl Config {
pub fn default_path()->Option<PathBuf>{ std::env::var_os("XDG_CONFIG_HOME").map(PathBuf::from).or_else(||std::env::var_os("HOME").map(|h|PathBuf::from(h).join(".config"))).map(|p|p.join("voxtype/config.toml")) }
pub fn runtime_dir()->PathBuf {std::env::var_os("XDG_RUNTIME_DIR").map(PathBuf::from).unwrap_or_else(||PathBuf::from("/tmp")).join("voxtype")}
}}
