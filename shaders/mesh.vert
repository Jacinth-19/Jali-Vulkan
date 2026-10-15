#version 450
layout(location=0) in vec3 position;
layout(location=1) in vec3 normal;
layout(location=2) in vec3 color;
layout(location=0) out vec3 world_normal;
layout(location=1) out vec3 base_color;
void main(){
    gl_Position=vec4(position.x*0.78,-(position.y+0.2)*0.78,(2.5-position.z)/5.0,1);
    world_normal=normal;base_color=color;
}
