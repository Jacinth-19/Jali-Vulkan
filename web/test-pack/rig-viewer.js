'use strict';
// Inspector for our generated two-bone GLB fixture, not the native Vulkan renderer.
// Embedded data makes this test pack usable from file:// on Windows without a server.
(() => {
  const canvas = document.getElementById('rig');
  const status = document.getElementById('rig-status');
  try {
    const gl = canvas.getContext('webgl2', { antialias: true, alpha: false });
    if (!gl) throw new Error('WebGL 2 is unavailable. The native-rendered rest image is shown instead.');
    const bytes = Uint8Array.from(atob(window.JALI_RIG_BASE64), c => c.charCodeAt(0));
    const header = new DataView(bytes.buffer);
    if (header.getUint32(0, true) !== 0x46546c67) throw new Error('Invalid GLB header');
    const jsonLength = header.getUint32(12, true);
    const model = JSON.parse(new TextDecoder().decode(bytes.subarray(20, 20 + jsonLength)));
    const binaryOffset = 28 + jsonLength;
    const primitive = model.meshes[0].primitives[0];
    const targetNames = model.meshes[0].extras.targetNames;
    const identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
    const pivot = model.nodes.find(n => n.name === 'Jaw').translation[1];
    const shader = (type, source) => {
      const value = gl.createShader(type); gl.shaderSource(value, source); gl.compileShader(value);
      if (!gl.getShaderParameter(value, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(value));
      return value;
    };
    const vertex = shader(gl.VERTEX_SHADER, `#version 300 es
      precision highp float;
      layout(location=0) in vec3 position;
      layout(location=1) in vec3 normal;
      layout(location=2) in vec3 color;
      layout(location=3) in uvec4 joints;
      layout(location=4) in vec4 weights;
      layout(location=5) in vec3 jawDelta;
      layout(location=6) in vec3 roundDelta;
      layout(location=7) in vec3 closeDelta;
      uniform mat4 bones[2];
      uniform vec3 pose;
      uniform vec2 orbit;
      uniform float aspect;
      out vec3 faceNormal;
      out vec3 faceColor;
      void main() {
        vec3 p = position + jawDelta * pose.x + roundDelta * pose.y + closeDelta * pose.z;
        mat4 skin = bones[joints.x]*weights.x + bones[joints.y]*weights.y + bones[joints.z]*weights.z + bones[joints.w]*weights.w;
        p = (skin * vec4(p, 1.0)).xyz;
        vec3 n = mat3(skin) * normal;
        float cy=cos(orbit.x), sy=sin(orbit.x), cx=cos(orbit.y), sx=sin(orbit.y);
        mat3 rotation = mat3(1,0,0, 0,cx,sx, 0,-sx,cx) * mat3(cy,0,-sy, 0,1,0, sy,0,cy);
        p.y += 0.4;
        p = rotation * p;
        faceNormal = rotation * n; faceColor = color;
        gl_Position = vec4(p.x * 0.64 / aspect, p.y * 0.64, -p.z * 0.2, 1.0);
      }`);
    const fragment = shader(gl.FRAGMENT_SHADER, `#version 300 es
      precision highp float;
      in vec3 faceNormal;
      in vec3 faceColor;
      out vec4 result;
      void main() {
        vec3 n=normalize(faceNormal), light=normalize(vec3(-0.65,0.9,1.6));
        float diffuse=max(dot(n,light),0.0);
        float spec=pow(max(dot(reflect(-light,n),vec3(0,0,1)),0.0),40.0);
        vec3 c=faceColor*(0.19+0.8*diffuse)+spec*0.45;
        c+=pow(1.0-max(n.z,0.0),3.0)*vec3(0.01,0.8,1.0)*0.2;
        if(faceColor.g>0.7 && faceColor.r<0.15)c=faceColor*0.95;
        result=vec4(pow(clamp(c,0.0,1.0),vec3(1.0/2.2)),1.0);
      }`);
    const program = gl.createProgram(); gl.attachShader(program, vertex); gl.attachShader(program, fragment); gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);
    const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
    function upload(accessorIndex, location, target = gl.ARRAY_BUFFER) {
      const a = model.accessors[accessorIndex], view = model.bufferViews[a.bufferView];
      const components = { VEC3: 3, VEC4: 4, SCALAR: 1 }[a.type];
      const componentBytes = { 5126: 4, 5123: 2, 5125: 4 }[a.componentType];
      if (!components || !componentBytes || view.byteStride || a.sparse) throw new Error('Unsupported inspector accessor');
      const offset = binaryOffset + (view.byteOffset || 0) + (a.byteOffset || 0);
      const buffer = gl.createBuffer(); gl.bindBuffer(target, buffer);
      gl.bufferData(target, bytes.subarray(offset, offset + a.count * components * componentBytes), gl.STATIC_DRAW);
      if (location !== null) {
        gl.enableVertexAttribArray(location);
        if (location === 3) gl.vertexAttribIPointer(location, components, a.componentType, 0, 0);
        else gl.vertexAttribPointer(location, components, a.componentType, false, 0, 0);
      }
      return a;
    }
    ['POSITION', 'NORMAL', 'COLOR_0', 'JOINTS_0', 'WEIGHTS_0'].forEach((name, i) => upload(primitive.attributes[name], i));
    ['jawOpen', 'mouthRound', 'mouthClose'].forEach((name, i) => upload(primitive.targets[targetNames.indexOf(name)].POSITION, 5 + i));
    const indices = upload(primitive.indices, null, gl.ELEMENT_ARRAY_BUFFER);
    const bonesLocation = gl.getUniformLocation(program, 'bones[0]');
    const poseLocation = gl.getUniformLocation(program, 'pose');
    const orbitLocation = gl.getUniformLocation(program, 'orbit');
    const aspectLocation = gl.getUniformLocation(program, 'aspect');
    let yaw = -0.10, pitch = 0, dragging = false, lastX = 0, lastY = 0;
    const controls = ['jaw', 'round', 'close'].map(id => document.getElementById(id));
    function draw() {
      const ratio = Math.min(devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.round(canvas.clientWidth * ratio));
      canvas.height = Math.max(1, Math.round(canvas.clientHeight * ratio));
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.clearColor(0.033, 0.057, 0.067, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.DEPTH_TEST);
      const pose = controls.map(input => Number(input.value) / 100);
      controls.forEach((input, i) => document.getElementById(input.id + '-value').textContent = pose[i].toFixed(2));
      const angle = pose[0] * (1 - pose[2]) * 0.22, c = Math.cos(angle), s = Math.sin(angle);
      const jaw = [1,0,0,0, 0,c,s,0, 0,-s,c,0, 0,pivot*(1-c),-pivot*s,1];
      gl.uniformMatrix4fv(bonesLocation, false, new Float32Array([...identity, ...jaw]));
      gl.uniform3fv(poseLocation, pose); gl.uniform2f(orbitLocation, yaw, pitch);
      gl.uniform1f(aspectLocation, canvas.width / canvas.height);
      gl.drawElements(gl.TRIANGLES, indices.count, indices.componentType, 0);
      const error = gl.getError(); if (error !== gl.NO_ERROR) throw new Error('WebGL draw error ' + error);
      canvas.dataset.pose = pose.join(',');
    }
    controls.forEach(input => input.addEventListener('input', draw));
    document.querySelectorAll('[data-pose]').forEach(button => button.addEventListener('click', () => {
      button.dataset.pose.split(',').forEach((v, i) => controls[i].value = Number(v) * 100); draw();
    }));
    canvas.addEventListener('pointerdown', event => {
      dragging = true; lastX = event.clientX; lastY = event.clientY; canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove', event => {
      if (!dragging) return;
      yaw += (event.clientX - lastX) * 0.008;
      pitch = Math.max(-0.7, Math.min(0.7, pitch + (event.clientY - lastY) * 0.008));
      lastX = event.clientX; lastY = event.clientY; draw();
    });
    canvas.addEventListener('pointerup', () => dragging = false);
    canvas.addEventListener('pointercancel', () => dragging = false);
    new ResizeObserver(draw).observe(canvas);
    draw(); canvas.dataset.ready = 'true';
    document.getElementById('rig-fallback').hidden = true; canvas.hidden = false;
    status.textContent = 'Rig loaded · drag to rotate';
  } catch (failure) {
    status.textContent = failure.message; status.dataset.error = 'true';
    console.error(failure);
  }
  const media = [...document.querySelectorAll('audio, video')];
  media.forEach(player => player.addEventListener('play', () => media.forEach(other => { if (other !== player) other.pause(); })));
})();
