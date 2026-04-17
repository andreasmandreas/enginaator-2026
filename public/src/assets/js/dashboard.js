const API = "http://localhost:3000";
const WS = "ws://localhost:3000";

let currentFilter = "all";

const socket = new WebSocket(WS);

socket.onopen = () => {
  console.log("WebSocket connected");
};

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "inventory_update") {
    renderInventory();
  }

  if (data.type === "request_update") {
    renderRequests();
    updateStats();
  }
};

socket.onerror = (err) => {
  console.error("WebSocket error:", err);
};

function escapeHtml(str) {
  return String(str).replace(/[&<>]/g, m =>
    m === '&' ? '&amp;' : m === '<' ? '&lt;' : '&gt;'
  );
}

function timeAgo(date) {
  const seconds = Math.floor((new Date() - new Date(date)) / 1000);
  if (seconds < 60) return "just now";
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins} min ago`;
  return `${Math.floor(mins / 60)}h ago`;
}

async function renderInventory() {
  const res = await fetch(`${API}/inventory`);
  const inventoryItems = await res.json();

  const container = document.getElementById('inventoryList');
  if (!container) return;

  container.innerHTML = inventoryItems.map(item => {
    let stockClass = '';
    if (item.available <= 0) stockClass = 'out';
    else if (item.available < item.threshold) stockClass = 'low';

    return `
      <div class="inv-row">
        <div class="inv-info">
          <h4>${escapeHtml(item.name)}</h4>
          <p>${item.category}</p>
        </div>
        <div class="inv-stats">
          <div class="stock-number ${stockClass}">
            ${item.available} available
          </div>
          <div style="font-size:10px;">
            ${item.reserved} reserved · total ${item.stock}
          </div>
          <button class="restock-btn" data-id="${item.id}">
            + Restock (+5)
          </button>
        </div>
      </div>
    `;
  }).join('');

  document.querySelectorAll('.restock-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;

      await fetch(`${API}/inventory/${id}/restock`, {
        method: "POST"
      });
    });
  });
}

async function renderRequests() {
  const res = await fetch(`${API}/requests`);
  let requests = await res.json();

  const container = document.getElementById('requestsContainer');
  if (!container) return;

  let filtered = requests.filter(r =>
    currentFilter === "all" ? true : r.status === currentFilter
  );

  filtered.sort((a,b) => new Date(b.createdAt) - new Date(a.createdAt));

  if (filtered.length === 0) {
    container.innerHTML = `<div style="padding:20px;"> No requests</div>`;
    return;
  }

  container.innerHTML = filtered.map(req => {
    const isNew = (new Date() - new Date(req.createdAt)) < 60000 && req.status === 'received';

    const itemsHtml = req.items.map(it =>
      `<span class="item-pill">${escapeHtml(it.name)} × ${it.quantity}</span>`
    ).join('');

    return `
      <div class="request-card">
        <div>
          Room ${escapeHtml(req.room)}
          ${isNew ? '<span class="new-tag">NEW</span>' : ''}
        </div>

        <div>${escapeHtml(req.category)}</div>
        <div>“${escapeHtml(req.text.replace(/SVARA/gi, 'Trivago'))}”</div>

        <div>${itemsHtml}</div>

        <div>
          <span>${req.status}</span>

          ${req.status === 'received' ? `
            <button data-action="progress" data-id="${req.id}">
              In Progress →
            </button>
            <button data-action="reject" data-id="${req.id}">
              Reject
            </button>
          ` : ''}

          ${req.status === 'in_progress' ? `
            <button data-action="deliver" data-id="${req.id}">
              Delivered
            </button>
            <button data-action="reject" data-id="${req.id}">
              Reject
            </button>
          ` : ''}
        </div>

        <div style="font-size:12px;">${timeAgo(req.createdAt)}</div>
      </div>
    `;
  }).join('');

  bindRequestActions();
}

function bindRequestActions() {
  document.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      const action = btn.dataset.action;

      let endpoint = "";

      if (action === "progress") endpoint = `/requests/${id}/progress`;
      if (action === "deliver") endpoint = `/requests/${id}/deliver`;
      if (action === "reject") endpoint = `/requests/${id}/reject`;

      await fetch(`${API}${endpoint}`, {
        method: "PATCH"
      });
    });
  });
}

async function addRandomDemoRequest() {
  const newRoom = Math.floor(Math.random() * 300) + 100;

  const newReq = {
    room: String(newRoom),
    text: "Hey Trivago, could I get a blanket and a bottle of water?",
    category: "Room Service",
    items: [
      { inventory_id: 6, name: "Blanket", quantity: 1 },
      { inventory_id: 3, name: "Still Water", quantity: 1 }
    ]
  };

  const res = await fetch(`${API}/requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(newReq)
  });

  if (!res.ok) {
    alert("Not enough stock");
  }
}

async function updateStats() {
  const res = await fetch(`${API}/stats`);
  const stats = await res.json();

  document.getElementById('statActive').innerText = stats.active;
  document.getElementById('statDelivered').innerText = stats.delivered;
  document.getElementById('lowStockCount').innerText = stats.lowStock;
}

document.querySelectorAll('.filter-pill').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.getAttribute('data-filter');
    renderRequests();
  });
});

document.getElementById('mockRestockBtn')?.addEventListener('click', async () => {
  await fetch(`${API}/inventory/2/restock`, { method: "POST" });
});

async function init() {
  await renderInventory();
  await renderRequests();
  await updateStats();
}

document.getElementById('monthlyReportBtn')?.addEventListener('click', () => {
  alert("Monthly report coming soon");
});

document.getElementById('stocktakingBtn')?.addEventListener('click', () => {
  alert("Stocktaking session started");
});

init();