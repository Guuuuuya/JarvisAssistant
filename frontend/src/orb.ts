import * as THREE from "three";

export class Orb {
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.1, 100);
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  mesh: THREE.Mesh;
  basePositions: Float32Array;
  analyser: AnalyserNode | null = null;

  constructor() {
    this.renderer.setSize(innerWidth, innerHeight);
    document.body.appendChild(this.renderer.domElement);
    this.camera.position.z = 3;

    const geo = new THREE.IcosahedronGeometry(1, 24);
    this.basePositions = geo.attributes.position.array.slice() as Float32Array;
    const mat = new THREE.MeshStandardMaterial({
      color: 0x2266ff,
      emissive: 0x1133aa,
      wireframe: true,
    });
    this.mesh = new THREE.Mesh(geo, mat);
    this.scene.add(this.mesh);
    this.scene.add(new THREE.AmbientLight(0xffffff, 1.2));

    addEventListener("resize", () => {
      this.camera.aspect = innerWidth / innerHeight;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(innerWidth, innerHeight);
    });

    this.animate();
  }

  setSource(node: AudioNode, ctx: AudioContext) {
    this.analyser = ctx.createAnalyser();
    this.analyser.fftSize = 256;
    node.connect(this.analyser);
  }

  animate = () => {
    requestAnimationFrame(this.animate);
    const pos = this.mesh.geometry.attributes.position;
    let amp = 0;
    if (this.analyser) {
      const data = new Uint8Array(this.analyser.frequencyBinCount);
      this.analyser.getByteFrequencyData(data);
      amp = data.reduce((a, b) => a + b, 0) / data.length / 255;
    }
    for (let i = 0; i < pos.count; i++) {
      const ix = i * 3;
      const x = this.basePositions[ix], y = this.basePositions[ix + 1], z = this.basePositions[ix + 2];
      const wobble = 1 + amp * 0.6 * Math.sin(Date.now() / 200 + i);
      pos.setXYZ(i, x * wobble, y * wobble, z * wobble);
    }
    pos.needsUpdate = true;
    this.mesh.rotation.y += 0.004 + amp * 0.05;
    this.renderer.render(this.scene, this.camera);
  };
}
