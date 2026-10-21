use winit::event::DeviceEvent::Key;
use winit::keyboard::KeyCode;
use winit::keyboard::PhysicalKey;

use crate::App;

fn file_manager(image_path: String) {
    todo!()
}

pub fn handle_input(input: PhysicalKey, app: &App) {
    match input {
        PhysicalKey::Code(KeyCode::Enter) => file_manager(app.data.image_path),
        _ => {}
    }
    todo!()
}
