const BASE = '/api/cmsd/v1';

export const api = {
  async getSummary() {
    const res = await fetch(`${BASE}/digital-twin/summary`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getResources() {
    const res = await fetch(`${BASE}/digital-twin/resources`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getOrders() {
    const res = await fetch(`${BASE}/digital-twin/orders`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getLayout() {
    const res = await fetch(`${BASE}/digital-twin/layout`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getChanges(limit = 50) {
    const res = await fetch(`${BASE}/changes?limit=${limit}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
};