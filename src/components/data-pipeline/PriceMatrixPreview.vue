<template>
  <div class="card">
    <div class="controls">
      <label>
        Mã cổ phiếu (cách nhau bởi dấu phẩy):
        <input v-model="symbolsInput" placeholder="AAPL,MSFT,NVDA,AMZN,GOOGL" />
      </label>

      <label>
        Số dòng preview (10–20):
        <input type="number" v-model.number="previewRows" min="10" max="20" />
      </label>

      <button @click="loadData" :disabled="loading">
        {{ loading ? 'Đang tải...' : 'Tải dữ liệu' }}
      </button>
    </div>

    <p v-if="error" class="error">
      Lỗi khi gọi API: {{ error }}
    </p>

    <table v-if="rows.length" class="price-table">
      <thead>
        <tr>
          <th>Date</th>
          <th v-for="sym in symbols" :key="sym">{{ sym }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in rows" :key="i">
          <td>{{ row.date }}</td>
          <td v-for="sym in symbols" :key="sym">{{ row[sym] ?? '—' }}</td>
        </tr>
      </tbody>
    </table>

    <p v-if="!loading && !error && !rows.length" class="hint">
      Bấm "Tải dữ liệu" để xem preview.
    </p>

    <!-- Fallback: nếu không đoán được cấu trúc JSON trả về, hiện JSON thô -->
    <details v-if="rawFallback" class="raw-fallback" open>
      <summary>
        Không tự nhận diện được cấu trúc bảng — đây là JSON thô trả về từ API.
        Mở file PriceMatrixPreview.vue, sửa hàm normalizeResponse() cho khớp cấu trúc này.
      </summary>
      <pre>{{ rawFallback }}</pre>
    </details>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const symbolsInput = ref('AAPL,MSFT,NVDA,AMZN,GOOGL')
const previewRows = ref(15)
const loading = ref(false)
const error = ref('')
const rows = ref([])
const symbols = ref([])
const rawFallback = ref('')

// Cố gắng nhận diện vài kiểu JSON phổ biến mà backend FastAPI/pandas hay trả về
// và chuyển tất cả về cùng 1 dạng: [{ date, AAPL, MSFT, ... }, ...]
function normalizeResponse(json, requestedSymbols) {
  // Kiểu 1: mảng record sẵn có, mỗi phần tử là 1 dòng
  // [{ "date": "2025-09-01", "AAPL": 180, "MSFT": 420 }, ...]
  if (Array.isArray(json) && json.length && typeof json[0] === 'object') {
    const syms = Object.keys(json[0]).filter((k) => k.toLowerCase() !== 'date')
    return { rows: json, symbols: syms }
  }

  // Kiểu 2: dạng cột (columnar)
  // { "dates": [...], "AAPL": [...], "MSFT": [...] }
  const dateKey = Object.keys(json || {}).find((k) =>
    ['date', 'dates', 'index'].includes(k.toLowerCase())
  )
  if (dateKey && Array.isArray(json[dateKey])) {
    const dates = json[dateKey]
    const syms = Object.keys(json).filter((k) => k !== dateKey)
    const out = dates.map((d, i) => {
      const row = { date: d }
      syms.forEach((s) => (row[s] = json[s][i]))
      return row
    })
    return { rows: out, symbols: syms }
  }

  // Kiểu 3: pandas "split" format
  // { "columns": [...], "index": [...], "data": [[...], ...] }
  if (json && Array.isArray(json.columns) && Array.isArray(json.data)) {
    const dateIdx = json.columns.findIndex((c) =>
      String(c).toLowerCase().includes('date')
    )
    const syms = json.columns.filter((_, i) => i !== dateIdx)
    const out = json.data.map((rowArr, i) => {
      const row = { date: dateIdx >= 0 ? rowArr[dateIdx] : json.index?.[i] }
      let s = 0
      json.columns.forEach((c, ci) => {
        if (ci !== dateIdx) row[c] = rowArr[ci]
        s++
      })
      return row
    })
    return { rows: out, symbols: syms }
  }

  // Kiểu 4: dữ liệu nằm trong field "data" hoặc "result"
  if (json && (json.data || json.result)) {
    return normalizeResponse(json.data ?? json.result, requestedSymbols)
  }

  return null
}

async function loadData() {
  loading.value = true
  error.value = ''
  rawFallback.value = ''
  rows.value = []

  const symbolList = symbolsInput.value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)

  const params = new URLSearchParams()
  symbolList.forEach((s) => params.append('symbols', s))
  params.append('days', 252)

  try {
    // "/api/..." sẽ được Vite proxy sang http://127.0.0.1:8000 (xem vite.config.js)
    const res = await fetch(
      `/api/v1/data-pipeline/cleaned-price-matrix?${params.toString()}`
    )
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const json = await res.json()

    const normalized = normalizeResponse(json, symbolList)
    if (normalized) {
      symbols.value = normalized.symbols
      // Chỉ preview N dòng đầu theo yêu cầu đề bài (10–20 dòng)
      rows.value = normalized.rows.slice(0, previewRows.value)
    } else {
      rawFallback.value = JSON.stringify(json, null, 2)
    }
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: end;
  margin-bottom: 16px;
}
.controls label {
  display: flex;
  flex-direction: column;
  font-size: 13px;
  gap: 4px;
}
.controls input {
  padding: 6px 8px;
  border: 1px solid #d7dae0;
  border-radius: 6px;
  min-width: 220px;
}
button {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  height: 34px;
}
button:disabled {
  opacity: 0.6;
  cursor: default;
}
.price-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.price-table th,
.price-table td {
  border: 1px solid #e5e7eb;
  padding: 8px 10px;
  text-align: right;
}
.price-table th:first-child,
.price-table td:first-child {
  text-align: left;
}
.price-table thead {
  background: #f3f4f6;
}
.error {
  color: #b91c1c;
}
.hint {
  color: #6b7280;
}
.raw-fallback {
  margin-top: 16px;
}
.raw-fallback pre {
  background: #111827;
  color: #d1d5db;
  padding: 12px;
  border-radius: 6px;
  overflow: auto;
  max-height: 400px;
}
</style>
