#![allow(
    dead_code,
    unsafe_op_in_unsafe_fn,
    unused_variables,
    clippy::too_many_arguments,
    clippy::unnecessary_wraps
)]

use winit::dpi::LogicalSize;
use winit::event::ElementState;
use winit::event::{Event, WindowEvent};
use winit::event_loop::{EventLoop, EventLoopWindowTarget};
use winit::window::WindowBuilder;

use anyhow::Result;
use log::*;

use std::process;

use app::App;
use key::*;

mod app;
mod key;
mod math;
mod model;
mod obj;
mod ppm;
mod vulkan;

// ── Entry Point ───────────────────────────────────────────────────────────────

fn main() -> Result<()> {
    pretty_env_logger::init();

    // Window

    let event_loop = EventLoop::new()?;
    let window = WindowBuilder::new()
        .with_title("Vulkan Tutorial (Rust)")
        .with_inner_size(LogicalSize::new(1024, 768))
        .build(&event_loop)?;

    // App

    let mut app = unsafe { App::create(&window)? };
    let mut minimized = false;
    event_loop.run(move |event, elwt| {
        match event {
            // Request a redraw when all events were processed.
            Event::AboutToWait => window.request_redraw(),
            Event::WindowEvent { event, .. } => match event {
                // Render a frame if our Vulkan app is not being destroyed.
                WindowEvent::RedrawRequested if !elwt.exiting() && !minimized => {
                    if let Err(e) = unsafe { app.render(&window) } {
                        error!("{e:#}");
                        process::exit(1);
                    }
                }
                WindowEvent::Resized(size) => {
                    if size.width == 0 || size.height == 0 {
                        minimized = true;
                    } else {
                        minimized = false;
                        app.resized = true;
                    }
                }
                // Destroy our Vulkan app.
                WindowEvent::CloseRequested => {
                    exit_app(&mut app, elwt);
                }

                WindowEvent::KeyboardInput { event, .. }
                    if event.state == ElementState::Pressed =>
                {
                    match handle_input(event.physical_key, &mut app.data) {
                        Ok(Signal::ReloadModel) => reload_model(&mut app),
                        Ok(Signal::ReloadTexture) => reload_texture(&mut app),
                        Ok(Signal::TextureAxe(axe)) => {
                            app.data.texture_axe = axe;
                            reload_model(&mut app);
                        }
                        Ok(Signal::ToggleMeshView) => app.mesh_view = !app.mesh_view,
                        Ok(Signal::UpdateAngleSpeed(speed)) => {
                            app.ang_vel += speed % 360.0;
                        }
                        Ok(Signal::Exit) => exit_app(&mut app, elwt),

                        Err(e) => {
                            error!("Error has ocurred while operating input {e}");
                        }
                        Ok(Signal::Nothing) => {}
                    };
                }
                _ => {}
            },
            _ => {}
        }
    })?;

    Ok(())
}

fn reload_texture(app: &mut App) {
    if !app.mesh_view {
        app.new_texture = true;
    }
}

fn reload_model(app: &mut App) {
    if !app.mesh_view {
        app.new_model = true;
    }
}

fn exit_app(app: &mut App, elwt: &EventLoopWindowTarget<()>) {
    elwt.exit();
    unsafe {
        app.destroy();
    }
}
