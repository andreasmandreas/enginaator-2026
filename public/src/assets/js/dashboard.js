import { loadModel } from "./modelViewer";

const modelGrid = document.getElementById("modelGrid")

loadModel(modelGrid, { modelPath: "./models/stepan.glb", scale: 4 });