import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { VRM, VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";

// Scene
const scene = new THREE.Scene();

// Background
const bgLoader = new THREE.TextureLoader();
bgLoader.load("./bg.jpg", (texture) => {
  const geometry = new THREE.PlaneGeometry(10, 6);
  const material = new THREE.MeshBasicMaterial({ map: texture });

  material.map.minFilter = THREE.LinearFilter;
  material.map.magFilter = THREE.LinearFilter;

  const bgMesh = new THREE.Mesh(geometry, material);
  bgMesh.position.set(0, 1, -5);
  scene.add(bgMesh);
});

// Camera
const camera = new THREE.PerspectiveCamera(30, window.innerWidth / window.innerHeight, 0.01, 1000);
camera.position.set(0, 1, 3);
camera.lookAt(0, 0.8, 0);

// Renderer
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// Lighting
scene.add(new THREE.AmbientLight(0xffffff, 0.8));
const light = new THREE.DirectionalLight(0xffffff, 1);
light.position.set(1, 1, 1);
scene.add(light);

// Audio detection
let isTalking = false;
let talkTimer = 0;
let lastSize = 0;

async function detectTalking() {
  try {
    const res = await fetch("./rem_output.wav?cache=" + Date.now());
    const blob = await res.blob();

    if (blob.size > 2000 && blob.size !== lastSize) {
      lastSize = blob.size;
      isTalking = true;
      talkTimer = 0;
    }
  } catch {}
}

setInterval(detectTalking, 1000);

// Loader
const loader = new GLTFLoader();
loader.register((parser) => new VRMLoaderPlugin(parser));

let currentVrm = null;
let baseVrmY = 0;

loader.load("./model.vrm", (gltf) => {
  VRMUtils.removeUnnecessaryVertices(gltf.scene);
  VRMUtils.removeUnnecessaryJoints(gltf.scene);

  currentVrm = gltf.userData.vrm;
  scene.add(currentVrm.scene);

  currentVrm.scene.rotation.y = Math.PI;

  const bbox = new THREE.Box3().setFromObject(currentVrm.scene);
  const minY = bbox.min.y;
  currentVrm.scene.position.y -= minY;
  baseVrmY = currentVrm.scene.position.y;

  const humanoid = currentVrm.humanoid;

  const lArm = humanoid.getNormalizedBoneNode("leftUpperArm");
  const rArm = humanoid.getNormalizedBoneNode("rightUpperArm");
  if (lArm) lArm.rotation.z = 1.0;
  if (rArm) rArm.rotation.z = -1.0;

  const lLower = humanoid.getNormalizedBoneNode("leftLowerArm");
  const rLower = humanoid.getNormalizedBoneNode("rightLowerArm");
  if (lLower) lLower.rotation.z = 0.5;
  if (rLower) rLower.rotation.z = -0.5;

  currentVrm.scene.traverse((obj) => (obj.frustumCulled = false));

  console.log("Mouth keys:", currentVrm.expressionManager?.mouthExpressionNames);
  console.log("Mouth keys FULL:", currentVrm.expressionManager.mouthExpressionNames);

  const map = currentVrm.expressionManager._expressionMap;
  console.log("Expression Map:", Object.keys(map));

});

// Blink
let blinkTimer = 0;
let isBlinking = false;
let blinkInterval = 2.8 + Math.random() * 2.4;
const blinkDuration = 0.12;

function setBlink(v) {
  if (!currentVrm || !currentVrm.expressionManager) return;
  try {
    currentVrm.expressionManager.setValue("blink", v);
  } catch {}
}

// ✅ FIXED MOUTH FUNCTION (OUTSIDE animate)
function setMouth(v) {
  if (!currentVrm || !currentVrm.expressionManager) return;

  const exp = currentVrm.expressionManager;

  const map = exp._expressionMap;

  if (!map) return;

  Object.keys(map).forEach((key) => {
    // only target mouth-related expressions
    if (key.toLowerCase().includes("mouth") || 
        key.toLowerCase().includes("aa") || 
        key.toLowerCase().includes("oh") || 
        key.toLowerCase().includes("ih")) {

      try {
        exp.setValue(key, v);
      } catch {}
    }
  });

  exp.update();
}


// Animation
let clock = new THREE.Clock();
let idleTimer = 0;
let idleState = "normal";

function animate() {
  requestAnimationFrame(animate);

  const delta = clock.getDelta();

  if (currentVrm) {
    const t = clock.elapsedTime;

    // breathing
    currentVrm.scene.position.y =
      baseVrmY + Math.sin(t * 1.4) * 0.0008;

    // idle state
    idleTimer += delta;
    if (idleTimer > 6) {
      idleTimer = 0;
      const states = ["normal", "look", "shy"];
      idleState = states[Math.floor(Math.random() * states.length)];
    }

    // head
    const head = currentVrm.humanoid.getNormalizedBoneNode("head");

    if (head) {
      if (idleState === "normal") {
        head.rotation.x = Math.sin(t * 0.8) * 0.03;
        head.rotation.y = Math.sin(t * 0.5) * 0.05;
      }
      if (idleState === "look") {
        head.rotation.y = Math.sin(t * 0.4) * 0.25;
      }
      if (idleState === "shy") {
        head.rotation.x = 0.15;
        head.rotation.y = -0.4;
      }
    }

    // body turn
    currentVrm.scene.rotation.y =
      Math.PI + Math.sin(t * 0.25) * 0.2;

    currentVrm.humanoid.update();
    currentVrm.update(delta);

    // blinking
    if (!isBlinking) {
      blinkTimer += delta;
      setBlink(0);
      if (blinkTimer > blinkInterval) {
        isBlinking = true;
        blinkTimer = 0;
      }
    } else {
      blinkTimer += delta;
      const v = Math.sin((blinkTimer / blinkDuration) * Math.PI);
      setBlink(v);
      if (blinkTimer > blinkDuration) {
        isBlinking = false;
        blinkTimer = 0;
      }
    }

    // 🗣️ LIP SYNC
    if (isTalking) {
      talkTimer += delta;

      let mouth =
        Math.abs(Math.sin(t * 9)) * 2 +
        Math.abs(Math.sin(t * 5)) * 3 +
        Math.random() * 3;

      mouth = Math.min(Math.pow(mouth, 0.7) * 2.8, 1);

      setMouth(mouth);

      if (talkTimer > 5) {
        isTalking = false;
      }
    } else {
      setMouth(0);
    }
  }

  renderer.render(scene, camera);
}

animate();

// Resize
window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
