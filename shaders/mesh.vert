#version 450
layout(location=0) in vec3 position;
layout(location=1) in vec3 normal;
layout(location=2) in vec3 color;
layout(location=3) in vec2 uv;
layout(location=4) in vec4 factor;
layout(location=5) in vec4 material;
layout(location=6) in float normal_scale;
layout(set=0,binding=2,std140) uniform Pose { mat4 bones[128]; vec4 morph; vec4 weights[20]; vec4 camera; } pose;
layout(location=0) out vec3 world_normal;
layout(location=1) out vec3 base_color;
layout(location=2) out vec2 texcoord;
layout(location=3) out vec4 color_factor;
layout(location=4) out vec4 parameters;
layout(location=5) out vec3 world_position;
layout(location=6) out float normal_strength;
void main(){
    if(pose.camera.w>0){vec3 p=position-pose.camera.xyz;gl_Position=vec4(p.x*pose.camera.w,-p.y*pose.camera.w,(2.5-p.z)/5.,1);}
    else gl_Position=vec4(position.x*.78,-(position.y+.2)*.78,(2.5-position.z)/5.,1);
    world_normal=normal;base_color=color;texcoord=uv;color_factor=factor;parameters=material;world_position=position;normal_strength=normal_scale;
}
