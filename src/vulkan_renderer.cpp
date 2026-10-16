#include "jali/vulkan_renderer.hpp"
#include <vulkan/vulkan.h>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <utility>

namespace jali {
namespace {
void vk_check(VkResult result, const char* operation) {
    if (result != VK_SUCCESS)
        throw std::runtime_error(std::string(operation) + " failed (VkResult " + std::to_string(result) + ")");
}
struct Push { std::uint32_t width, height; float jaw, time; };
static_assert(sizeof(Push) == 16, "shader push-constant ABI");
}
struct VulkanFaceRenderer::Impl {
    VkInstance instance = VK_NULL_HANDLE;
    VkPhysicalDevice physical = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    VkQueue queue = VK_NULL_HANDLE;
    VkBuffer buffer = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkDescriptorSetLayout set_layout = VK_NULL_HANDLE;
    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkShaderModule shader_module = VK_NULL_HANDLE;
    VkDescriptorPool descriptor_pool = VK_NULL_HANDLE;
    VkDescriptorSet descriptor_set = VK_NULL_HANDLE;
    VkCommandPool command_pool = VK_NULL_HANDLE;
    VkCommandBuffer command = VK_NULL_HANDLE;
    VkFence fence = VK_NULL_HANDLE;
    void* mapped = nullptr;
    std::uint32_t width, height, family = 0;
    VkDeviceSize bytes;
    std::string name;
    bool hardware = false, require_hardware = false;
    #include "vulkan_mesh.inc"

    Impl(std::uint32_t w, std::uint32_t h, const std::filesystem::path& shader, bool require_gpu)
        : width(w), height(h), bytes(VkDeviceSize(w) * h * 4), require_hardware(require_gpu) {
        if (w < 32 || h < 32 || w > 2048 || h > 2048)
            throw std::invalid_argument("render dimensions must be between 32 and 2048");
        try { initialize(shader); } catch (...) { cleanup(); throw; }
    }
    ~Impl() { cleanup(); }
    void cleanup() noexcept {
        if (device) {
            vkDeviceWaitIdle(device);
            cleanup_mesh();
            if (mapped) vkUnmapMemory(device, memory);
            if (fence) vkDestroyFence(device, fence, nullptr);
            if (command_pool) vkDestroyCommandPool(device, command_pool, nullptr);
            if (pipeline) vkDestroyPipeline(device, pipeline, nullptr);
            if (shader_module) vkDestroyShaderModule(device, shader_module, nullptr);
            if (pipeline_layout) vkDestroyPipelineLayout(device, pipeline_layout, nullptr);
            if (descriptor_pool) vkDestroyDescriptorPool(device, descriptor_pool, nullptr);
            if (set_layout) vkDestroyDescriptorSetLayout(device, set_layout, nullptr);
            if (buffer) vkDestroyBuffer(device, buffer, nullptr);
            if (memory) vkFreeMemory(device, memory, nullptr);
            vkDestroyDevice(device, nullptr);
        }
        if (instance) vkDestroyInstance(instance, nullptr);
    }
    void initialize(const std::filesystem::path& shader_path) {
        VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
        app.pApplicationName = "Jali offscreen face";
        app.apiVersion = VK_API_VERSION_1_0;
        VkInstanceCreateInfo instance_info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
        instance_info.pApplicationInfo = &app;
        vk_check(vkCreateInstance(&instance_info, nullptr, &instance), "vkCreateInstance");
        std::uint32_t count = 0;
        vk_check(vkEnumeratePhysicalDevices(instance, &count, nullptr), "enumerate devices");
        if (!count) throw std::runtime_error("no Vulkan device/ICD; install a driver or select SwiftShader");
        std::vector<VkPhysicalDevice> devices(count);
        vk_check(vkEnumeratePhysicalDevices(instance, &count, devices.data()), "enumerate devices");
        int best = -1;
        for (auto candidate : devices) {
            VkPhysicalDeviceProperties props{};
            vkGetPhysicalDeviceProperties(candidate, &props);
            std::uint32_t queue_count = 0;
            vkGetPhysicalDeviceQueueFamilyProperties(candidate, &queue_count, nullptr);
            std::vector<VkQueueFamilyProperties> families(queue_count);
            vkGetPhysicalDeviceQueueFamilyProperties(candidate, &queue_count, families.data());
            for (std::uint32_t i = 0; i < queue_count; ++i) {
                const int score = props.deviceType == VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU ? 3 :
                                  props.deviceType == VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU ? 2 : 1;
                if (families[i].queueCount && (families[i].queueFlags & (VK_QUEUE_COMPUTE_BIT|VK_QUEUE_GRAPHICS_BIT)) == (VK_QUEUE_COMPUTE_BIT|VK_QUEUE_GRAPHICS_BIT) && score > best && (!require_hardware || score >= 2)) {
                    best = score; physical = candidate; family = i; name = props.deviceName; hardware = score >= 2;
                }
            }
        }
        if (!physical) throw std::runtime_error("no compatible Vulkan device (hardware GPU required when requested)");
        VkPhysicalDeviceProperties props{};
        vkGetPhysicalDeviceProperties(physical, &props);
        if (bytes > props.limits.maxStorageBufferRange || props.limits.maxPushConstantsSize < sizeof(Push) ||
            props.limits.maxComputeWorkGroupInvocations < 64 || props.limits.maxComputeWorkGroupSize[0] < 8 ||
            props.limits.maxComputeWorkGroupSize[1] < 8)
            throw std::runtime_error("Vulkan device limits do not support the face shader");
        const float priority = 1;
        VkDeviceQueueCreateInfo queue_info{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
        queue_info.queueFamilyIndex = family; queue_info.queueCount = 1; queue_info.pQueuePriorities = &priority;
        VkDeviceCreateInfo device_info{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
        device_info.queueCreateInfoCount = 1; device_info.pQueueCreateInfos = &queue_info;
        vk_check(vkCreateDevice(physical, &device_info, nullptr, &device), "vkCreateDevice");
        vkGetDeviceQueue(device, family, 0, &queue);

        VkBufferCreateInfo buffer_info{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
        buffer_info.size = bytes; buffer_info.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT;
        buffer_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
        vk_check(vkCreateBuffer(device, &buffer_info, nullptr, &buffer), "vkCreateBuffer");
        VkMemoryRequirements requirements{};
        vkGetBufferMemoryRequirements(device, buffer, &requirements);
        VkPhysicalDeviceMemoryProperties memory_props{};
        vkGetPhysicalDeviceMemoryProperties(physical, &memory_props);
        std::uint32_t memory_type = memory_props.memoryTypeCount;
        const auto flags = VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;
        for (std::uint32_t i = 0; i < memory_props.memoryTypeCount; ++i)
            if ((requirements.memoryTypeBits & (1u << i)) &&
                (memory_props.memoryTypes[i].propertyFlags & flags) == static_cast<VkMemoryPropertyFlags>(flags)) {
                memory_type = i; break;
            }
        if (memory_type == memory_props.memoryTypeCount)
            throw std::runtime_error("renderer requires host-visible coherent storage memory");
        VkMemoryAllocateInfo allocation{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        allocation.allocationSize = requirements.size; allocation.memoryTypeIndex = memory_type;
        vk_check(vkAllocateMemory(device, &allocation, nullptr, &memory), "vkAllocateMemory");
        vk_check(vkBindBufferMemory(device, buffer, memory, 0), "vkBindBufferMemory");
        vk_check(vkMapMemory(device, memory, 0, bytes, 0, &mapped), "vkMapMemory");

        VkDescriptorSetLayoutBinding binding{};
        binding.binding = 0; binding.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        binding.descriptorCount = 1; binding.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
        VkDescriptorSetLayoutCreateInfo set_info{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        set_info.bindingCount = 1; set_info.pBindings = &binding;
        vk_check(vkCreateDescriptorSetLayout(device, &set_info, nullptr, &set_layout), "create descriptor layout");
        VkPushConstantRange range{VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(Push)};
        VkPipelineLayoutCreateInfo layout_info{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        layout_info.setLayoutCount = 1; layout_info.pSetLayouts = &set_layout;
        layout_info.pushConstantRangeCount = 1; layout_info.pPushConstantRanges = &range;
        vk_check(vkCreatePipelineLayout(device, &layout_info, nullptr, &pipeline_layout), "create pipeline layout");
        std::ifstream shader(shader_path, std::ios::binary | std::ios::ate);
        if (!shader) throw std::runtime_error("cannot open SPIR-V shader: " + shader_path.string());
        const auto length = shader.tellg();
        if (length < 20 || length > 1024 * 1024 || length % 4 != 0)
            throw std::runtime_error("invalid SPIR-V file size");
        std::vector<std::uint32_t> words(static_cast<std::size_t>(length) / 4);
        shader.seekg(0); shader.read(reinterpret_cast<char*>(words.data()), length);
        if (!shader || words[0] != 0x07230203) throw std::runtime_error("invalid SPIR-V shader");
        VkShaderModuleCreateInfo shader_info{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};
        shader_info.codeSize = static_cast<std::size_t>(length); shader_info.pCode = words.data();
        vk_check(vkCreateShaderModule(device, &shader_info, nullptr, &shader_module), "create shader module");
        VkComputePipelineCreateInfo pipeline_info{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};
        pipeline_info.stage.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        pipeline_info.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        pipeline_info.stage.module = shader_module; pipeline_info.stage.pName = "main";
        pipeline_info.layout = pipeline_layout;
        vk_check(vkCreateComputePipelines(device, VK_NULL_HANDLE, 1, &pipeline_info, nullptr, &pipeline), "create compute pipeline");

        VkDescriptorPoolSize pool_size{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1};
        VkDescriptorPoolCreateInfo pool_info{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        pool_info.maxSets = 1; pool_info.poolSizeCount = 1; pool_info.pPoolSizes = &pool_size;
        vk_check(vkCreateDescriptorPool(device, &pool_info, nullptr, &descriptor_pool), "create descriptor pool");
        VkDescriptorSetAllocateInfo set_allocation{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        set_allocation.descriptorPool = descriptor_pool; set_allocation.descriptorSetCount = 1;
        set_allocation.pSetLayouts = &set_layout;
        vk_check(vkAllocateDescriptorSets(device, &set_allocation, &descriptor_set), "allocate descriptor set");
        VkDescriptorBufferInfo descriptor_buffer{buffer, 0, bytes};
        VkWriteDescriptorSet write{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
        write.dstSet = descriptor_set; write.dstBinding = 0; write.descriptorCount = 1;
        write.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER; write.pBufferInfo = &descriptor_buffer;
        vkUpdateDescriptorSets(device, 1, &write, 0, nullptr);
        VkCommandPoolCreateInfo pool{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
        pool.queueFamilyIndex = family; pool.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        vk_check(vkCreateCommandPool(device, &pool, nullptr, &command_pool), "create command pool");
        VkCommandBufferAllocateInfo commands{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
        commands.commandPool = command_pool; commands.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        commands.commandBufferCount = 1;
        vk_check(vkAllocateCommandBuffers(device, &commands, &command), "allocate command buffer");
        VkFenceCreateInfo fence_info{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
        vk_check(vkCreateFence(device, &fence_info, nullptr, &fence), "create fence");
    }
    std::vector<std::uint8_t> draw(float jaw, float time) {
        vk_check(vkResetCommandBuffer(command, 0), "reset command buffer");
        VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
        begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        vk_check(vkBeginCommandBuffer(command, &begin), "begin command buffer");
        vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline);
        vkCmdBindDescriptorSets(command, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline_layout, 0, 1, &descriptor_set, 0, nullptr);
        const Push push{width, height, jaw, time};
        vkCmdPushConstants(command, pipeline_layout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(push), &push);
        vkCmdDispatch(command, (width + 7) / 8, (height + 7) / 8, 1);
        VkBufferMemoryBarrier barrier{VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER};
        barrier.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT; barrier.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
        barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED; barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        barrier.buffer = buffer; barrier.size = VK_WHOLE_SIZE;
        vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_HOST_BIT,
                             0, 0, nullptr, 1, &barrier, 0, nullptr);
        vk_check(vkEndCommandBuffer(command), "end command buffer");
        VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};
        submit.commandBufferCount = 1; submit.pCommandBuffers = &command;
        vk_check(vkQueueSubmit(queue, 1, &submit, fence), "submit compute render");
        vk_check(vkWaitForFences(device, 1, &fence, VK_TRUE, 30'000'000'000ull), "wait for render fence");
        vk_check(vkResetFences(device, 1, &fence), "reset render fence");
        std::vector<std::uint8_t> output(static_cast<std::size_t>(bytes));
        std::memcpy(output.data(), mapped, output.size());
        return output;
    }
};
VulkanFaceRenderer::VulkanFaceRenderer(std::uint32_t w, std::uint32_t h, const std::filesystem::path& shader, bool require_hardware)
    : impl_(std::make_unique<Impl>(w, h, shader, require_hardware)) {}
VulkanFaceRenderer::~VulkanFaceRenderer() = default;
std::string VulkanFaceRenderer::device_name() const { return impl_->name; }
bool VulkanFaceRenderer::hardware_accelerated() const { return impl_->hardware; }
void VulkanFaceRenderer::load_character(const std::filesystem::path& path) {
    impl_->load_mesh(load_character_glb(path), std::filesystem::path(JALI_MESH_SHADER_DIR));
}
std::vector<std::uint8_t> VulkanFaceRenderer::render_pose(SpeechPose pose) { return impl_->draw_mesh(pose); }
std::vector<std::array<float,3>> VulkanFaceRenderer::deformed_positions() const {
    if (!impl_->mesh_rendered) throw std::invalid_argument("render a mesh pose before reading deformed positions");
    std::vector<std::array<float,3>> out(impl_->character.vertices.size());
    const auto* words=static_cast<const float*>(impl_->deformed_vertices.mapped);
    for(std::size_t i=0;i<out.size();++i) std::copy_n(words+i*20,3,out[i].begin());
    return out;
}
std::vector<std::uint8_t> VulkanFaceRenderer::render_named_pose(const MorphWeights& weights,BoneMotion motion) { return impl_->draw_mesh({},weights,motion); }
std::vector<std::array<float,3>> VulkanFaceRenderer::deformed_normals() const {
    if(!impl_->mesh_rendered)throw std::invalid_argument("render before normals readback");
    std::vector<std::array<float,3>> out(impl_->character.vertices.size());const auto* words=static_cast<const float*>(impl_->deformed_vertices.mapped);
    for(std::size_t i=0;i<out.size();++i)std::copy_n(words+i*20+3,3,out[i].begin());return out;
}
void VulkanFaceRenderer::submit(const Rig& rig, const std::vector<FaceFrame>& frames) {
    validate_frames(rig, frames);
    if (rig.morph_channels.size() != 1 || rig.morph_channels[0].name != "jawOpen")
        throw std::invalid_argument("procedural Vulkan face expects one jawOpen channel");
    for (const auto& frame : frames)
        if (frame.morph_weights[0] < 0 || frame.morph_weights[0] > 1)
            throw std::invalid_argument("Vulkan jawOpen must be normalized");
    frames_ = frames;
}
std::vector<std::uint8_t> VulkanFaceRenderer::render(double time) {
    if (!std::isfinite(time) || time < 0 || time > 60 || frames_.empty())
        throw std::invalid_argument("render requires a timeline and finite time in [0,60]");
    auto right = std::lower_bound(frames_.begin(), frames_.end(), time,
        [](const FaceFrame& frame, double t) { return frame.audio_time_seconds < t; });
    float jaw = 0;
    if (right == frames_.begin()) jaw = right->morph_weights[0];
    else if (right == frames_.end()) jaw = frames_.back().morph_weights[0];
    else {
        const auto& left = *(right - 1);
        const auto alpha = (time - left.audio_time_seconds) / (right->audio_time_seconds - left.audio_time_seconds);
        jaw = static_cast<float>(left.morph_weights[0] * (1-alpha) + right->morph_weights[0] * alpha);
    }
    return impl_->draw(jaw, static_cast<float>(time));
}
std::uint32_t VulkanFaceRenderer::write_sequence(const std::filesystem::path& output, double duration, std::uint32_t fps) {
    if (!std::isfinite(duration) || duration <= 0 || duration > 60 || fps < 1 || fps > 60)
        throw std::invalid_argument("sequence requires 0-60 seconds at 1-60 FPS");
    const auto count = static_cast<std::uint32_t>(std::ceil(duration * fps));
    if (impl_->bytes * count > 1024ull * 1024 * 1024)
        throw std::invalid_argument("raw video exceeds 1 GiB limit; reduce size, FPS, or text length");
    std::ofstream stream(output, std::ios::binary);
    if (!stream) throw std::runtime_error("cannot create raw frame sequence");
    for (std::uint32_t i = 0; i < count; ++i) {
        auto frame = render(double(i) / fps);
        stream.write(reinterpret_cast<const char*>(frame.data()), static_cast<std::streamsize>(frame.size()));
        if (!stream) throw std::runtime_error("frame sequence write failed");
    }
    stream.flush();
    if (!stream) throw std::runtime_error("frame sequence flush failed");
    return count;
}
} // namespace jali
