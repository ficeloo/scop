#version 450

layout(binding = 1) uniform sampler2D texSampler;

layout(push_constant) uniform PushConstants {
	layout(offset = 64) float opacity;
	layout(offset = 68) float mesh_view;
} pcs;

layout(location = 0) in vec3 fragColor;
layout(location = 1) in vec2 fragTexCoord;

layout(location = 0) out vec4 outColor;

void main() {
	if (pcs.mesh_view == 1.0) {
		float id = float(gl_PrimitiveID);
		float shade = clamp((mod(id, 8.0) / 7.0), 0.1, 0.95);

		outColor = vec4(vec3(shade), pcs.opacity);
	} else {
		outColor = vec4(texture(texSampler, fragTexCoord).rgb, pcs.opacity);
	}
}
