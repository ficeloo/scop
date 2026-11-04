use std::collections::HashMap;
use std::mem::size_of;

use anyhow::Result;
use vulkanalia::prelude::v1_0::*;

use crate::app::AppData;
use crate::math::{Vec2, Vec3, get_normal_axis_max, vec2, vec3};
use crate::obj::{self, FaceVertex, ObjModel};

// ── Constants ─────────────────────────────────────────────────────────────────

const TARGET_SIZE: f32 = 1.50;
const TEXTURE_ZOOM: f32 = 1.0;

// ── Vertex Data ─────────────────────────────────────────────────────────────────

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct Vertex {
    pos: Vec3,
    color: Vec3,
    tex_coord: Vec2,
}

impl Vertex {
    const fn new(pos: Vec3, color: Vec3, tex_coord: Vec2) -> Self {
        Self {
            pos,
            color,
            tex_coord,
        }
    }

    pub fn binding_description() -> vk::VertexInputBindingDescription {
        vk::VertexInputBindingDescription::builder()
            .binding(0)
            .stride(size_of::<Vertex>() as u32)
            .input_rate(vk::VertexInputRate::VERTEX)
            .build()
    }

    pub fn attribute_descriptions() -> [vk::VertexInputAttributeDescription; 3] {
        let pos = vk::VertexInputAttributeDescription::builder()
            .binding(0)
            .location(0)
            .format(vk::Format::R32G32B32_SFLOAT)
            .offset(0)
            .build();

        let color = vk::VertexInputAttributeDescription::builder()
            .binding(0)
            .location(1)
            .format(vk::Format::R32G32B32_SFLOAT)
            .offset(size_of::<Vec3>() as u32)
            .build();

        let tex_coord = vk::VertexInputAttributeDescription::builder()
            .binding(0)
            .location(2)
            .format(vk::Format::R32G32_SFLOAT)
            .offset((size_of::<Vec3>() + size_of::<Vec3>()) as u32)
            .build();
        [pos, color, tex_coord]
    }
}

// ── Model Loading ─────────────────────────────────────────────────────────────────

fn build_vertex(
    models: &ObjModel,
    fv: &FaceVertex,
    center: [f32; 3],
    facteur: f32,
    min: [f32; 3],
    inv_etendu: [f32; 3],
    tex_axe: (usize, usize),
) -> Vertex {
    let model_pos = models.positions[fv.position_index];
    let tex_coord = match fv.tex_coord_index {
        Some(i) => {
            let model_vert = models.tex_coords[i];
            vec2(model_vert[0], 1.0 - model_vert[1])
        }
        None => {
            let (y, x) = tex_axe;
            vec2(
                (model_pos[x] - min[x]) * inv_etendu[x] * TEXTURE_ZOOM,
                (1.0 - model_pos[y] - min[y]) * inv_etendu[y] * TEXTURE_ZOOM,
            )
        }
    };

    Vertex {
        pos: vec3(
            (model_pos[2] - center[2]) * facteur,
            (model_pos[0] - center[0]) * facteur,
            (model_pos[1] - center[1]) * facteur,
        ),
        color: vec3(0.0, 0.0, 0.0),
        tex_coord,
    }
}

fn toggling_box_mapping(model: &ObjModel, face: &[FaceVertex; 3]) -> (usize, usize) {
    let pos_a = model.positions[face[0].position_index];
    let pos_b = model.positions[face[1].position_index];
    let pos_c = model.positions[face[2].position_index];

    let a = vec3(pos_a[0], pos_a[1], pos_a[2]);
    let b = vec3(pos_b[0], pos_b[1], pos_b[2]);
    let c = vec3(pos_c[0], pos_c[1], pos_c[2]);

    let normal = (b - a).cross(c - a);

    get_normal_axis_max([normal.x, normal.y, normal.z])
}

pub fn load_model(data: &mut AppData) -> Result<()> {
    let model = obj::parse_obj(&data.image_path)?;

    let (min, max) = obj::compute_bounding_box(&model.positions);
    let center = obj::compute_centroid(&model.positions);
    let etendu: [f32; 3] = [max[0] - min[0], max[1] - min[1], max[2] - min[2]];
    let inv_etendu: [f32; 3] =
        etendu.map(|ampl| if ampl > f32::EPSILON { 1.0 / ampl } else { 0.0 });
    let etendu_max = etendu[0].max(etendu[1]).max(etendu[2]);
    let tex_axe = etendu
        .iter()
        .enumerate()
        .min_by(|(_, x), (_, y)| x.total_cmp(y))
        .map(|(i, _)| ((i + data.texture_axe) % 3, (i + 1 + data.texture_axe) % 3))
        .unwrap_or((1, 2));
    let facteur: f32 = if etendu_max > f32::EPSILON {
        TARGET_SIZE / etendu_max
    } else {
        1.0
    };

    let mut unique_vertices = HashMap::new();

    for face in &model.faces {
        let normal_axis = if data.toggle_box_mapping {
            toggling_box_mapping(&model, face)
        } else {
            tex_axe
        };

        for fv in face {
            let key_axis = if fv.tex_coord_index.is_some() {
                (0, 0)
            } else {
                normal_axis
            };
            let key = (fv, key_axis);

            if let Some(i) = unique_vertices.get(&key) {
                data.indices.push(*i as u32);
            } else {
                let vertex =
                    build_vertex(&model, fv, center, facteur, min, inv_etendu, normal_axis);
                let index = data.vertices.len();
                unique_vertices.insert(key, index);
                data.vertices.push(vertex);
                data.indices.push(index as u32);
            }
        }
    }
    Ok(())
}
