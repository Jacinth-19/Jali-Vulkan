#version 450
layout(location=0) in vec3 world_normal;
layout(location=1) in vec3 base_color;
layout(location=2) in vec2 texcoord;
layout(location=3) in vec4 color_factor;
layout(location=4) in vec4 parameters;
layout(location=5) in vec3 world_position;
layout(location=6) in float normal_strength;
layout(set=0,binding=5) uniform sampler2D atlas;
layout(set=0,binding=6) uniform sampler2D normal_atlas;
layout(location=0) out vec4 out_color;
const float PI=3.14159265;
vec3 lightPBR(vec3 n,vec3 v,vec3 l,vec3 base,float metal,float rough){
    vec3 h=normalize(v+l);float nv=max(dot(n,v),.001),nl=max(dot(n,l),0),nh=max(dot(n,h),0),vh=max(dot(v,h),0);
    float a=max(.045,rough*rough),a2=a*a,d=a2/(PI*pow(nh*nh*(a2-1)+1,2));
    float k=pow(rough+1,2)/8,g=(nv/(nv*(1-k)+k))*(nl/(nl*(1-k)+k));
    vec3 f0=mix(vec3(.04),base,metal),f=f0+(1-f0)*pow(1-vh,5);
    return ((1-f)*(1-metal)*base/PI+d*g*f/max(4*nv*nl,.001))*nl;
}
void main(){
    vec3 n=normalize(world_normal),light=normalize(vec3(-.65,.9,1.6)),view=vec3(0,0,1);
    if(parameters.w<0){
        float diffuse=max(dot(n,light),0),spec=pow(max(dot(reflect(-light,n),view),0),40);
        vec3 c=base_color*(.19+.8*diffuse)+spec*.45;
        c+=pow(1-max(dot(n,view),0),3)*vec3(.01,.8,1)*.2;
        c+=max(dot(n,normalize(vec3(1,-.1,.6))),0)*vec3(1,.08,.32)*.06;
        if(base_color.g>.7&&base_color.r<.15)c=base_color*.95;
        out_color=vec4(pow(clamp(c,0,1),vec3(1./2.2)),1);return;
    }
    if(parameters.w>=4&&!gl_FrontFacing)discard;
    float alpha_mode=mod(parameters.w,4);
    vec4 tex=texture(atlas,texcoord)*color_factor;
    if(alpha_mode==1&&tex.a<parameters.z)discard;
    if(!gl_FrontFacing)n=-n;
    if(normal_strength>0){
        vec3 dp1=dFdx(world_position),dp2=dFdy(world_position);vec2 d1=dFdx(texcoord),d2=dFdy(texcoord);
        vec3 p2=cross(dp2,n),p1=cross(n,dp1),t=p2*d1.x+p1*d2.x,b=p2*d1.y+p1*d2.y;
        float scale=inversesqrt(max(max(dot(t,t),dot(b,b)),1e-20));
        vec3 local=texture(normal_atlas,texcoord).xyz*2-1;
        n=normalize(t*scale*local.x*normal_strength+b*scale*local.y*normal_strength+n*local.z);
    }
    vec3 c=tex.rgb*.42+lightPBR(n,view,light,tex.rgb,parameters.x,parameters.y)*2.2;
    c+=lightPBR(n,view,normalize(vec3(.9,.1,.7)),tex.rgb,parameters.x,parameters.y)*.65;
    c=c/(c+vec3(1));out_color=vec4(pow(max(c,vec3(0)),vec3(1./2.2)),alpha_mode==2?tex.a:1);
}
