import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { VRM, VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";

// UI Status elements
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

function updateStatus(text, active = false) {
  if (statusText) statusText.innerText = text;
  if (statusDot) {
    if (active) statusDot.classList.add("active");
    else statusDot.classList.remove("active");
  }
}

// Scene
const scene = new THREE.Scene();

// Background
const bgLoader = new THREE.TextureLoader();
bgLoader.load(
  "./bg.jpg",
  (texture) => {
    const geometry = new THREE.PlaneGeometry(10, 6);
    const material = new THREE.MeshBasicMaterial({ map: texture });
    material.map.minFilter = THREE.LinearFilter;
    material.map.magFilter = THREE.LinearFilter;

    const bgMesh = new THREE.Mesh(geometry, material);
    bgMesh.position.set(0, 1, -5);
    scene.add(bgMesh);
  },
  undefined,
  (err) => {
    console.warn("Background image bg.jpg not found, using default background.");
  }
);

// Camera
const camera = new THREE.PerspectiveCamera(
  30,
  window.innerWidth / window.innerHeight,
  0.01,
  1000
);
camera.position.set(0, 1.3, 2.5);
camera.lookAt(0, 1.1, 0);

// Renderer
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.body.appendChild(renderer.domElement);

// Lighting
scene.add(new THREE.AmbientLight(0xffffff, 1.0));
const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
dirLight.position.set(1, 2, 1);
scene.add(dirLight);

// Audio / Lip sync state
let isTalking = false;
let talkTimer = 0;
let lastSize = 0;

async function detectTalking() {
  try {
    const res = await fetch("./rem_output.wav?cache=" + Date.now(), { method: "HEAD" });
    if (!res.ok) return;

    const contentLength = res.headers.get("Content-Length");
    if (contentLength) {
      const size = parseInt(contentLength, 10);
      if (size > 2000 && size !== lastSize) {
        lastSize = size;
        isTalking = true;
        talkTimer = 0;
        updateStatus("Rem Speaking...", true);
      }
    }
  } catch (e) {
    // Ignore fetch errors during idle
  }
}

setInterval(detectTalking, 800);

// VRM Loader
const loader = new GLTFLoader();
loader.register((parser) => new VRMLoaderPlugin(parser));

let currentVrm = null;
let baseVrmY = 0;

updateStatus("Loading 3D Waifu Avatar...", false);

loader.load(
  "./model.vrm",
  (gltf) => {
    VRMUtils.removeUnnecessaryVertices(gltf.scene);
    VRMUtils.removeUnnecessaryJoints(gltf.scene);

    currentVrm = gltf.userData.vrm;
    scene.add(currentVrm.scene);

    currentVrm.scene.rotation.y = Math.PI;

    const bbox = new THREE.Box3().setFromObject(currentVrm.scene);
    const minY = bbox.min.y;
    currentVrm.scene.position.y -= minY;
    baseVrmY = currentVrm.scene.position.y;

    // Adjust arms to natural pose
    const humanoid = currentVrm.humanoid;
    if (humanoid) {
      const lArm = humanoid.getNormalizedBoneNode("leftUpperArm");
      const rArm = humanoid.getNormalizedBoneNode("rightUpperArm");
      if (lArm) lArm.rotation.z = 1.0;
      if (rArm) rArm.rotation.z = -1.0;

      const lLower = humanoid.getNormalizedBoneNode("leftLowerArm");
      const rLower = humanoid.getNormalizedBoneNode("rightLowerArm");
      if (lLower) lLower.rotation.z = 0.5;
      if (rLower) rLower.rotation.z = -0.5;
    }

    currentVrm.scene.traverse((obj) => (obj.frustumCulled = false));

    console.log("VRM Model Loaded Successfully!");
    updateStatus("Rem Online", true);
  },
  (progress) => {
    if (progress.total > 0) {
      const pct = Math.round((progress.loaded / progress.total) * 100);
      updateStatus(`Loading Avatar (${pct}%)...`, false);
    }
  },
  (error) => {
    console.error("Error loading VRM model:", error);
    updateStatus("Failed to load model.vrm", false);
  }
);

// Blinking logic
let blinkTimer = 0;
let isBlinking = false;
let blinkInterval = 2.8 + Math.random() * 2.4;
const blinkDuration = 0.12;

function setBlink(v) {
  if (!currentVrm || !currentVrm.expressionManager) return;
  try {
    currentVrm.expressionManager.setValue("blink", v);
  } catch (e) {}
}

// Lip sync mouth expression logic
function setMouth(v) {
  if (!currentVrm || !currentVrm.expressionManager) return;

  const exp = currentVrm.expressionManager;
  try {
    // Try standard VRM 1.0 / 0.x expression keys
    exp.setValue("aa", v);
    exp.setValue("oh", v * 0.5);
  } catch (e) {
    // Fallback: search expression map dynamically
    const map = exp._expressionMap;
    if (map) {
      Object.keys(map).forEach((key) => {
        if (
          key.toLowerCase().includes("mouth") ||
          key.toLowerCase().includes("aa") ||
          key.toLowerCase().includes("oh") ||
          key.toLowerCase().includes("ih")
        ) {
          try {
            exp.setValue(key, v);
          } catch (err) {}
        }
      });
    }
  }

  exp.update();
}

// Animation loop
const clock = new THREE.Clock();
let idleTimer = 0;
let idleState = "normal";

function animate() {
  requestAnimationFrame(animate);

  const delta = clock.getDelta();

  if (currentVrm) {
    const t = clock.elapsedTime;

    // Subtle breathing animation
    currentVrm.scene.position.y = baseVrmY + Math.sin(t * 1.4) * 0.0008;

    // Idle state transitions
    idleTimer += delta;
    if (idleTimer > 6) {
      idleTimer = 0;
      const states = ["normal", "look", "shy"];
      idleState = states[Math.floor(Math.random() * states.length)];
    }

    // Head rotation
    const head = currentVrm.humanoid?.getNormalizedBoneNode("head");
    if (head) {
      if (idleState === "normal") {
        head.rotation.x = Math.sin(t * 0.8) * 0.03;
        head.rotation.y = Math.sin(t * 0.5) * 0.05;
      } else if (idleState === "look") {
        head.rotation.y = Math.sin(t * 0.4) * 0.25;
      } else if (idleState === "shy") {
        head.rotation.x = 0.15;
        head.rotation.y = -0.4;
      }
    }

    // Body idle sway
    currentVrm.scene.rotation.y = Math.PI + Math.sin(t * 0.25) * 0.15;

    if (currentVrm.humanoid) currentVrm.humanoid.update();
    currentVrm.update(delta);

    // Blinking updates
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
        blinkInterval = 2.8 + Math.random() * 2.4;
      }
    }

    // Lip sync updates
    if (isTalking) {
      talkTimer += delta;

      let mouth =
        Math.abs(Math.sin(t * 10)) * 0.5 +
        Math.abs(Math.sin(t * 6)) * 0.4 +
        Math.random() * 0.2;

      mouth = Math.min(mouth * 1.2, 1.0);
      setMouth(mouth);

      if (talkTimer > 4.5) {
        isTalking = false;
        updateStatus("Rem Online", true);
      }
    } else {
      setMouth(0);
    }
  }

  renderer.render(scene, camera);
}

animate();

// Responsive window resize
window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
