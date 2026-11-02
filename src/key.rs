use anyhow::Result;
use winit::keyboard::KeyCode;
use winit::keyboard::PhysicalKey;

use crate::app::AppData;

pub enum Signal {
    Nothing,
    Exit,
    ReloadModel,
    ReloadTexture,
    TextureAxe(usize),
    ToggleMeshView,
    UpdateAngleSpeed,
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

fn toggle_mesh_view() -> Result<Signal> {
    Ok(Signal::ToggleMeshView)
}

pub fn handle_input(input: PhysicalKey, data: &mut AppData) -> Result<Signal> {
    match input {
        PhysicalKey::Code(KeyCode::Enter) => file_manager(data),
        PhysicalKey::Code(KeyCode::ArrowLeft) => change_texture_index(data, false),
        PhysicalKey::Code(KeyCode::ArrowRight) => change_texture_index(data, true),
        PhysicalKey::Code(KeyCode::KeyM) => toggle_mesh_view(),
        PhysicalKey::Code(KeyCode::KeyJ) => Ok(Signal::TextureAxe(0)),
        PhysicalKey::Code(KeyCode::KeyK) => Ok(Signal::TextureAxe(1)),
        PhysicalKey::Code(KeyCode::KeyL) => Ok(Signal::TextureAxe(2)),
        PhysicalKey::Code(KeyCode::KeyO) => Ok(Signal::UpdateAngleSpeed)
        PhysicalKey::Code(KeyCode::Escape) => Ok(Signal::Exit),
        _ => Ok(Signal::Nothing),
    }
}
