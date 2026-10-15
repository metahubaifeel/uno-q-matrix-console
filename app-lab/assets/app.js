/*
 * UNO Q 点阵控制台 - 前端
 *
 * 点格子 → 组成 104 字符的字符串 → 发给板子 → 点阵亮
 */

const COLS = 13;
const ROWS = 8;
const TOTAL = COLS * ROWS;   // 104

const gridEl = document.getElementById('grid');
const statusEl = document.getElementById('status');

// 当前画面：104 个 0/1
let pixels = new Array(TOTAL).fill(0);

let socket = null;
let isDrawing = false;
let drawValue = 1;           // 拖动时是画上还是擦掉
let lastSent = '';

/* ---------- 建立点阵格子 ---------- */
const cells = [];
for (let i = 0; i < TOTAL; i++) {
  const cell = document.createElement('div');
  cell.className = 'cell';
  cell.dataset.index = i;
  gridEl.appendChild(cell);
  cells.push(cell);
}

/* ---------- 画面 → 字符串 ---------- */
function toPayload() {
  return pixels.join('');
}

/* ---------- 重绘 ---------- */
function render() {
  for (let i = 0; i < TOTAL; i++) {
    cells[i].classList.toggle('on', pixels[i] === 1);
  }
}

/* ---------- 发给板子 ---------- */
function push() {
  const payload = toPayload();
  if (payload === lastSent) return;   // 没变化就不发
  lastSent = payload;

  if (socket && socket.connected) {
    socket.emit('set_pixels', { pixels: payload });
  }
}

/* ---------- 点 / 拖 ---------- */
function setCell(i, value) {
  if (pixels[i] === value) return;
  pixels[i] = value;
  cells[i].classList.toggle('on', value === 1);
}

gridEl.addEventListener('pointerdown', (e) => {
  const cell = e.target.closest('.cell');
  if (!cell) return;

  const i = Number(cell.dataset.index);
  // 点亮的格子，拖动时是擦除；未亮的，拖动时是画上
  drawValue = pixels[i] === 1 ? 0 : 1;
  setCell(i, drawValue);
  push();

  isDrawing = true;
  gridEl.setPointerCapture(e.pointerId);
});

gridEl.addEventListener('pointermove', (e) => {
  if (!isDrawing) return;
  const el = document.elementFromPoint(e.clientX, e.clientY);
  if (!el || !el.classList.contains('cell')) return;
  setCell(Number(el.dataset.index), drawValue);
  push();
});

function endDraw() { isDrawing = false; }
gridEl.addEventListener('pointerup', endDraw);
gridEl.addEventListener('pointercancel', endDraw);

/* ---------- 工具按钮 ---------- */
document.getElementById('btn-clear').onclick = () => {
  pixels.fill(0); render(); push();
};
document.getElementById('btn-fill').onclick = () => {
  pixels.fill(1); render(); push();
};
document.getElementById('btn-invert').onclick = () => {
  pixels = pixels.map(v => v ? 0 : 1); render(); push();
};

/* ---------- 预设图案 ---------- */
const PRESETS = {
  heart: [
    "0000000000000",
    "0011000011000",
    "0111100111100",
    "1111111111110",
    "1111111111110",
    "0111111111100",
    "0011111111000",
    "0001111110000",
  ],
  smile: [
    "0000000000000",
    "0011000011000",
    "0011000011000",
    "0000000000000",
    "0100000000010",
    "0010000000100",
    "0001111110000",
    "0000000000000",
  ],
  star: [
    "0000001000000",
    "0000011100000",
    "1111111111111",
    "0111111111110",
    "0011111111100",
    "0111000001110",
    "1100000000011",
    "0000000000000",
  ],
  flag: [
    "0000000000000",
    "0111000011000",
    "1111100011000",
    "0111000000000",
    "0000001100110",
    "0000001100110",
    "0000000000000",
    "0000000000000",
  ],
};

document.querySelectorAll('.preset').forEach(btn => {
  btn.onclick = () => {
    const rows = PRESETS[btn.dataset.preset];
    if (!rows) return;
    pixels = rows.join('').split('').map(Number);
    render();
    push();
  };
});

/* ---------- Socket.IO ---------- */
function connect() {
  socket = io(`http://${window.location.host}`);

  socket.on('connect', () => {
    statusEl.textContent = '已连接';
    statusEl.className = 'status online';
    lastSent = '';
    socket.emit('get_state', {});   // 拉取板子当前画面
  });

  socket.on('disconnect', () => {
    statusEl.textContent = '连接断开';
    statusEl.className = 'status offline';
  });

  socket.on('get_state_response', (data) => {
    if (!data || typeof data.pixels !== 'string') return;
    if (data.pixels.length !== TOTAL) return;
    pixels = data.pixels.split('').map(Number);
    render();
    lastSent = data.pixels;
  });
}

connect();
render();
