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

document.addEventListener('DOMContentLoaded', () => {
	const dropdown = document.getElementById('custom-language-dropdown');
	if (!dropdown) return;
	const toggle = dropdown.querySelector('.dropdown-toggle');
	const menu = dropdown.querySelector('.dropdown-menu');
	const selected = dropdown.querySelector('#dropdown-selected');
	let currentValue = '';

	toggle.addEventListener('click', (e) => {
		e.stopPropagation();
		dropdown.classList.toggle('open');
	});

	menu.querySelectorAll('li').forEach((item) => {
		item.addEventListener('click', (e) => {
			e.stopPropagation();
			menu.querySelectorAll('li').forEach(li => li.classList.remove('selected'));
			item.classList.add('selected');
			selected.textContent = item.textContent;
			currentValue = item.getAttribute('data-value');
			dropdown.classList.remove('open');
			// If you need to trigger a change event:
			const event = new CustomEvent('languageChange', { detail: { value: currentValue } });
			dropdown.dispatchEvent(event);
		});
	});

	document.addEventListener('click', () => {
		dropdown.classList.remove('open');
	});
});

