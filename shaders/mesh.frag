#version 450
layout(location=0) in vec3 world_normal;
layout(location=1) in vec3 base_color;
layout(location=0) out vec4 out_color;
void main(){
    vec3 n=normalize(world_normal),light=normalize(vec3(-0.65,0.9,1.6)),view=vec3(0,0,1);
    float diffuse=max(dot(n,light),0),spec=pow(max(dot(reflect(-light,n),view),0),40);
    vec3 c=base_color*(0.19+0.8*diffuse)+spec*0.45;
    c+=pow(1-max(dot(n,view),0),3)*vec3(0.01,0.8,1)*0.2;
    c+=max(dot(n,normalize(vec3(1,-0.1,0.6))),0)*vec3(1,0.08,0.32)*0.06;
    if(base_color.g>0.7 && base_color.r<0.15)c=base_color*0.95;
    out_color=vec4(pow(clamp(c,0,1),vec3(1.0/2.2)),1);
}
