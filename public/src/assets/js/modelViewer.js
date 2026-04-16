import { Scene, PerspectiveCamera, WebGLRenderer, AmbientLight, DirectionalLight, TextureLoader, RepeatWrapping, Box3, Vector3, Group, Cache } from 'https://cdn.jsdelivr.net/npm/three@0.182.0/+esm';
import { GLTFLoader } from 'https://cdn.jsdelivr.net/npm/three@0.182.0/examples/jsm/loaders/GLTFLoader.js/+esm';
import { MeshoptDecoder } from 'https://cdn.jsdelivr.net/npm/three@0.182.0/examples/jsm/libs/meshopt_decoder.module.js/+esm';
import * as SkeletonUtils from 'https://cdn.jsdelivr.net/npm/three@0.182.0/examples/jsm/utils/SkeletonUtils.js/+esm';

Cache.enabled = true;

const modelCache = new Map();

async function getModelInstance(modelPath) {
	if (!modelCache.has(modelPath)) {
		const promise = new Promise((resolve, reject) => {
			const loader = new GLTFLoader();
			loader.setMeshoptDecoder(MeshoptDecoder);
			loader.load(modelPath, (gltf) => resolve(gltf.scene), undefined, reject);
		});
		modelCache.set(modelPath, promise);
	}

	const baseScene = await modelCache.get(modelPath);
	const clonedScene = SkeletonUtils.clone(baseScene);
  
	clonedScene.traverse((child) => {
		if (child.isMesh && child.material) {
			child.material = child.material.clone();
		}
	});

	return clonedScene;
}


export function loadModel(container, { modelPath, enableResize = false, onError, scale = 4 } = {}) {
	if (!modelPath) throw new Error('modelPath is required');

	const scene = new Scene();
	const camera = new PerspectiveCamera(55, container.clientWidth / container.clientHeight, 0.1, 100);
	camera.position.set(0, 0, 6);

	const renderer = new WebGLRenderer({ alpha: true, antialias: true });
	renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
	renderer.domElement.style.display = 'block';
	renderer.domElement.style.width = '100%';
	renderer.domElement.style.height = '100%';
	container.appendChild(renderer.domElement);

	let lastWidth = 0;
	let lastHeight = 0;
	let resizeTimeout = null;

	const doResize = () => {
		let width = container.clientWidth;
		let height = container.clientHeight;
		if (!width || !height) {
			const rect = container.getBoundingClientRect();
			width = Math.floor(rect.width);
			height = Math.floor(rect.height);
		}
		if (width === lastWidth && height === lastHeight) return;
		lastWidth = width;
		lastHeight = height;
		renderer.setSize(width, height, false);
		camera.aspect = width / height;
		camera.updateProjectionMatrix();
	};

	const resize = () => {
		if (resizeTimeout) clearTimeout(resizeTimeout);
		resizeTimeout = setTimeout(doResize, 150);
	};

	doResize();
	window.addEventListener('resize', resize);

	if (enableResize) {
		if (typeof ResizeObserver !== 'undefined' && !navigator.userAgent.match(/Mobile|Android|iPhone/i)) {
			const observer = new ResizeObserver(resize);
			observer.observe(container);
		}
	}

	scene.add(new AmbientLight(0xffffff, 1.2));
	const light = new DirectionalLight(0xffffff, 1.0);
	light.position.set(2, 3, 4);
	scene.add(light);

	let model = null;
	let pivot = null;
	let rotationY = 0;
	let isDragging = false;
	let didDrag = false;
	let lastX = 0;
	let dragStartX = 0;
	let lastDragTime = 0;
	const autoRotateDelayMs = 900;
	const autoRotateSpeed = 0.003;
	let isCancelled = false;

	getModelInstance(modelPath).then((clonedModel) => {
		if (isCancelled) return;
		model = clonedModel;
		model.scale.setScalar(scale);
		const box = new Box3().setFromObject(model);
		const center = new Vector3();
		box.getCenter(center);
		model.position.sub(center);

		pivot = new Group();
		pivot.add(model);
		scene.add(pivot);
	}).catch((error) => {
		if (onError && !isCancelled) onError(error);
	});

	const domElement = renderer.domElement;
	domElement.style.cursor = 'grab';
	const now = () => performance.now();

	domElement.addEventListener('pointerdown', (event) => {
		isDragging = true;
		didDrag = false;
		lastX = event.clientX;
		dragStartX = event.clientX;
		lastDragTime = now();
		domElement.setPointerCapture(event.pointerId);
		domElement.style.cursor = 'grabbing';
	});

	domElement.addEventListener('pointermove', (event) => {
		if (!isDragging || !model) return;
		const deltaX = event.clientX - lastX;
		lastX = event.clientX;
		rotationY += deltaX * 0.01;
		if (Math.abs(event.clientX - dragStartX) > 4) {
			didDrag = true;
		}
		lastDragTime = now();
	});

	domElement.addEventListener('pointerup', (event) => {
		isDragging = false;
		lastDragTime = now();
		domElement.releasePointerCapture(event.pointerId);
		domElement.style.cursor = 'grab';
		if (didDrag) {
			container.dataset.dragged = 'true';
		}
	});

	domElement.addEventListener('pointerleave', () => {
		isDragging = false;
		lastDragTime = now();
		domElement.style.cursor = 'grab';
	});

	let animating = true;
	function animate() {
		if (!animating) return;
		requestAnimationFrame(animate);
		if (pivot) {
			if (!isDragging && now() - lastDragTime > autoRotateDelayMs) {
				rotationY += autoRotateSpeed;
			}
			pivot.rotation.y = rotationY;
		}
		renderer.render(scene, camera);
	}
	animate();
	return () => { 
		animating = false; 
		isCancelled = true;
		window.removeEventListener('resize', resize);
		if (pivot && model) {
			model.traverse((child) => {
				if (child.isMesh) {
					// Do NOT dispose of geometry if we share it via SkeletonUtils.clone
					if (child.material) {
						if (child.material.map) child.material.map.dispose();
						child.material.dispose();
					}
				}
			});
			scene.remove(pivot);
		}
		renderer.dispose();
		renderer.forceContextLoss();
	};
}
