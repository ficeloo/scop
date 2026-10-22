use anyhow::Result;
use winit::keyboard::KeyCode;
use winit::keyboard::PhysicalKey;

use crate::app::AppData;

pub enum Signal {
    Nothing,
    ReloadModel,
    ReloadTexture,
}

fn change_texture_index(data: &mut AppData, direction: bool) -> Result<Signal> {
    let len = data.texture_path_vec.len();
    let i = data.texture_path_index;

    if len == 0 {
        return Ok(Signal::Nothing);
    }

    data.texture_path_index = if direction {
        (i + 1) % len
    } else {
        (i + len - 1) % len
    };

    Ok(Signal::ReloadTexture)
}

fn file_manager(data: &mut AppData) -> Result<Signal> {
    let path = std::env::current_dir()?.join("resources/model");

    let file = rfd::FileDialog::new()
        .add_filter("model", &["obj"])
        .set_directory(&path)
        .pick_file();

    match file {
        Some(path) => {
            data.image_path = path;
            Ok(Signal::ReloadModel)
        }
        None => Ok(Signal::Nothing),
    }
}

pub fn handle_input(input: PhysicalKey, data: &mut AppData) -> Result<Signal> {
    match input {
        PhysicalKey::Code(KeyCode::Enter) => file_manager(data),
        PhysicalKey::Code(KeyCode::ArrowLeft) => change_texture_index(data, false),
        PhysicalKey::Code(KeyCode::ArrowRight) => change_texture_index(data, true),
        _ => Ok(Signal::Nothing),
    }
}
