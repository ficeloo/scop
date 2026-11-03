use anyhow::Result;
use winit::keyboard::KeyCode;

use crate::app::AppData;
use crate::math::{Vector3, vec3};

const SPEED: f32 = 15.0;

pub enum Signal {
    Nothing,
    Exit,
    ReloadModel,
    ReloadTexture,
    TextureAxe(usize),
    ToggleMeshView,
    UpdateAngleSpeed(f32),
    StopRotation,
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

pub fn handle_input(input: KeyCode, data: &mut AppData) -> Result<Signal> {
    match input {
        KeyCode::Enter => file_manager(data),
        KeyCode::ArrowLeft => change_texture_index(data, false),
        KeyCode::ArrowRight => change_texture_index(data, true),
        KeyCode::KeyM => Ok(Signal::ToggleMeshView),
        KeyCode::KeyJ => Ok(Signal::TextureAxe(0)),
        KeyCode::KeyK => Ok(Signal::TextureAxe(1)),
        KeyCode::KeyL => Ok(Signal::TextureAxe(2)),
        KeyCode::KeyO => Ok(Signal::UpdateAngleSpeed(SPEED)),
        KeyCode::KeyI => Ok(Signal::UpdateAngleSpeed(-SPEED)),
        KeyCode::KeyP => Ok(Signal::StopRotation),
        KeyCode::Escape => Ok(Signal::Exit),
        _ => Ok(Signal::Nothing),
    }
}

pub fn move_model(input: KeyCode) -> Option<Vector3> {
    match input {
        KeyCode::KeyW => Some(vec3(-1.0, 0.0, 0.0)),
        KeyCode::KeyS => Some(vec3(1.0, 0.0, 0.0)),
        KeyCode::KeyD => Some(vec3(0.0, -1.0, 0.0)),
        KeyCode::KeyA => Some(vec3(0.0, 1.0, 0.0)),
        KeyCode::KeyQ => Some(vec3(0.0, 0.0, -1.0)),
        KeyCode::KeyE => Some(vec3(0.0, 0.0, 1.0)),
        _ => None,
    }
}
