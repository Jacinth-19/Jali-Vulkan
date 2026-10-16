// Included inside VulkanFaceRenderer::Impl: shared device/queue/readback ownership.
struct MeshBuffer { VkBuffer buffer=VK_NULL_HANDLE; VkDeviceMemory memory=VK_NULL_HANDLE; void* mapped=nullptr; };
struct MeshImage { VkImage image=VK_NULL_HANDLE; VkDeviceMemory memory=VK_NULL_HANDLE; VkImageView view=VK_NULL_HANDLE; };
struct MeshPose { JointPalette bones; std::array<float,4> morph; };
static_assert(sizeof(MeshPose)==8208,"std140 pose ABI");
static_assert(offsetof(MeshPose,morph)==8192,"shader morph offset after 128 matrices");
MeshBuffer rest_vertices, deformed_vertices, mesh_indices, pose_buffer;
MeshImage color_image,depth_image;
VkRenderPass mesh_pass=VK_NULL_HANDLE;
VkFramebuffer mesh_framebuffer=VK_NULL_HANDLE;
VkDescriptorSetLayout mesh_set_layout=VK_NULL_HANDLE;
VkDescriptorPool mesh_pool=VK_NULL_HANDLE;
VkDescriptorSet mesh_set=VK_NULL_HANDLE;
VkPipelineLayout mesh_layout=VK_NULL_HANDLE;
VkPipeline skin_pipeline=VK_NULL_HANDLE, mesh_pipeline=VK_NULL_HANDLE;
VkShaderModule skin_module=VK_NULL_HANDLE,vertex_module=VK_NULL_HANDLE,fragment_module=VK_NULL_HANDLE;
Character character;
bool mesh_loaded=false, mesh_rendered=false;
void cleanup_mesh() noexcept {
    if(mesh_pipeline)vkDestroyPipeline(device,mesh_pipeline,nullptr);
    if(skin_pipeline)vkDestroyPipeline(device,skin_pipeline,nullptr);
    for(auto m:{skin_module,vertex_module,fragment_module})if(m)vkDestroyShaderModule(device,m,nullptr);
    if(mesh_framebuffer)vkDestroyFramebuffer(device,mesh_framebuffer,nullptr);
    if(mesh_pass)vkDestroyRenderPass(device,mesh_pass,nullptr);
    if(mesh_layout)vkDestroyPipelineLayout(device,mesh_layout,nullptr);
    if(mesh_pool)vkDestroyDescriptorPool(device,mesh_pool,nullptr);
    if(mesh_set_layout)vkDestroyDescriptorSetLayout(device,mesh_set_layout,nullptr);
    for(auto* b:{&rest_vertices,&deformed_vertices,&mesh_indices,&pose_buffer}) {
        if(b->mapped)vkUnmapMemory(device,b->memory);
        if(b->buffer)vkDestroyBuffer(device,b->buffer,nullptr);
        if(b->memory)vkFreeMemory(device,b->memory,nullptr);*b={};
    }
    for(auto* i:{&color_image,&depth_image}) {
        if(i->view)vkDestroyImageView(device,i->view,nullptr);
        if(i->image)vkDestroyImage(device,i->image,nullptr);
        if(i->memory)vkFreeMemory(device,i->memory,nullptr);*i={};
    }
    mesh_pipeline=skin_pipeline=VK_NULL_HANDLE;skin_module=vertex_module=fragment_module=VK_NULL_HANDLE;
    mesh_pass=VK_NULL_HANDLE;mesh_framebuffer=VK_NULL_HANDLE;mesh_layout=VK_NULL_HANDLE;mesh_pool=VK_NULL_HANDLE;mesh_set_layout=VK_NULL_HANDLE;
    mesh_loaded=mesh_rendered=false;
}
std::uint32_t memory_type(std::uint32_t bits,VkMemoryPropertyFlags flags) {
    VkPhysicalDeviceMemoryProperties p{};vkGetPhysicalDeviceMemoryProperties(physical,&p);
    for(std::uint32_t i=0;i<p.memoryTypeCount;++i)if((bits&(1u<<i)) && (p.memoryTypes[i].propertyFlags&flags)==flags)return i;
    throw std::runtime_error("no suitable Vulkan memory type");
}
void make_mesh_buffer(MeshBuffer& b,VkDeviceSize size,VkBufferUsageFlags usage,const void* data=nullptr) {
    VkBufferCreateInfo info{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};info.size=size;info.usage=usage;info.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
    vk_check(vkCreateBuffer(device,&info,nullptr,&b.buffer),"create mesh buffer");
    VkMemoryRequirements r{};vkGetBufferMemoryRequirements(device,b.buffer,&r);
    VkMemoryAllocateInfo a{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};a.allocationSize=r.size;
    a.memoryTypeIndex=memory_type(r.memoryTypeBits,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    vk_check(vkAllocateMemory(device,&a,nullptr,&b.memory),"allocate mesh memory");
    vk_check(vkBindBufferMemory(device,b.buffer,b.memory,0),"bind mesh memory");
    vk_check(vkMapMemory(device,b.memory,0,size,0,&b.mapped),"map mesh memory");if(data)std::memcpy(b.mapped,data,std::size_t(size));
}
void make_mesh_image(MeshImage& image,VkFormat format,VkImageUsageFlags usage,VkImageAspectFlags aspect) {
    VkImageCreateInfo i{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};i.imageType=VK_IMAGE_TYPE_2D;i.format=format;i.extent={width,height,1};
    i.mipLevels=i.arrayLayers=1;i.samples=VK_SAMPLE_COUNT_1_BIT;i.tiling=VK_IMAGE_TILING_OPTIMAL;i.usage=usage;
    i.sharingMode=VK_SHARING_MODE_EXCLUSIVE;i.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED;
    vk_check(vkCreateImage(device,&i,nullptr,&image.image),"create render image");
    VkMemoryRequirements r{};vkGetImageMemoryRequirements(device,image.image,&r);
    VkMemoryAllocateInfo a{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};a.allocationSize=r.size;a.memoryTypeIndex=memory_type(r.memoryTypeBits,0);
    vk_check(vkAllocateMemory(device,&a,nullptr,&image.memory),"allocate render image");
    vk_check(vkBindImageMemory(device,image.image,image.memory,0),"bind render image");
    VkImageViewCreateInfo v{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};v.image=image.image;v.viewType=VK_IMAGE_VIEW_TYPE_2D;v.format=format;
    v.subresourceRange={aspect,0,1,0,1};vk_check(vkCreateImageView(device,&v,nullptr,&image.view),"create render image view");
}
VkShaderModule read_module(const std::filesystem::path& path) {
    std::ifstream f(path,std::ios::binary|std::ios::ate);if(!f)throw std::runtime_error("missing mesh shader");
    const auto n=f.tellg();if(n<20 || n>1024*1024 || n%4)throw std::runtime_error("invalid mesh shader size");
    std::vector<std::uint32_t> words(std::size_t(n)/4);f.seekg(0);f.read(reinterpret_cast<char*>(words.data()),n);
    if(!f || words[0]!=0x07230203)throw std::runtime_error("invalid mesh SPIR-V");
    VkShaderModuleCreateInfo info{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};info.codeSize=std::size_t(n);info.pCode=words.data();
    VkShaderModule module;vk_check(vkCreateShaderModule(device,&info,nullptr,&module),"create mesh shader module");return module;
}
void load_mesh(Character imported,const std::filesystem::path& shaders) {
    vk_check(vkDeviceWaitIdle(device),"wait before character replacement");cleanup_mesh();character=std::move(imported);
    VkPhysicalDeviceProperties props{};vkGetPhysicalDeviceProperties(physical,&props);
    if(character.vertices.size()*sizeof(MeshVertex)>props.limits.maxStorageBufferRange || props.limits.maxUniformBufferRange<sizeof(MeshPose))
        throw std::runtime_error("character exceeds device buffer limits");
    VkFormatProperties depth_props{};vkGetPhysicalDeviceFormatProperties(physical,VK_FORMAT_D32_SFLOAT,&depth_props);
    if(!(depth_props.optimalTilingFeatures&VK_FORMAT_FEATURE_DEPTH_STENCIL_ATTACHMENT_BIT))throw std::runtime_error("D32 depth attachments unsupported");
    make_mesh_buffer(rest_vertices,character.vertices.size()*sizeof(MeshVertex),VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,character.vertices.data());
    make_mesh_buffer(deformed_vertices,character.vertices.size()*9*sizeof(float),VK_BUFFER_USAGE_STORAGE_BUFFER_BIT|VK_BUFFER_USAGE_VERTEX_BUFFER_BIT);
    make_mesh_buffer(mesh_indices,character.indices.size()*4,VK_BUFFER_USAGE_INDEX_BUFFER_BIT,character.indices.data());
    make_mesh_buffer(pose_buffer,sizeof(MeshPose),VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT);
    make_mesh_image(color_image,VK_FORMAT_R8G8B8A8_UNORM,VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|VK_IMAGE_USAGE_TRANSFER_SRC_BIT,VK_IMAGE_ASPECT_COLOR_BIT);
    make_mesh_image(depth_image,VK_FORMAT_D32_SFLOAT,VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,VK_IMAGE_ASPECT_DEPTH_BIT);
    std::array<VkAttachmentDescription,2> attachments{};
    attachments[0].format=VK_FORMAT_R8G8B8A8_UNORM;attachments[0].samples=VK_SAMPLE_COUNT_1_BIT;
    attachments[0].loadOp=VK_ATTACHMENT_LOAD_OP_CLEAR;attachments[0].storeOp=VK_ATTACHMENT_STORE_OP_STORE;
    attachments[0].stencilLoadOp=VK_ATTACHMENT_LOAD_OP_DONT_CARE;attachments[0].stencilStoreOp=VK_ATTACHMENT_STORE_OP_DONT_CARE;
    attachments[0].initialLayout=VK_IMAGE_LAYOUT_UNDEFINED;attachments[0].finalLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
    attachments[1]=attachments[0];attachments[1].format=VK_FORMAT_D32_SFLOAT;attachments[1].storeOp=VK_ATTACHMENT_STORE_OP_DONT_CARE;
    attachments[1].finalLayout=VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
    VkAttachmentReference color{0,VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL},depth{1,VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL};
    VkSubpassDescription subpass{};subpass.pipelineBindPoint=VK_PIPELINE_BIND_POINT_GRAPHICS;subpass.colorAttachmentCount=1;subpass.pColorAttachments=&color;subpass.pDepthStencilAttachment=&depth;
    VkSubpassDependency dependency{};dependency.srcSubpass=VK_SUBPASS_EXTERNAL;dependency.dstSubpass=0;
    dependency.srcStageMask=VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT;dependency.dstStageMask=VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT|VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
    dependency.dstAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT|VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
    VkRenderPassCreateInfo pass{VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO};pass.attachmentCount=2;pass.pAttachments=attachments.data();pass.subpassCount=1;pass.pSubpasses=&subpass;pass.dependencyCount=1;pass.pDependencies=&dependency;
    vk_check(vkCreateRenderPass(device,&pass,nullptr,&mesh_pass),"create mesh render pass");
    const VkImageView views[]{color_image.view,depth_image.view};
    VkFramebufferCreateInfo fb{VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO};fb.renderPass=mesh_pass;fb.attachmentCount=2;fb.pAttachments=views;fb.width=width;fb.height=height;fb.layers=1;
    vk_check(vkCreateFramebuffer(device,&fb,nullptr,&mesh_framebuffer),"create framebuffer");
    std::array<VkDescriptorSetLayoutBinding,3> bindings{};
    for(int b=0;b<3;++b) {bindings[b].binding=b;bindings[b].descriptorCount=1;bindings[b].descriptorType=b==2 ? VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER : VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;bindings[b].stageFlags=VK_SHADER_STAGE_COMPUTE_BIT;}
    VkDescriptorSetLayoutCreateInfo set{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};set.bindingCount=3;set.pBindings=bindings.data();
    vk_check(vkCreateDescriptorSetLayout(device,&set,nullptr,&mesh_set_layout),"create skin descriptors");
    const VkDescriptorPoolSize sizes[]{{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,2},{VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,1}};
    VkDescriptorPoolCreateInfo pool{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};pool.maxSets=1;pool.poolSizeCount=2;pool.pPoolSizes=sizes;
    vk_check(vkCreateDescriptorPool(device,&pool,nullptr,&mesh_pool),"create mesh descriptor pool");
    VkDescriptorSetAllocateInfo allocation{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};allocation.descriptorPool=mesh_pool;allocation.descriptorSetCount=1;allocation.pSetLayouts=&mesh_set_layout;
    vk_check(vkAllocateDescriptorSets(device,&allocation,&mesh_set),"allocate mesh descriptors");
    const VkDescriptorBufferInfo infos[]{{rest_vertices.buffer,0,VK_WHOLE_SIZE},{deformed_vertices.buffer,0,VK_WHOLE_SIZE},{pose_buffer.buffer,0,sizeof(MeshPose)}};
    std::array<VkWriteDescriptorSet,3> writes{};for(int b=0;b<3;++b){writes[b].sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;writes[b].dstSet=mesh_set;writes[b].dstBinding=b;writes[b].descriptorCount=1;writes[b].descriptorType=bindings[b].descriptorType;writes[b].pBufferInfo=&infos[b];}
    vkUpdateDescriptorSets(device,3,writes.data(),0,nullptr);
    VkPushConstantRange push{VK_SHADER_STAGE_COMPUTE_BIT,0,4};
    VkPipelineLayoutCreateInfo layout{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};layout.setLayoutCount=1;layout.pSetLayouts=&mesh_set_layout;layout.pushConstantRangeCount=1;layout.pPushConstantRanges=&push;
    vk_check(vkCreatePipelineLayout(device,&layout,nullptr,&mesh_layout),"create skin pipeline layout");
    skin_module=read_module(shaders/"skin.comp.spv");vertex_module=read_module(shaders/"mesh.vert.spv");fragment_module=read_module(shaders/"mesh.frag.spv");
    VkComputePipelineCreateInfo skin{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};skin.layout=mesh_layout;skin.stage.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;skin.stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;skin.stage.module=skin_module;skin.stage.pName="main";
    vk_check(vkCreateComputePipelines(device,VK_NULL_HANDLE,1,&skin,nullptr,&skin_pipeline),"create GPU skinning pipeline");
    std::array<VkPipelineShaderStageCreateInfo,2> stages{};for(int i=0;i<2;++i){stages[i].sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;stages[i].stage=i ? VK_SHADER_STAGE_FRAGMENT_BIT : VK_SHADER_STAGE_VERTEX_BIT;stages[i].module=i ? fragment_module : vertex_module;stages[i].pName="main";}
    VkVertexInputBindingDescription vertex_binding{0,9*sizeof(float),VK_VERTEX_INPUT_RATE_VERTEX};
    VkVertexInputAttributeDescription attributes[]{{0,0,VK_FORMAT_R32G32B32_SFLOAT,0},{1,0,VK_FORMAT_R32G32B32_SFLOAT,12},{2,0,VK_FORMAT_R32G32B32_SFLOAT,24}};
    VkPipelineVertexInputStateCreateInfo vertex{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};vertex.vertexBindingDescriptionCount=1;vertex.pVertexBindingDescriptions=&vertex_binding;vertex.vertexAttributeDescriptionCount=3;vertex.pVertexAttributeDescriptions=attributes;
    VkPipelineInputAssemblyStateCreateInfo assembly{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};assembly.topology=VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
    VkViewport viewport{0,0,float(width),float(height),0,1};VkRect2D scissor{{0,0},{width,height}};
    VkPipelineViewportStateCreateInfo view{VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO};view.viewportCount=1;view.pViewports=&viewport;view.scissorCount=1;view.pScissors=&scissor;
    VkPipelineRasterizationStateCreateInfo raster{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO};raster.polygonMode=VK_POLYGON_MODE_FILL;raster.cullMode=VK_CULL_MODE_NONE;raster.frontFace=VK_FRONT_FACE_COUNTER_CLOCKWISE;raster.lineWidth=1;
    VkPipelineMultisampleStateCreateInfo sample{VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO};sample.rasterizationSamples=VK_SAMPLE_COUNT_1_BIT;
    VkPipelineDepthStencilStateCreateInfo depth_state{VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO};depth_state.depthTestEnable=VK_TRUE;depth_state.depthWriteEnable=VK_TRUE;depth_state.depthCompareOp=VK_COMPARE_OP_LESS;
    VkPipelineColorBlendAttachmentState blend{};blend.colorWriteMask=15;
    VkPipelineColorBlendStateCreateInfo blending{VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO};blending.attachmentCount=1;blending.pAttachments=&blend;
    VkGraphicsPipelineCreateInfo graphics{VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO};graphics.stageCount=2;graphics.pStages=stages.data();graphics.pVertexInputState=&vertex;graphics.pInputAssemblyState=&assembly;graphics.pViewportState=&view;graphics.pRasterizationState=&raster;graphics.pMultisampleState=&sample;graphics.pDepthStencilState=&depth_state;graphics.pColorBlendState=&blending;graphics.layout=mesh_layout;graphics.renderPass=mesh_pass;
    vk_check(vkCreateGraphicsPipelines(device,VK_NULL_HANDLE,1,&graphics,nullptr,&mesh_pipeline),"create mesh graphics pipeline");mesh_loaded=true;
}
std::vector<std::uint8_t> draw_mesh(SpeechPose pose) {
    if(!mesh_loaded)throw std::invalid_argument("load an imported character before rendering a pose");
    const MeshPose uniform{character_palette(character,pose),{pose.jaw,pose.round,pose.close,0}};
    std::memcpy(pose_buffer.mapped,&uniform,sizeof(uniform));
    vk_check(vkResetCommandBuffer(command,0),"reset mesh command");VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};begin.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    vk_check(vkBeginCommandBuffer(command,&begin),"begin mesh command");
    vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_COMPUTE,skin_pipeline);vkCmdBindDescriptorSets(command,VK_PIPELINE_BIND_POINT_COMPUTE,mesh_layout,0,1,&mesh_set,0,nullptr);
    const auto count=std::uint32_t(character.vertices.size());vkCmdPushConstants(command,mesh_layout,VK_SHADER_STAGE_COMPUTE_BIT,0,4,&count);vkCmdDispatch(command,(count+63)/64,1,1);
    VkBufferMemoryBarrier skin_barrier{VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER};skin_barrier.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;skin_barrier.dstAccessMask=VK_ACCESS_VERTEX_ATTRIBUTE_READ_BIT|VK_ACCESS_HOST_READ_BIT;skin_barrier.srcQueueFamilyIndex=skin_barrier.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;skin_barrier.buffer=deformed_vertices.buffer;skin_barrier.size=VK_WHOLE_SIZE;
    vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_VERTEX_INPUT_BIT|VK_PIPELINE_STAGE_HOST_BIT,0,0,nullptr,1,&skin_barrier,0,nullptr);
    VkClearValue clears[2]{};clears[0].color={{.035f,.065f,.09f,1}};clears[1].depthStencil={1,0};
    VkRenderPassBeginInfo render{VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO};render.renderPass=mesh_pass;render.framebuffer=mesh_framebuffer;render.renderArea={{0,0},{width,height}};render.clearValueCount=2;render.pClearValues=clears;
    vkCmdBeginRenderPass(command,&render,VK_SUBPASS_CONTENTS_INLINE);vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_GRAPHICS,mesh_pipeline);
    const VkDeviceSize offset=0;vkCmdBindVertexBuffers(command,0,1,&deformed_vertices.buffer,&offset);vkCmdBindIndexBuffer(command,mesh_indices.buffer,0,VK_INDEX_TYPE_UINT32);
    vkCmdDrawIndexed(command,std::uint32_t(character.indices.size()),1,0,0,0);vkCmdEndRenderPass(command);
    VkImageMemoryBarrier image{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};image.srcAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;image.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT;image.oldLayout=image.newLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;image.srcQueueFamilyIndex=image.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;image.image=color_image.image;image.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
    vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&image);
    VkBufferImageCopy copy{};copy.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1};copy.imageExtent={width,height,1};vkCmdCopyImageToBuffer(command,color_image.image,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,buffer,1,&copy);
    VkBufferMemoryBarrier host{VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER};host.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;host.dstAccessMask=VK_ACCESS_HOST_READ_BIT;host.srcQueueFamilyIndex=host.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;host.buffer=buffer;host.size=VK_WHOLE_SIZE;
    vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,0,nullptr,1,&host,0,nullptr);
    vk_check(vkEndCommandBuffer(command),"end mesh command");VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};submit.commandBufferCount=1;submit.pCommandBuffers=&command;
    vk_check(vkQueueSubmit(queue,1,&submit,fence),"submit mesh render");vk_check(vkWaitForFences(device,1,&fence,VK_TRUE,30'000'000'000ull),"wait for mesh render");vk_check(vkResetFences(device,1,&fence),"reset mesh fence");
    std::vector<std::uint8_t> pixels(static_cast<std::size_t>(bytes));std::memcpy(pixels.data(),mapped,pixels.size());mesh_rendered=true;return pixels;
}
