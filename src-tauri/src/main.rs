// Do not open an additional console window in production on Windows.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    substrakt_lib::run()
}
