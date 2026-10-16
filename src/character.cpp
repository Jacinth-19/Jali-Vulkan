#include "jali/character.hpp"
#define TINYGLTF_IMPLEMENTATION
#define TINYGLTF_NO_STB_IMAGE
#define TINYGLTF_NO_STB_IMAGE_WRITE
#include <tiny_gltf.h>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <functional>
#include <numeric>
#include <stdexcept>
namespace jali {
namespace {
void ensure(bool ok,const char* message) { if(!ok) throw std::invalid_argument(message); }
struct Reader {
    const tinygltf::Model& m;
    std::vector<double> read(int id, int type, std::size_t expected=0) {
        ensure(id>=0 && std::size_t(id)<m.accessors.size(),"missing/invalid accessor");
        const auto& a=m.accessors[id];
        ensure(!a.sparse.isSparse && a.type==type && a.count<=100000 && (!expected || a.count==expected),"unsupported accessor shape/count/sparsity");
        ensure(a.bufferView>=0 && std::size_t(a.bufferView)<m.bufferViews.size(),"invalid buffer view");
        const auto& view=m.bufferViews[a.bufferView];
        ensure(view.buffer>=0 && std::size_t(view.buffer)<m.buffers.size(),"invalid buffer");
        const auto& bytes=m.buffers[view.buffer].data;
        const auto components=tinygltf::GetNumComponentsInType(type);
        const auto component_size=tinygltf::GetComponentSizeInBytes(a.componentType);
        ensure(components>0 && component_size>0,"invalid component type");
        ensure(a.componentType==TINYGLTF_COMPONENT_TYPE_FLOAT || a.componentType==TINYGLTF_COMPONENT_TYPE_UNSIGNED_SHORT ||
               a.componentType==TINYGLTF_COMPONENT_TYPE_UNSIGNED_BYTE || a.componentType==TINYGLTF_COMPONENT_TYPE_UNSIGNED_INT,"unsupported component type");
        const auto element=std::size_t(components*component_size);
        const auto stride=view.byteStride ? view.byteStride : element;
        ensure(stride>=element && view.byteOffset<=bytes.size() && view.byteLength<=bytes.size()-view.byteOffset,"invalid accessor byte bounds");
        ensure(a.byteOffset<=view.byteLength && (!a.count || ((a.count-1)<= (view.byteLength-a.byteOffset)/stride &&
               (a.count-1)*stride+element<=view.byteLength-a.byteOffset)),"truncated accessor");
        std::vector<double> out(a.count*components);
        for(std::size_t i=0;i<a.count;++i) for(int j=0;j<components;++j) {
            const auto* p=bytes.data()+view.byteOffset+a.byteOffset+i*stride+j*component_size;
            double value=0;
            if(a.componentType==TINYGLTF_COMPONENT_TYPE_FLOAT) { float f;std::memcpy(&f,p,4);value=f; }
            else { std::uint32_t n=0; for(int b=0;b<component_size;++b) n|=std::uint32_t(p[b])<<(b*8); value=n;
                if(a.normalized) value/=a.componentType==TINYGLTF_COMPONENT_TYPE_UNSIGNED_BYTE ? 255.0 : a.componentType==TINYGLTF_COMPONENT_TYPE_UNSIGNED_SHORT ? 65535.0 : 4294967295.0; }
            ensure(std::isfinite(value),"nonfinite asset data");out[i*components+j]=value;
        }
        return out;
    }
};
Mat4 node_matrix(const tinygltf::Node& node) {
    auto out=identity_matrix();
    if(!node.matrix.empty()) {
        ensure(node.matrix.size()==16,"invalid node matrix");
        for(int i=0;i<16;++i) { ensure(std::isfinite(node.matrix[i]) && std::abs(node.matrix[i])<100,"invalid matrix");out[i]=float(node.matrix[i]); }
        return out;
    }
    if(!node.scale.empty()) { ensure(node.scale.size()==3,"invalid scale"); for(auto s:node.scale) ensure(std::abs(s-1)<1e-6,"this renderer requires unit-scale joints"); }
    if(!node.rotation.empty()) {
        ensure(node.rotation.size()==4,"invalid rotation");
        double x=node.rotation[0],y=node.rotation[1],z=node.rotation[2],w=node.rotation[3];
        ensure(std::abs(x*x+y*y+z*z+w*w-1)<1e-4,"nonunit quaternion");
        out={float(1-2*y*y-2*z*z),float(2*x*y+2*z*w),float(2*x*z-2*y*w),0,
             float(2*x*y-2*z*w),float(1-2*x*x-2*z*z),float(2*y*z+2*x*w),0,
             float(2*x*z+2*y*w),float(2*y*z-2*x*w),float(1-2*x*x-2*y*y),0,0,0,0,1};
    }
    if(!node.translation.empty()) { ensure(node.translation.size()==3,"invalid translation");for(int i=0;i<3;++i) {ensure(std::isfinite(node.translation[i]) && std::abs(node.translation[i])<100,"invalid translation");out[12+i]=float(node.translation[i]);} }
    return out;
}
}
Mat4 identity_matrix() { return {1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1}; }
Mat4 multiply(const Mat4& a,const Mat4& b) {
    Mat4 c{};for(int col=0;col<4;++col) for(int row=0;row<4;++row) for(int k=0;k<4;++k) c[col*4+row]+=a[k*4+row]*b[col*4+k];return c;
}
Character load_character_glb(const std::filesystem::path& path) {
    std::ifstream file(path,std::ios::binary|std::ios::ate);
    ensure(bool(file),"cannot open GLB");const auto size=file.tellg();ensure(size>=20 && size<=16*1024*1024,"GLB must be 20 bytes to 16 MiB");
    std::vector<unsigned char> bytes(static_cast<std::size_t>(size));file.seekg(0);file.read(reinterpret_cast<char*>(bytes.data()),size);ensure(bool(file),"truncated GLB file");
    tinygltf::TinyGLTF loader;
    tinygltf::FsCallbacks fs;
    fs.FileExists=[](const std::string&,void*){return false;};
    fs.ExpandFilePath=[](const std::string& p,void*){return p;};
    fs.ReadWholeFile=[](auto*,auto* error,const auto&,void*){if(error)*error="external files disabled";return false;};
    fs.WriteWholeFile=[](auto*,const auto&,const auto&,void*){return false;};
    fs.GetFileSizeInBytes=[](auto*,auto*,const auto&,void*){return false;};fs.user_data=nullptr;
    ensure(loader.SetFsCallbacks(fs),"cannot disable external asset files");
    tinygltf::Model model;std::string error,warning;
    ensure(loader.LoadBinaryFromMemory(&model,&error,&warning,bytes.data(),static_cast<unsigned>(bytes.size())),"invalid or unsupported GLB");
    ensure(model.extensionsRequired.empty() && model.images.empty() && model.animations.empty() && model.materials.empty(),"extensions, materials/textures, and authored animation tracks are outside this vertex-color facial profile");
    ensure(model.scenes.size()==1 && model.defaultScene==0,"requires one explicitly selected scene");
    ensure(model.meshes.size()==1 && model.skins.size()==1 && model.nodes.size()<=kMaxCharacterNodes,"requires one skinned mesh and <=256 nodes");
    const auto& skin=model.skins[0];ensure(!skin.joints.empty() && skin.joints.size()<=kMaxCharacterJoints,"requires 1-128 joints");
    std::vector<int> parents(model.nodes.size(),-1);
    for(std::size_t i=0;i<model.nodes.size();++i) for(int child:model.nodes[i].children) {
        ensure(child>=0 && std::size_t(child)<parents.size() && parents[child]==-1,"invalid/multiple node parents");parents[child]=int(i);
    }
    // This minimal importer requires all ancestors of joints to be included in skin.joints.
    Character result;Reader reader{model};const auto inverse=reader.read(skin.inverseBindMatrices,TINYGLTF_TYPE_MAT4,skin.joints.size());
    for(std::size_t i=0;i<skin.joints.size();++i) {
        const auto node=skin.joints[i];ensure(node>=0 && std::size_t(node)<model.nodes.size(),"invalid joint node");
        ensure(std::count(skin.joints.begin(),skin.joints.end(),node)==1,"duplicate joint");
        const auto parent=std::find(skin.joints.begin(),skin.joints.end(),parents[node]);
        ensure(parents[node]==-1 || parent!=skin.joints.end(),"joint ancestors must be in the skin");
        CharacterJoint joint; joint.name=model.nodes[node].name;joint.parent=parents[node]==-1 ? -1 : int(parent-skin.joints.begin());joint.local=node_matrix(model.nodes[node]);
        std::copy_n(inverse.begin()+i*16,16,joint.inverse_bind.begin());
        for(const auto& matrix:{joint.local,joint.inverse_bind}) {
            for(float value:matrix)ensure(std::isfinite(value) && std::abs(value)<100,"invalid joint matrix range");
            ensure(std::abs(matrix[3])+std::abs(matrix[7])+std::abs(matrix[11])+std::abs(matrix[15]-1)<1e-4,"nonaffine joint matrix");
            for(int col=0;col<3;++col)for(int other=0;other<3;++other) {
                float dot=0;for(int row=0;row<3;++row)dot+=matrix[col*4+row]*matrix[other*4+row];
                ensure(std::abs(dot-(col==other?1:0))<1e-3,"joint scale/shear is unsupported by the normal transform");
            }
        }
        result.joints.push_back(joint);
        if(joint.name=="Jaw" || joint.name=="jaw") {ensure(result.jaw_joint==-1,"multiple jaw joints");result.jaw_joint=int(i);}
    }
    ensure(result.jaw_joint>=0,"skin must contain a named Jaw joint");
    int mesh_nodes=0;
    for(std::size_t i=0;i<model.nodes.size();++i) if(model.nodes[i].mesh>=0) {
        ensure(model.nodes[i].mesh==0 && model.nodes[i].skin==0 && parents[i]==-1 && node_matrix(model.nodes[i])==identity_matrix(),"mesh node must be identity, root-level, and use skin 0");++mesh_nodes;
    }
    ensure(mesh_nodes==1,"requires one mesh instance");
    for(const auto& node:model.nodes)for(double w:node.weights)ensure(w==0,"nonzero node default morph weights are unsupported");
    const auto& mesh=model.meshes[0];
    ensure(mesh.weights.empty() || mesh.weights.size()==3,"invalid mesh default morph weights");
    for(double w:mesh.weights)ensure(w==0,"nonzero mesh default morph weights are unsupported");
    ensure(mesh.extras.IsObject() && mesh.extras.Has("targetNames"),"missing named facial morph targets");
    const auto& names=mesh.extras.Get("targetNames");ensure(names.IsArray() && names.ArrayLen()==3,"requires jawOpen, mouthRound, mouthClose targets");
    std::array<int,3> mapping{};const std::array<std::string,3> expected{"jawOpen","mouthRound","mouthClose"};
    for(int t=0;t<3;++t) {mapping[t]=-1;for(int n=0;n<3;++n) if(names.Get(n).IsString() && names.Get(n).Get<std::string>()==expected[t]) {ensure(mapping[t]==-1,"duplicate morph name");mapping[t]=n;}ensure(mapping[t]>=0,"missing facial morph name");}
    for(const auto& primitive:mesh.primitives) {
        ensure(primitive.mode==TINYGLTF_MODE_TRIANGLES && primitive.targets.size()==3,"requires triangle primitives and three targets");
        auto attribute=[&](const char* key){auto found=primitive.attributes.find(key);ensure(found!=primitive.attributes.end(),"missing required vertex attribute");return found->second;};
        ensure(!primitive.attributes.count("JOINTS_1") && !primitive.attributes.count("WEIGHTS_1"),"runtime policy supports at most four influences; reduce explicitly offline");
        auto positions=reader.read(attribute("POSITION"),TINYGLTF_TYPE_VEC3);const auto n=positions.size()/3;ensure(n>0 && result.vertices.size()+n<=100000,"mesh vertex limit");
        const auto normals=reader.read(attribute("NORMAL"),TINYGLTF_TYPE_VEC3,n), colors=reader.read(attribute("COLOR_0"),TINYGLTF_TYPE_VEC3,n);
        const auto joints=reader.read(attribute("JOINTS_0"),TINYGLTF_TYPE_VEC4,n), weights=reader.read(attribute("WEIGHTS_0"),TINYGLTF_TYPE_VEC4,n);
        std::array<std::vector<double>,3> deltas;
        for(int t=0;t<3;++t) {auto it=primitive.targets[mapping[t]].find("POSITION");ensure(it!=primitive.targets[mapping[t]].end(),"missing position morph delta");deltas[t]=reader.read(it->second,TINYGLTF_TYPE_VEC3,n);}
        const auto base=std::uint32_t(result.vertices.size());
        for(std::size_t i=0;i<n;++i) {
            MeshVertex v;
            for(int k=0;k<3;++k) {v.position[k]=float(positions[i*3+k]);v.normal[k]=float(normals[i*3+k]);v.color[k]=float(colors[i*3+k]);v.jaw_delta[k]=float(deltas[0][i*3+k]);v.round_delta[k]=float(deltas[1][i*3+k]);v.close_delta[k]=float(deltas[2][i*3+k]);ensure(std::abs(v.position[k])<100 && v.color[k]>=0 && v.color[k]<=1,"invalid vertex range");}
            double total=0,normal_length=0;for(float c:v.normal) normal_length+=c*c;ensure(std::abs(normal_length-1)<1e-3,"nonunit normal");
            for(int k=0;k<4;++k) {const auto j=joints[i*4+k],w=weights[i*4+k];ensure(j>=0 && j<result.joints.size() && j==std::floor(j) && w>=0 && w<=1,"invalid skin influence");v.joints[k]=std::uint32_t(j);v.weights[k]=float(w);total+=w;}
            ensure(std::abs(total-1)<1e-4,"unnormalized skin weights");result.vertices.push_back(v);
        }
        auto indices=reader.read(primitive.indices,TINYGLTF_TYPE_SCALAR);ensure(indices.size()%3==0 && result.indices.size()+indices.size()<=600000,"invalid/excessive triangle indices");
        for(auto i:indices) {ensure(i>=0 && i<n && i==std::floor(i),"out-of-range mesh index");result.indices.push_back(base+std::uint32_t(i));}
    }
    ensure(!result.indices.empty(),"empty mesh");character_palette(result,{});return result;
}
JointPalette character_palette(const Character& c,SpeechPose pose) {
    ensure(c.joints.size()<=kMaxCharacterJoints && !c.joints.empty(),"invalid joint count");
    for(auto v:{pose.jaw,pose.round,pose.close}) ensure(std::isfinite(v) && v>=0 && v<=1,"invalid facial pose");
    JointPalette out,global;for(auto& m:out)m=identity_matrix();std::array<int,kMaxCharacterJoints> visit{};
    std::function<void(int)> solve=[&](int i) {ensure(i>=0 && std::size_t(i)<c.joints.size(),"invalid hierarchy link");ensure(visit[i]!=1,"cyclic joint hierarchy");if(visit[i]==2)return;visit[i]=1;
        auto local=c.joints[i].local;if(i==c.jaw_joint) {auto r=identity_matrix();float angle=pose.jaw*(1-pose.close)*0.22f;r[5]=r[10]=std::cos(angle);r[6]=std::sin(angle);r[9]=-r[6];local=multiply(local,r);}
        const auto parent=c.joints[i].parent;if(parent!=-1) {solve(parent);global[i]=multiply(global[parent],local);}else global[i]=local;
        out[i]=multiply(global[i],c.joints[i].inverse_bind);visit[i]=2;};
    for(std::size_t i=0;i<c.joints.size();++i)solve(int(i));return out;
}
std::vector<std::array<float,3>> deform_reference(const Character& c,SpeechPose pose) {
    const auto palette=character_palette(c,pose);std::vector<std::array<float,3>> out;
    for(const auto& v:c.vertices) {std::array<float,3> p{},q{};for(int k=0;k<3;++k)p[k]=v.position[k]+v.jaw_delta[k]*pose.jaw+v.round_delta[k]*pose.round+v.close_delta[k]*pose.close;
        for(int b=0;b<4;++b) for(int k=0;k<3;++k) {const auto& m=palette.at(v.joints[b]);q[k]+=v.weights[b]*(m[k]*p[0]+m[4+k]*p[1]+m[8+k]*p[2]+m[12+k]);}out.push_back(q);}
    return out;
}
} // namespace jali
