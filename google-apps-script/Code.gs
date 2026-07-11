/**
 * FinBot — Google Apps Script Web App
 * =====================================
 * This is the ONLY thing that ever touches the spreadsheet directly. The
 * Telegram bot (running on Railway) never sees a service account or an API
 * key — it just POSTs a small JSON body to this Web App's /exec URL, and
 * this script does the actual read/write against the sheet on its behalf.
 *
 * Deploy: Extensions -> Apps Script (from inside the spreadsheet) -> paste
 * this whole file over Code.gs -> Project Settings -> Script Properties ->
 * add SHARED_SECRET = <any random string> -> Deploy -> New deployment ->
 * type "Web app" -> Execute as "Me", Who has access "Anyone" -> Deploy ->
 * copy the /exec URL into GAS_WEB_APP_URL in the bot's .env (and the same
 * secret into GAS_SHARED_SECRET). Full walkthrough in the README.
 *
 * This script NEVER changes the spreadsheet's structure (no new tabs, no
 * new columns, no inserted rows outside what the template already reserves)
 * — it only reads and writes cells that already exist.
 */

// ============================================================================
// CONFIG — matches the template's exact tab names and column layout.
// ============================================================================

var SHEET_TX = 'Cashflow Harian';
var SHEET_BUDGET = 'Budget Planner';
var SHEET_GOALS = 'Goal Planning';

// 'Cashflow Harian' columns (1-indexed). Header row is 2, data starts row 3.
var TX_COL = {
  ID: 1, DATE: 2, TIME: 3, TYPE: 4, CATEGORY: 5, NEED_WANT_GOAL: 6,
  FIXED_VARIABLE: 7, AMOUNT: 8, ACCOUNT: 9, MERCHANT: 10, PAYMENT_METHOD: 11,
  NOTES: 12, TAGS: 13,
};
var TX_HEADER_ROW = 2;
var TX_DATA_START_ROW = 3;
var SCRIPT_TIMEZONE = 'Asia/Jakarta';

function parseDateOnly_(dateStr) {
  if (!dateStr) return null;
  return new Date(String(dateStr).trim() + 'T00:00:00+07:00');
}

function parseTimeOnly_(timeStr) {
  if (!timeStr) return null;
  var normalized = String(timeStr).trim();
  if (normalized.length === 5) normalized += ':00';
  return new Date('1970-01-01T' + normalized + '+07:00');
}

// 'Budget Planner' — fixed category rows the template ships with.
// { rowLabel: { row, section } }
var BUDGET_ROWS = {
  'Sewa/Cicilan Rumah': { row: 8, section: 'Needs' },
  'Makanan & Kebutuhan Dapur': { row: 9, section: 'Needs' },
  'Transportasi': { row: 10, section: 'Needs' },
  'Tagihan Utilitas': { row: 11, section: 'Needs' },
  'Asuransi': { row: 12, section: 'Needs' },
  'Kesehatan & Obat': { row: 13, section: 'Needs' },
  'Kebutuhan Lainnya': { row: 14, section: 'Needs' },
  'Hiburan & Streaming': { row: 18, section: 'Wants' },
  'Makan di Luar / Kafe': { row: 19, section: 'Wants' },
  'Belanja Fashion & Lifestyle': { row: 20, section: 'Wants' },
  'Hobi & Rekreasi': { row: 21, section: 'Wants' },
  'Keinginan Lainnya': { row: 22, section: 'Wants' },
  'Dana Darurat (target 3-6 bln)': { row: 26, section: 'Saving & Invest' },
  'Investasi Jangka Panjang': { row: 27, section: 'Saving & Invest' },
  'Tabungan Tujuan Khusus': { row: 28, section: 'Saving & Invest' },
};
var BUDGET_COL = { LABEL: 2, BUDGET: 3, ACTUAL: 4, DIFF: 5, PCT_INCOME: 6, STATUS: 7 };
var BUDGET_ALERT_THRESHOLDS = [0.8, 0.9, 1.0];

// Maps a Cashflow Harian Category -> its Budget Planner row label, so a
// saved Expense/Transfer can auto-increment that row's AKTUAL column.
var BUDGET_CATEGORY_MAP = {
  'Rent': 'Sewa/Cicilan Rumah',
  'Breakfast': 'Makanan & Kebutuhan Dapur', 'Lunch': 'Makanan & Kebutuhan Dapur',
  'Dinner': 'Makanan & Kebutuhan Dapur', 'Groceries': 'Makanan & Kebutuhan Dapur',
  'Transportation': 'Transportasi', 'Fuel': 'Transportasi', 'Parking': 'Transportasi', 'Toll': 'Transportasi',
  'Electricity': 'Tagihan Utilitas', 'Water': 'Tagihan Utilitas', 'Internet': 'Tagihan Utilitas', 'Mobile Phone': 'Tagihan Utilitas',
  'Insurance': 'Asuransi',
  'Healthcare': 'Kesehatan & Obat',
  'Tax': 'Kebutuhan Lainnya', 'Education': 'Kebutuhan Lainnya', 'Parents': 'Kebutuhan Lainnya',
  'Child': 'Kebutuhan Lainnya', 'Household': 'Kebutuhan Lainnya', 'Debt Payment': 'Kebutuhan Lainnya',
  'Entertainment': 'Hiburan & Streaming', 'Movie': 'Hiburan & Streaming', 'Netflix': 'Hiburan & Streaming',
  'Spotify': 'Hiburan & Streaming', 'YouTube Premium': 'Hiburan & Streaming', 'Gaming': 'Hiburan & Streaming',
  'Coffee': 'Makan di Luar / Kafe', 'Dining Out': 'Makan di Luar / Kafe',
  'Shopping': 'Belanja Fashion & Lifestyle', 'Fashion': 'Belanja Fashion & Lifestyle',
  'Gadget': 'Belanja Fashion & Lifestyle', 'Electronics': 'Belanja Fashion & Lifestyle',
  'Beauty': 'Belanja Fashion & Lifestyle', 'Skincare': 'Belanja Fashion & Lifestyle',
  'Hobby': 'Hobi & Rekreasi', 'Travel': 'Hobi & Rekreasi', 'Vacation': 'Hobi & Rekreasi',
  'Emergency Fund': 'Dana Darurat (target 3-6 bln)',
  'Investment': 'Investasi Jangka Panjang', 'Retirement': 'Investasi Jangka Panjang',
  'House': 'Tabungan Tujuan Khusus', 'Wedding': 'Tabungan Tujuan Khusus', 'Car': 'Tabungan Tujuan Khusus',
  'Education Fund': 'Tabungan Tujuan Khusus', 'Business Capital': 'Tabungan Tujuan Khusus',
  'Vacation Fund': 'Tabungan Tujuan Khusus',
};

// 'Goal Planning' — the template's 5 goal slots (3 pre-filled: Dana Darurat,
// Mobil, Menikah; 2 blank, usable once a matching row is added to Cashflow's
// TABUNGAN & INVESTASI section). Name (B) and Monthly Saving (F) are
// formulas linked back to 'Cashflow' — we only ever write Target (C) and
// Current (D) here.
var GOAL_ROWS = [4, 5, 6, 7, 8];
var GOAL_COL = { NAME: 2, TARGET: 3, CURRENT: 4, HORIZON: 5, MONTHLY_SAVING: 6, FUTURE_VALUE: 9, FEASIBILITY: 11 };

// ============================================================================
// ENTRY POINT
// ============================================================================

function doPost(e) {
  var response;
  try {
    var body = JSON.parse(e.postData.contents);
    var secret = PropertiesService.getScriptProperties().getProperty('SHARED_SECRET');
    if (!secret || body.secret !== secret) {
      return jsonOutput({ status: 'error', message: 'Unauthorized' });
    }

    var action = body.action;
    var payload = body.payload || {};
    var handler = ACTIONS[action];
    if (!handler) {
      return jsonOutput({ status: 'error', message: 'Unknown action: ' + action });
    }
    response = handler(payload);
    response.status = response.status || 'ok';
  } catch (err) {
    response = { status: 'error', message: String(err && err.message ? err.message : err) };
  }
  return jsonOutput(response);
}

function jsonOutput(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

// ============================================================================
// ACTION DISPATCH TABLE
// ============================================================================

var ACTIONS = {
  addTransaction: function (payload) { return addTransactionRow(payload); },
  addTransactions: function (payload) { return addTransactionRows(payload.transactions || []); },
  editTransaction: function (payload) { return editTransaction(payload.transactionId, payload.fields || {}); },
  deleteTransaction: function (payload) { return deleteTransaction(payload.transactionId); },
  getTransactions: function (payload) { return getTransactions(payload); },
  getBalance: function (payload) { return getBalance(payload.year, payload.month); },
  getBudgets: function () { return getBudgets(); },
  setBudgetAmount: function (payload) { return setBudgetAmount(payload.category, payload.amount); },
  getGoals: function () { return getGoals(); },
  setGoalTarget: function (payload) { return setGoalTarget(payload.name, payload.amount); },
  contributeGoal: function (payload) { return contributeGoal(payload.name, payload.amount); },
};

// ============================================================================
// TRANSACTIONS — 'Cashflow Harian'
// ============================================================================

function txSheet_() {
  return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_TX);
}

function nextTransactionId_(sheet) {
  var lastRow = sheet.getLastRow();
  var maxN = 0;
  if (lastRow >= TX_DATA_START_ROW) {
    var ids = sheet.getRange(TX_DATA_START_ROW, TX_COL.ID, lastRow - TX_DATA_START_ROW + 1, 1).getValues();
    for (var i = 0; i < ids.length; i++) {
      var id = String(ids[i][0] || '');
      var match = id.match(/^TRX(\d+)$/);
      if (match) {
        var n = parseInt(match[1], 10);
        if (n > maxN) maxN = n;
      }
    }
  }
  var next = maxN + 1;
  var padded = String(next);
  while (padded.length < 6) padded = '0' + padded;
  return 'TRX' + padded;
}

// The first data row to write into next. We anchor on column A (the TRX id)
// instead of sheet.appendRow()/getLastRow(): the template ships with
// formulas/content far down the sheet, and appendRow would land the new row
// at the very bottom (row 900+) instead of right under the last transaction.
function nextTxRow_(sheet) {
  var lastRow = sheet.getLastRow();
  if (lastRow < TX_DATA_START_ROW) return TX_DATA_START_ROW;
  var ids = sheet.getRange(TX_DATA_START_ROW, TX_COL.ID, lastRow - TX_DATA_START_ROW + 1, 1).getValues();
  var lastTrx = TX_DATA_START_ROW - 1;
  for (var i = 0; i < ids.length; i++) {
    if (/^TRX\d+$/.test(String(ids[i][0]).trim())) lastTrx = TX_DATA_START_ROW + i;
  }
  return lastTrx + 1;
}

function writeTxRow_(sheet, row, id, p) {
  sheet.getRange(row, 1, 1, TX_COL.TAGS).setValues([rowFromPayload_(id, p)]);
}

function rowFromPayload_(id, p) {
  var row = [];
  row[TX_COL.ID - 1] = id;
  row[TX_COL.DATE - 1] = p.date instanceof Date ? p.date : parseDateOnly_(p.date);
  row[TX_COL.TIME - 1] = p.time instanceof Date ? p.time : parseTimeOnly_(p.time);
  row[TX_COL.TYPE - 1] = p.type;
  row[TX_COL.CATEGORY - 1] = p.category;
  row[TX_COL.NEED_WANT_GOAL - 1] = p.needWantGoal || '-';
  row[TX_COL.FIXED_VARIABLE - 1] = p.fixedVariable || 'Variable';
  row[TX_COL.AMOUNT - 1] = p.amount;
  row[TX_COL.ACCOUNT - 1] = p.account || '';
  row[TX_COL.MERCHANT - 1] = p.merchant || '';
  row[TX_COL.PAYMENT_METHOD - 1] = p.paymentMethod || '';
  row[TX_COL.NOTES - 1] = p.notes || '';
  row[TX_COL.TAGS - 1] = p.tags || '';
  return row;
}

function addTransactionRow(payload) {
  var sheet = txSheet_();
  var id = nextTransactionId_(sheet);
  writeTxRow_(sheet, nextTxRow_(sheet), id, payload);
  SpreadsheetApp.flush();
  var alert = null;
  if (payload.type === 'Expense' || payload.type === 'Transfer') {
    alert = applyBudgetDelta_(payload.category, Number(payload.amount) || 0);
  }
  return { transactionId: id, budgetAlert: alert };
}

function addTransactionRows(transactions) {
  var sheet = txSheet_();
  var ids = [];
  var alerts = [];
  var row = nextTxRow_(sheet);
  for (var i = 0; i < transactions.length; i++) {
    var p = transactions[i];
    var id = nextTransactionId_(sheet); // recompute each time so a batch never collides
    writeTxRow_(sheet, row, id, p);
    SpreadsheetApp.flush(); // so nextTransactionId_ sees this row on the next loop
    row++;
    ids.push(id);
    if (p.type === 'Expense' || p.type === 'Transfer') {
      alerts.push(applyBudgetDelta_(p.category, Number(p.amount) || 0));
    } else {
      alerts.push(null);
    }
  }
  return { transactionIds: ids, budgetAlerts: alerts };
}

function findTxRow_(sheet, transactionId) {
  var lastRow = sheet.getLastRow();
  if (lastRow < TX_DATA_START_ROW) return -1;
  var ids = sheet.getRange(TX_DATA_START_ROW, TX_COL.ID, lastRow - TX_DATA_START_ROW + 1, 1).getValues();
  for (var i = 0; i < ids.length; i++) {
    if (String(ids[i][0]) === String(transactionId)) return TX_DATA_START_ROW + i;
  }
  return -1;
}

function rowToTxObject_(sheet, row) {
  var vals = sheet.getRange(row, 1, 1, TX_COL.TAGS).getValues()[0];
  return {
    transactionId: vals[TX_COL.ID - 1],
    date: formatDate_(vals[TX_COL.DATE - 1]),
    time: formatTime_(vals[TX_COL.TIME - 1]),
    type: vals[TX_COL.TYPE - 1],
    category: vals[TX_COL.CATEGORY - 1],
    needWantGoal: vals[TX_COL.NEED_WANT_GOAL - 1],
    fixedVariable: vals[TX_COL.FIXED_VARIABLE - 1],
    amount: vals[TX_COL.AMOUNT - 1],
    account: vals[TX_COL.ACCOUNT - 1],
    merchant: vals[TX_COL.MERCHANT - 1],
    paymentMethod: vals[TX_COL.PAYMENT_METHOD - 1],
    notes: vals[TX_COL.NOTES - 1],
    tags: vals[TX_COL.TAGS - 1],
  };
}

var EDITABLE_TX_FIELDS = {
  date: TX_COL.DATE, time: TX_COL.TIME, type: TX_COL.TYPE, category: TX_COL.CATEGORY,
  needWantGoal: TX_COL.NEED_WANT_GOAL, fixedVariable: TX_COL.FIXED_VARIABLE, amount: TX_COL.AMOUNT,
  account: TX_COL.ACCOUNT, merchant: TX_COL.MERCHANT, paymentMethod: TX_COL.PAYMENT_METHOD,
  notes: TX_COL.NOTES, tags: TX_COL.TAGS,
};

function editTransaction(transactionId, fields) {
  var sheet = txSheet_();
  var row = findTxRow_(sheet, transactionId);
  if (row === -1) return { found: false };

  var oldAmount = sheet.getRange(row, TX_COL.AMOUNT).getValue();
  var oldCategory = sheet.getRange(row, TX_COL.CATEGORY).getValue();
  var oldType = sheet.getRange(row, TX_COL.TYPE).getValue();

  for (var key in fields) {
    if (EDITABLE_TX_FIELDS.hasOwnProperty(key)) {
      sheet.getRange(row, EDITABLE_TX_FIELDS[key]).setValue(fields[key]);
    }
  }
  SpreadsheetApp.flush();

  // Reconcile Budget Planner AKTUAL if amount/category/type changed.
  if (oldType === 'Expense' || oldType === 'Transfer') {
    applyBudgetDelta_(oldCategory, -Number(oldAmount) || 0);
  }
  var newAmount = sheet.getRange(row, TX_COL.AMOUNT).getValue();
  var newCategory = sheet.getRange(row, TX_COL.CATEGORY).getValue();
  var newType = sheet.getRange(row, TX_COL.TYPE).getValue();
  if (newType === 'Expense' || newType === 'Transfer') {
    applyBudgetDelta_(newCategory, Number(newAmount) || 0);
  }

  return { found: true, transaction: rowToTxObject_(sheet, row) };
}

function deleteTransaction(transactionId) {
  var sheet = txSheet_();
  var row = findTxRow_(sheet, transactionId);
  if (row === -1) return { found: false };

  var amount = sheet.getRange(row, TX_COL.AMOUNT).getValue();
  var category = sheet.getRange(row, TX_COL.CATEGORY).getValue();
  var type = sheet.getRange(row, TX_COL.TYPE).getValue();

  sheet.deleteRow(row);

  if (type === 'Expense' || type === 'Transfer') {
    applyBudgetDelta_(category, -Number(amount) || 0);
  }
  return { found: true };
}

function getTransactions(filters) {
  var sheet = txSheet_();
  var lastRow = sheet.getLastRow();
  var out = [];
  if (lastRow < TX_DATA_START_ROW) return { transactions: out };

  var values = sheet.getRange(TX_DATA_START_ROW, 1, lastRow - TX_DATA_START_ROW + 1, TX_COL.TAGS).getValues();
  var dateFrom = filters.dateFrom ? parseDateOnly_(filters.dateFrom) : null;
  var dateTo = filters.dateTo ? new Date(String(filters.dateTo).trim() + 'T23:59:59.999+07:00') : null;

  for (var i = 0; i < values.length; i++) {
    var v = values[i];
    if (!v[TX_COL.ID - 1]) continue; // skip blank template rows

    var txDate = v[TX_COL.DATE - 1] instanceof Date ? v[TX_COL.DATE - 1] : new Date(v[TX_COL.DATE - 1]);
    if (dateFrom && txDate < dateFrom) continue;
    // dateTo is already end-of-day (23:59:59.999) for the requested date —
    // comparing directly, no extra day offset needed.
    if (dateTo && txDate > dateTo) continue;
    if (filters.category && v[TX_COL.CATEGORY - 1] !== filters.category) continue;
    if (filters.type && v[TX_COL.TYPE - 1] !== filters.type) continue;

    out.push({
      transactionId: v[TX_COL.ID - 1],
      date: formatDate_(v[TX_COL.DATE - 1]),
      time: formatTime_(v[TX_COL.TIME - 1]),
      type: v[TX_COL.TYPE - 1],
      category: v[TX_COL.CATEGORY - 1],
      needWantGoal: v[TX_COL.NEED_WANT_GOAL - 1],
      fixedVariable: v[TX_COL.FIXED_VARIABLE - 1],
      amount: v[TX_COL.AMOUNT - 1],
      account: v[TX_COL.ACCOUNT - 1],
      merchant: v[TX_COL.MERCHANT - 1],
      paymentMethod: v[TX_COL.PAYMENT_METHOD - 1],
      notes: v[TX_COL.NOTES - 1],
      tags: v[TX_COL.TAGS - 1],
    });
  }
  return { transactions: out };
}

function getBalance(year, month) {
  var all = getTransactions({}).transactions;
  var income = 0, expense = 0, transfer = 0;
  for (var i = 0; i < all.length; i++) {
    var t = all[i];
    if (year && month) {
      var d = parseDateOnly_(t.date);
      if (!d || d.getFullYear() !== Number(year) || d.getMonth() + 1 !== Number(month)) continue;
    }
    if (t.type === 'Income') income += Number(t.amount) || 0;
    else if (t.type === 'Expense') expense += Number(t.amount) || 0;
    else if (t.type === 'Transfer') transfer += Number(t.amount) || 0;
  }
  return { balance: { income: income, expense: expense, transfer: transfer, net: income - expense - transfer } };
}

function formatDate_(value) {
  if (value instanceof Date) return Utilities.formatDate(value, SCRIPT_TIMEZONE, 'yyyy-MM-dd');
  return String(value);
}

function formatTime_(value) {
  if (value instanceof Date) return Utilities.formatDate(value, SCRIPT_TIMEZONE, 'HH:mm:ss');
  return String(value || '00:00:00');
}

// ============================================================================
// BUDGET PLANNER
// ============================================================================

function budgetSheet_() {
  return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_BUDGET);
}

function getBudgets() {
  var sheet = budgetSheet_();
  var out = [];
  for (var label in BUDGET_ROWS) {
    var meta = BUDGET_ROWS[label];
    var vals = sheet.getRange(meta.row, 1, 1, BUDGET_COL.STATUS).getValues()[0]; // starts at col A so vals[COL-1] indexing is direct
    out.push({
      category: vals[BUDGET_COL.LABEL - 1] || label,
      section: meta.section,
      budget: vals[BUDGET_COL.BUDGET - 1] || 0,
      actual: vals[BUDGET_COL.ACTUAL - 1] || 0,
      difference: vals[BUDGET_COL.DIFF - 1] || 0,
      pctOfIncome: vals[BUDGET_COL.PCT_INCOME - 1] || 0,
      status: vals[BUDGET_COL.STATUS - 1] || '',
    });
  }
  return { budgets: out };
}

function findBudgetLabel_(label) {
  var norm = String(label).trim().toLowerCase();
  for (var known in BUDGET_ROWS) {
    if (known.toLowerCase() === norm) return known;
  }
  return null;
}

function setBudgetAmount(category, amount) {
  var match = findBudgetLabel_(category);
  if (!match) return { found: false };
  var sheet = budgetSheet_();
  var row = BUDGET_ROWS[match].row;
  sheet.getRange(row, BUDGET_COL.BUDGET).setValue(Number(amount));
  SpreadsheetApp.flush();
  var vals = sheet.getRange(row, 1, 1, BUDGET_COL.STATUS).getValues()[0]; // starts at col A so vals[COL-1] indexing is direct
  return {
    found: true,
    budget: {
      category: match, section: BUDGET_ROWS[match].section,
      budget: vals[BUDGET_COL.BUDGET - 1] || 0, actual: vals[BUDGET_COL.ACTUAL - 1] || 0,
      difference: vals[BUDGET_COL.DIFF - 1] || 0, pctOfIncome: vals[BUDGET_COL.PCT_INCOME - 1] || 0,
      status: vals[BUDGET_COL.STATUS - 1] || '',
    },
  };
}

/**
 * Increments (or decrements, if delta is negative) a Budget Planner row's
 * AKTUAL cell based on a Cashflow Harian category, and returns an alert
 * string if this exact call just crossed the 80/90/100% threshold —
 * computed statelessly from before/after values, so no separate "already
 * alerted" flag needs to live anywhere.
 */
function applyBudgetDelta_(category, delta) {
  var label = BUDGET_CATEGORY_MAP[category];
  if (!label || !BUDGET_ROWS[label]) return null;

  var sheet = budgetSheet_();
  var row = BUDGET_ROWS[label].row;
  var actualCell = sheet.getRange(row, BUDGET_COL.ACTUAL);
  var budgetCell = sheet.getRange(row, BUDGET_COL.BUDGET);

  var before = Number(actualCell.getValue()) || 0;
  var after = before + delta;
  actualCell.setValue(after);
  SpreadsheetApp.flush();

  if (delta <= 0) return null; // only alert on increases (new spending)
  var budget = Number(budgetCell.getValue()) || 0;
  if (budget <= 0) return null;

  var beforePct = before / budget;
  var afterPct = after / budget;
  for (var i = 0; i < BUDGET_ALERT_THRESHOLDS.length; i++) {
    var t = BUDGET_ALERT_THRESHOLDS[i];
    if (beforePct < t && afterPct >= t) {
      var emoji = t >= 1.0 ? '🚨' : '⚠️';
      return emoji + ' *Budget Alert* — ' + label + '\n' +
        'You\'ve used ' + Math.round(afterPct * 100) + '% of your budget (' +
        after.toLocaleString('id-ID') + ' / ' + budget.toLocaleString('id-ID') + ').';
    }
  }
  return null;
}

// ============================================================================
// GOAL PLANNING
// ============================================================================

function goalSheet_() {
  return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_GOALS);
}

function goalRowToObject_(sheet, row) {
  var name = sheet.getRange(row, GOAL_COL.NAME).getValue();
  if (!name) return null;
  return {
    name: String(name),
    targetAmount: sheet.getRange(row, GOAL_COL.TARGET).getValue() || 0,
    currentAmount: sheet.getRange(row, GOAL_COL.CURRENT).getValue() || 0,
    horizonYears: sheet.getRange(row, GOAL_COL.HORIZON).getValue() || null,
    monthlySaving: sheet.getRange(row, GOAL_COL.MONTHLY_SAVING).getValue() || null,
    futureValue: sheet.getRange(row, GOAL_COL.FUTURE_VALUE).getValue() || null,
    feasibility: sheet.getRange(row, GOAL_COL.FEASIBILITY).getValue() || null,
  };
}

function getGoals() {
  var sheet = goalSheet_();
  var out = [];
  for (var i = 0; i < GOAL_ROWS.length; i++) {
    var obj = goalRowToObject_(sheet, GOAL_ROWS[i]);
    if (obj) out.push(obj);
  }
  return { goals: out };
}

function findGoalRow_(sheet, name) {
  var norm = String(name).trim().toLowerCase();
  for (var i = 0; i < GOAL_ROWS.length; i++) {
    var row = GOAL_ROWS[i];
    var cellName = String(sheet.getRange(row, GOAL_COL.NAME).getValue() || '').trim().toLowerCase();
    if (cellName && cellName === norm) return row;
  }
  return -1;
}

function setGoalTarget(name, amount) {
  var sheet = goalSheet_();
  var row = findGoalRow_(sheet, name);
  if (row === -1) return { found: false };
  sheet.getRange(row, GOAL_COL.TARGET).setValue(Number(amount));
  SpreadsheetApp.flush();
  return { found: true, goal: goalRowToObject_(sheet, row) };
}

function contributeGoal(name, amount) {
  var sheet = goalSheet_();
  var row = findGoalRow_(sheet, name);
  if (row === -1) return { found: false };
  var current = Number(sheet.getRange(row, GOAL_COL.CURRENT).getValue()) || 0;
  sheet.getRange(row, GOAL_COL.CURRENT).setValue(current + Number(amount));
  SpreadsheetApp.flush();
  return { found: true, goal: goalRowToObject_(sheet, row) };
}

// ============================================================================
// Manual test helper — run this from the Apps Script editor (select
// `testPing` in the function dropdown, click Run) to sanity-check the
// script has edit access to the spreadsheet before deploying.
// ============================================================================
function testPing() {
  Logger.log(JSON.stringify(getBalance()));
  Logger.log(JSON.stringify(getBudgets()));
  Logger.log(JSON.stringify(getGoals()));
}