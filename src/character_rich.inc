// Canonical decoded GLB profile. No runtime codecs, remote resources or implicit
// attribute/morph reduction. Invoked only by an explicit rich-v1 marker.
Character load_rich_character(const tinygltf::Model& model) {
    const auto& extra=model.extras;
    ensure(extra.Get("jaliNativeProfile").IsString() && extra.Get("jaliNativeProfile").Get<std::string>()=="rich-v1","unknown native profile");
    ensure(model.extensionsRequired.empty() && model.animations.empty() && model.meshes.size()==1 && model.skins.size()==1 && model.nodes.size()<=kMaxCharacterNodes,"unsupported canonical structure");
    ensure(model.materials.size()>0&&model.materials.size()<=64&&model.images.size()==2&&model.textures.size()==2&&model.textures[0].source==0&&model.textures[1].source==1,"canonical image/material structure");
    for(const auto& b:model.buffers)ensure(b.uri.empty(),"canonical external buffers disabled");
    for(const auto& image:model.images)ensure(image.uri.empty()&&image.bufferView>=0&&image.mimeType=="image/png","canonical images must be embedded PNGs");
    Character c;Reader r{model};const auto& skin=model.skins[0];
    ensure(!skin.joints.empty() && skin.joints.size()<=kMaxCharacterJoints,"canonical palette limit");
    std::vector<int> parents(model.nodes.size(),-1);
    for(std::size_t n=0;n<model.nodes.size();++n)for(int child:model.nodes[n].children){ensure(child>=0 && std::size_t(child)<parents.size() && parents[child]==-1,"invalid canonical parents");parents[child]=int(n);}
    const auto inverse=r.read(skin.inverseBindMatrices,TINYGLTF_TYPE_MAT4,skin.joints.size());
    for(std::size_t i=0;i<skin.joints.size();++i){
        const auto node=skin.joints[i];ensure(node>=0 && std::size_t(node)<model.nodes.size() && std::count(skin.joints.begin(),skin.joints.end(),node)==1,"invalid canonical joint");
        const auto parent=std::find(skin.joints.begin(),skin.joints.end(),parents[node]);ensure(parents[node]<0 || parent!=skin.joints.end(),"missing canonical ancestor");
        CharacterJoint j;j.name=model.nodes[node].name;j.parent=parents[node]<0?-1:int(parent-skin.joints.begin());j.local=node_matrix(model.nodes[node]);
        std::copy_n(inverse.begin()+i*16,16,j.inverse_bind.begin());
        for(const auto& matrix:{j.local,j.inverse_bind}){for(float v:matrix)ensure(std::isfinite(v)&&std::abs(v)<100000,"invalid canonical matrix");ensure(std::abs(matrix[3])+std::abs(matrix[7])+std::abs(matrix[11])+std::abs(matrix[15]-1)<1e-4,"nonaffine canonical matrix");}
        c.joints.push_back(j);
    }
    for(const auto& node:model.nodes)for(double w:node.weights)ensure(w==0,"canonical nonzero node morph defaults");
    for(double w:model.meshes[0].weights)ensure(w==0,"canonical nonzero mesh morph defaults");
    int instances=0;for(std::size_t i=0;i<model.nodes.size();++i)if(model.nodes[i].mesh>=0){++instances;ensure(model.nodes[i].mesh==0&&model.nodes[i].skin==0&&parents[i]<0&&node_matrix(model.nodes[i])==identity_matrix(),"canonical mesh must be root identity");}
    ensure(instances==1,"canonical mesh instance count");
    const auto& mesh=model.meshes[0];ensure(mesh.extras.IsObject()&&mesh.extras.Has("targetNames"),"canonical target names missing");const auto& names=mesh.extras.Get("targetNames");
    ensure(names.IsArray()&&names.ArrayLen()>0&&names.ArrayLen()<=kMaxCharacterMorphs,"canonical morph limit");
    for(std::size_t i=0;i<names.ArrayLen();++i){ensure(names.Get(int(i)).IsString(),"invalid target name");const auto n=names.Get(int(i)).Get<std::string>();ensure(!n.empty()&&n.size()<128&&std::find(c.morph_names.begin(),c.morph_names.end(),n)==c.morph_names.end(),"duplicate/invalid target name");c.morph_names.push_back(n);}
    c.morphs.resize(c.morph_names.size());
    ensure(mesh.primitives.size()>0&&mesh.primitives.size()<=64,"canonical primitive limit");
    for(const auto& p:mesh.primitives){
        ensure(p.mode==TINYGLTF_MODE_TRIANGLES && p.targets.size()==c.morph_names.size() && p.attributes.size()==5 && !p.attributes.count("JOINTS_1") && !p.attributes.count("WEIGHTS_1"),"invalid canonical primitive");
        auto attr=[&](const char* key){auto it=p.attributes.find(key);ensure(it!=p.attributes.end(),"missing canonical attribute");return it->second;};
        const auto pos=r.read(attr("POSITION"),TINYGLTF_TYPE_VEC3);const auto n=pos.size()/3,base=c.vertices.size();ensure(n>0&&base+n<=100000,"canonical vertex limit");
        const auto normal=r.read(attr("NORMAL"),TINYGLTF_TYPE_VEC3,n),uv=r.read(attr("TEXCOORD_0"),TINYGLTF_TYPE_VEC2,n),joints=r.read(attr("JOINTS_0"),TINYGLTF_TYPE_VEC4,n),weights=r.read(attr("WEIGHTS_0"),TINYGLTF_TYPE_VEC4,n);
        ensure(p.material>=0&&std::size_t(p.material)<model.materials.size(),"canonical material index");const auto& m=model.materials[p.material];const auto& mat=m.pbrMetallicRoughness;
        ensure((m.normalTexture.index<0||m.normalTexture.index==1)&&m.emissiveTexture.index<0&&m.occlusionTexture.index<0&&mat.metallicRoughnessTexture.index<0&&m.extensions.empty()&&m.emissiveFactor==std::vector<double>({0,0,0}),"unsupported material map/extension");
        ensure(mat.baseColorFactor.size()==4&&mat.baseColorTexture.index==0&&mat.baseColorTexture.texCoord==0&&m.normalTexture.texCoord==0&&mat.baseColorTexture.extensions.empty()&&m.normalTexture.extensions.empty()&&(m.alphaMode=="OPAQUE"||m.alphaMode=="MASK"||m.alphaMode=="BLEND"),"invalid canonical material");
        for(auto v:mat.baseColorFactor)ensure(std::isfinite(v)&&v>=0&&v<=1,"invalid material color");
        for(auto v:{mat.metallicFactor,mat.roughnessFactor,m.alphaCutoff})ensure(std::isfinite(v)&&v>=0&&v<=1,"invalid material parameter");
        float depth=0;
        for(std::size_t i=0;i<n;++i){MeshVertex v;MeshSurface surface;
            for(int k=0;k<3;++k){ensure(std::abs(pos[i*3+k])<100000&&std::abs(normal[i*3+k])<=1.01,"invalid canonical vertex");v.position[k]=float(pos[i*3+k]);v.normal[k]=float(normal[i*3+k]);v.color[k]=1;}
            float total=0;for(int k=0;k<4;++k){const auto j=joints[i*4+k],w=weights[i*4+k];ensure(j>=0&&j<c.joints.size()&&j==std::floor(j)&&w>=0&&w<=1,"invalid canonical influence");v.joints[k]=std::uint32_t(j);v.weights[k]=float(w);total+=float(w);}
            ensure(std::abs(total-1)<1e-4,"canonical weight sum");
            for(int k=0;k<2;++k){ensure(uv[i*2+k]>=0&&uv[i*2+k]<=1,"canonical atlas UV bounds");surface.uv[k]=float(uv[i*2+k]);}
            std::copy(mat.baseColorFactor.begin(),mat.baseColorFactor.end(),surface.factor.begin());surface.material={float(mat.metallicFactor),float(mat.roughnessFactor),float(m.alphaCutoff),(m.alphaMode=="BLEND"?2.f:m.alphaMode=="MASK"?1.f:0.f)+(m.doubleSided?0.f:4.f)};
            surface.normal_scale=m.normalTexture.index>=0?float(m.normalTexture.scale):0;ensure(std::isfinite(surface.normal_scale)&&surface.normal_scale>=0&&surface.normal_scale<=4,"normal scale bounds");
            depth+=v.position[2]/float(n);c.vertices.push_back(v);c.surfaces.push_back(surface);
        }
        for(const auto& t:p.targets)for(const auto& [key,_]:t)ensure(key=="POSITION"||key=="NORMAL","canonical unsupported morph semantic");
        for(std::size_t t=0;t<c.morphs.size();++t){
            auto get=[&](const char* key){const auto it=p.targets[t].find(key);return it==p.targets[t].end()?std::vector<double>(n*3):r.read(it->second,TINYGLTF_TYPE_VEC3,n);};
            const auto dp=get("POSITION"),dn=get("NORMAL");auto& target=c.morphs[t];target.resize(base+n);
            for(std::size_t i=0;i<n;++i)for(int k=0;k<3;++k){ensure(std::abs(dp[i*3+k])<100000&&std::abs(dn[i*3+k])<100,"invalid canonical delta");target[base+i].position[k]=float(dp[i*3+k]);target[base+i].normal[k]=float(dn[i*3+k]);}
        }
        const auto indices=r.read(p.indices,TINYGLTF_TYPE_SCALAR);ensure(!indices.empty()&&indices.size()%3==0&&c.indices.size()+indices.size()<=600000,"canonical index limit");
        c.ranges.push_back({std::uint32_t(c.indices.size()),std::uint32_t(indices.size()),m.alphaMode=="BLEND",depth});
        for(auto idx:indices){ensure(idx>=0&&idx<n&&idx==std::floor(idx),"invalid canonical index");c.indices.push_back(std::uint32_t(base+idx));}
    }
    ensure(extra.Has("nativeAtlas")&&extra.Has("camera"),"canonical atlas/camera missing");const auto& atlas=extra.Get("nativeAtlas");
    ensure(atlas.IsObject()&&atlas.Has("width")&&atlas.Has("height")&&atlas.Has("bufferView"),"invalid atlas metadata");
    auto integer=[](const tinygltf::Value& value){ensure(value.IsNumber(),"expected numeric atlas field");const double d=value.GetNumberAsDouble();ensure(std::isfinite(d)&&d>=0&&d<=2147483647&&d==std::floor(d),"expected bounded atlas integer");return int(d);};
    const int w=integer(atlas.Get("width")),h=integer(atlas.Get("height")),v=integer(atlas.Get("bufferView"));
    ensure(w>0&&h>0&&w<=8192&&h<=8192&&std::uint64_t(w)*h<=32*1024*1024&&v>=0&&std::size_t(v)<model.bufferViews.size(),"atlas bounds");
    const auto& view=model.bufferViews[v];ensure(view.buffer>=0&&std::size_t(view.buffer)<model.buffers.size(),"atlas buffer");const auto& bytes=model.buffers[view.buffer].data;
    ensure(view.byteLength==std::size_t(w)*h*4&&view.byteOffset<=bytes.size()&&view.byteLength<=bytes.size()-view.byteOffset,"atlas byte bounds");
    c.atlas_width=std::uint32_t(w);c.atlas_height=std::uint32_t(h);c.atlas.assign(bytes.begin()+view.byteOffset,bytes.begin()+view.byteOffset+view.byteLength);
    ensure(atlas.Has("normalBufferView"),"normal atlas missing");const int nv=integer(atlas.Get("normalBufferView"));ensure(nv>=0&&std::size_t(nv)<model.bufferViews.size(),"normal atlas view");const auto& normalview=model.bufferViews[nv];
    ensure(normalview.buffer>=0&&std::size_t(normalview.buffer)<model.buffers.size(),"normal atlas buffer");const auto& normalbytes=model.buffers[normalview.buffer].data;
    ensure(normalview.byteLength==std::size_t(w)*h*4&&normalview.byteOffset<=normalbytes.size()&&normalview.byteLength<=normalbytes.size()-normalview.byteOffset,"normal atlas bounds");c.normal_atlas.assign(normalbytes.begin()+normalview.byteOffset,normalbytes.begin()+normalview.byteOffset+normalview.byteLength);
    const auto& camera=extra.Get("camera");ensure(camera.IsArray()&&camera.ArrayLen()==4,"invalid native camera");
    for(int i=0;i<4;++i){ensure(camera.Get(i).IsNumber(),"invalid camera value");c.camera[i]=float(camera.Get(i).GetNumberAsDouble());ensure(std::isfinite(c.camera[i])&&std::abs(c.camera[i])<100,"camera bounds");}ensure(c.camera[3]>.1f&&c.camera[3]<20,"camera scale");
    std::stable_sort(c.ranges.begin(),c.ranges.end(),[](const auto& a,const auto& b){if(a.blend!=b.blend)return !a.blend;return a.blend?a.depth<b.depth:false;});
    deform_named_reference(c,{});return c;
}
