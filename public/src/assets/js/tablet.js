import { loadModel } from "./modelViewer.js";

const modelSlots = [
	document.querySelector('.model-slot-1'),
	document.querySelector('.model-slot-2'),
	document.querySelector('.model-slot-3')
];

const models = [
	{ modelPath: "assets/models/the_megaphone.glb", scale: 0.01, texturePath: "assets/imgs/blank.png" },
	{ modelPath: "assets/models/document_board.glb", scale: 12, texturePath: "assets/imgs/blank.png" },
	{ modelPath: "assets/models/crossmark.glb", scale: 4, texturePath: "assets/imgs/blank.png" } 
];

modelSlots.forEach((slot, i) => {
	if (slot && models[i]) {
		loadModel(slot, models[i]);
	}
});