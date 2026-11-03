use anyhow::{Context, Result, anyhow};
use std::path::PathBuf;
use std::fs::read_to_string;
use thiserror::Error;

use crate::math::{Point2, point2};

#[derive(Clone, Debug, Default)]
pub struct ObjModel {
    pub positions: Vec<[f32; 3]>,
    pub tex_coords: Vec<[f32; 2]>,
    pub normals: Vec<[f32; 3]>,
    pub faces: Vec<[FaceVertex; 3]>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct FaceVertex {
    pub position_index: usize,
    pub tex_coord_index: Option<usize>,
    pub normal_index: Option<usize>,
}

#[derive(Clone, Copy, Debug)]
pub struct RawFaceVertex {
    position_index: i32,
    tex_coord_index: Option<i32>,
    normal_index: Option<i32>,
}

// ── Gestion des erreurs ─────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum ObjError {
    #[error("Ligne {line_number} : ligne malformée '{content}'")]
    MalformedLine { line_number: usize, content: String },

    #[error("Ligne {line_number} : indice invalide ou hors-limites")]
    InvalidIndex { line_number: usize },

    #[error("Erreur I/O : {0}")]
    IoError(std::io::Error),
}

pub fn parse_obj(path: &PathBuf) -> Result<ObjModel> {
    let content = read_to_string(path).map_err(ObjError::IoError)?;

    parse_obj_str(&content)
}

fn parse_obj_str(content: &str) -> Result<ObjModel> {
    let mut model = ObjModel::default();

    for (line_number, line) in content.lines().enumerate().map(|(i, l)| (i + 1, l.trim())) {
        let resolve =
            |idx, len| resolve_index(idx, len).map_err(|_| ObjError::InvalidIndex { line_number });

        let ctx = || ObjError::MalformedLine {
            line_number,
            content: (line.to_string()),
        };
        match line.split_whitespace().next() {
            Some("v") => model
                .positions
                .push(parse_vertex_line(line).with_context(ctx)?),
            Some("vt") => model
                .tex_coords
                .push(parse_texcoord_line(line).with_context(ctx)?),
            Some("vn") => model
                .normals
                .push(parse_normal_line(line).with_context(ctx)?),
            Some("f") => {
                let resolved = parse_face_line(line)
                    .with_context(ctx)?
                    .into_iter()
                    .map(|raw| {
                        Ok(FaceVertex {
                            position_index: resolve(raw.position_index, model.positions.len())?,
                            tex_coord_index: raw
                                .tex_coord_index
                                .map(|i| resolve_index(i, model.tex_coords.len()))
                                .transpose()?,
                            normal_index: raw
                                .normal_index
                                .map(|i| resolve_index(i, model.normals.len()))
                                .transpose()?,
                        })
                    })
                    .collect::<Result<Vec<_>>>()
                    .with_context(ctx)?;

                model
                    .faces
                    .extend(triangulate_face(&resolved, &model.positions));
            }
            _ => {}
        }
    }

    Ok(model)
}

// ── Parsing par type de ligne ────────────────────────────────────────────────

fn parse_vertex_line(line: &str) -> Result<[f32; 3]> {
    let mut split = line.split_whitespace();
    split.next();

    let mut coords = [0.0f32; 3];
    for coord in coords.iter_mut() {
        *coord = split
            .next()
            .ok_or_else(|| anyhow!("not a number"))?
            .parse()?;
    }
    split.next(); // w optionnekl
    if split.next().is_some() {
        return Err(anyhow!("invalid vertex line"));
    }
    Ok(coords)
}

fn parse_texcoord_line(line: &str) -> Result<[f32; 2]> {
    let mut split = line.split_whitespace();
    split.next();

    let mut coords = [0.0f32; 2];
    for coord in coords.iter_mut() {
        *coord = split
            .next()
            .ok_or_else(|| anyhow!("not a number"))?
            .parse()?;
    }
    split.next();
    if split.next().is_some() {
        return Err(anyhow!("Texcoord line has too much values"));
    }
    Ok(coords)
}

fn parse_normal_line(line: &str) -> Result<[f32; 3]> {
    let mut split = line.split_whitespace();
    split.next();

    let mut coords = [0.0f32; 3];
    for coord in coords.iter_mut() {
        *coord = split
            .next()
            .ok_or_else(|| anyhow!("not a number"))?
            .parse()?;
    }

    if split.next().is_some() {
        return Err(anyhow!("Normal line has too much values"));
    }
    Ok(coords)
}

fn parse_face_line(line: &str) -> Result<Vec<RawFaceVertex>> {
    let mut result: Vec<RawFaceVertex> = Vec::with_capacity(4);
    let mut split = line.split_whitespace();

    split.next(); // skip 'f'

    let mut count: Option<usize> = None;
    for parts in split {
        let mut sub_parts = parts.split("/");
        let curr_count = parts.chars().filter(|c| *c == '/').count();
        if *count.get_or_insert(curr_count) != curr_count {
            return Err(anyhow!("Malformed line"));
        }
        let pos = sub_parts.next();
        let tex = sub_parts.next();
        let norm = sub_parts.next();
        let (position_index, tex_coord_index, normal_index) = match (pos, tex, norm) {
            (Some(pos), None, None) => (pos.parse::<i32>()?, None, None),
            (Some(pos), Some(tex), None) => (pos.parse::<i32>()?, Some(tex.parse::<i32>()?), None),
            (Some(pos), Some(""), Some(norm)) => {
                (pos.parse::<i32>()?, None, Some(norm.parse::<i32>()?))
            }
            (Some(pos), Some(tex), Some(norm)) => (
                pos.parse::<i32>()?,
                Some(tex.parse::<i32>()?),
                Some(norm.parse::<i32>()?),
            ),
            _ => return Err(anyhow!("Invalid line")),
        };

        let raw_vertex = RawFaceVertex {
            position_index,
            tex_coord_index,
            normal_index,
        };
        result.push(raw_vertex);
    }

    if result.len() < 3 {
        return Err(anyhow!("not enough parameters"));
    }
    Ok(result)
}

// ── Triangulation ────────────────────────────────────────────────────────────

fn triangulate_face(vertices: &[FaceVertex], positions: &[[f32; 3]]) -> Vec<[FaceVertex; 3]> {
    if vertices.len() == 3 {
        return vec![[vertices[0], vertices[1], vertices[2]]];
    }
    if vertices.len() < 3 {
        return Vec::new();
    }
    let mut triangles: Vec<[FaceVertex; 3]> = Vec::with_capacity(vertices.len() - 2);
    let face_points: Vec<[f32; 3]> = vertices
        .iter()
        .map(|x| positions[x.position_index])
        .collect();
    let points_2d = project_face_2d(&face_points);
    let mut remaining: Vec<usize> = (0..vertices.len()).collect();

    while remaining.len() > 3 {
        let m = remaining.len();

        let ear = (0..m).find(|&k| {
            let prev = remaining[(k + m - 1) % m];
            let curr = remaining[k];
            let next = remaining[(k + 1) % m];
            let (a, b, c) = (points_2d[prev], points_2d[curr], points_2d[next]);

            is_convex(a, b, c)
                && remaining.iter().all(|&i| {
                    i == prev || i == curr || i == next || !is_in_triangle(points_2d[i], a, b, c)
                })
        });
        match ear {
            Some(k) => {
                let prev = remaining[(k + m - 1) % m];
                let next = remaining[(k + 1) % m];
                triangles.push([vertices[prev], vertices[remaining[k]], vertices[next]]);
                remaining.remove(k);
            }
            None => {
                for i in 1..m - 1 {
                    triangles.push([
                        vertices[remaining[0]],
                        vertices[remaining[i]],
                        vertices[remaining[i + 1]],
                    ]);
                }
                return triangles;
            }
        }
    }

    triangles.push([
        vertices[remaining[0]],
        vertices[remaining[1]],
        vertices[remaining[2]],
    ]);

    triangles
}

fn project_face_2d(face_points: &[[f32; 3]]) -> Vec<Point2> {
    let mut normal: [f32; 3] = [0.0, 0.0, 0.0];
    let len = face_points.len();
    let mut face_2d: Vec<Point2> = Vec::with_capacity(len);

    for i in 0..len {
        let current = face_points[i];
        let next = face_points[(i + 1) % len];

        normal[0] += (current[1] - next[1]) * (current[2] + next[2]);
        normal[1] += (current[2] - next[2]) * (current[0] + next[0]);
        normal[2] += (current[0] - next[0]) * (current[1] + next[1]);
    }

    let normal_axis = normal
        .iter()
        .enumerate()
        .max_by(|(_, x), (_, y)| x.abs().total_cmp(&y.abs()))
        .map(|(i, &r)| {
            if r >= 0.0 {
                ((i + 1) % 3, (i + 2) % 3)
            } else {
                ((i + 2) % 3, (i + 1) % 3)
            }
        })
        .unwrap_or((1, 2));

    let (x, y) = normal_axis;
    for i in 0..len {
        let current = face_points[i];
        face_2d.push(point2(current[x], current[y]));
    }

    face_2d
}

fn is_in_triangle(p: Point2, a: Point2, b: Point2, c: Point2) -> bool {
    cross_2d(p, b, c) >= 0.0 && cross_2d(a, p, c) >= 0.0 && cross_2d(a, b, p) >= 0.0
}

fn cross_2d(a: Point2, b: Point2, c: Point2) -> f32 {
    (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
}

fn is_convex(a: Point2, b: Point2, c: Point2) -> bool {
    cross_2d(a, b, c) > 0.0
}

// ── Résolution des indices négatifs (relatifs) ──────────────────────────────

fn resolve_index(index: i32, current_count: usize) -> Result<usize> {
    let resolved = if index > 0 {
        (index - 1) as usize
    } else if index < 0 {
        let offset = index.unsigned_abs() as usize;
        current_count
            .checked_sub(offset)
            .ok_or_else(|| anyhow!("relative index out of bounds"))?
    } else {
        return Err(anyhow!("index cannot be 0"));
    };

    if resolved >= current_count {
        return Err(anyhow!("resolved index is out of bound"));
    }
    Ok(resolved)
}

// ── Bounding box / centroid ─────────────────────────────────────────────────

pub fn compute_centroid(positions: &[[f32; 3]]) -> [f32; 3] {
    let (min, max) = compute_bounding_box(positions);

    [
        (max[0] + min[0]) / 2.0,
        (max[1] + min[1]) / 2.0,
        (max[2] + min[2]) / 2.0,
    ]
}

pub fn compute_bounding_box(positions: &[[f32; 3]]) -> ([f32; 3], [f32; 3]) {
    if positions.is_empty() {
        return ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]);
    }
    let mut max: [f32; 3] = positions[0];
    let mut min: [f32; 3] = positions[0];

    for pos in &positions[1..] {
        for (i, &val) in pos.iter().enumerate() {
            max[i] = val.max(max[i]);
            min[i] = val.min(min[i]);
        }
    }

    (min, max)
}
