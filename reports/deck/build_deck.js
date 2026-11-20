// Executive deck for the Superstore analysis. Every figure comes from build/deck_data.json
// (python reports/deck/build_deck_data.py), which is computed from the pipeline marts.
//
//   npm install pptxgenjs
//   python reports/deck/build_deck_data.py
//   node reports/deck/build_deck.js
//   python reports/deck/apply_theme.py reports/Superstore_Executive_Deck.pptx
//
// Structured deck: theme colours + fonts, named layouts with placeholders, sections, speaker notes.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..");
const D = JSON.parse(fs.readFileSync(path.join(ROOT, "build", "deck_data.json"), "utf8"));
const OUT = path.join(ROOT, "reports", "Superstore_Executive_Deck.pptx");

// ---- theme (kept in step with apply_theme.py) ----------------------------------------------------
const THEME = {
  headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "1B2A2F", lt1: "FFFFFF", dk2: "0F4C5C", lt2: "EAF1F0", accent1: "0F4C5C", accent2: "E36414",
            accent3: "5B8E7D", accent4: "F4A259", accent5: "8CB369", accent6: "BC4B51", hlink: "0F4C5C", folHlink: "5B8E7D" },
};
const HEX = THEME.colors;           // chart colours must be hex
const MUTED = "4A5A5F";             // chart axis text (hex-only option)

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";        // 13.33 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Superstore sales: where the profit goes";
pres.author = "Superstore analytics project";
const C = pres.SchemeColor;

// ---- formatting helpers ---------------------------------------------------------------------------
const usd0 = (v) => "$" + Math.round(v).toLocaleString("en-US");
const usdK = (v) => (v < 0 ? "-" : "") + "$" + Math.round(Math.abs(v) / 1000).toLocaleString("en-US") + "K";
const usdM = (v) => "$" + (v / 1e6).toFixed(2) + "M";
const pct0 = (v) => Math.round(v * 100) + "%";
const pct1 = (v) => (v * 100).toFixed(1) + "%";

// ---- layouts --------------------------------------------------------------------------------------
const FOOT = "Superstore sales analysis  |  customer IDs masked  |  figures reconcile to the source data";
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.2, w: 8.4, h: 1.6, fontSize: 54, bold: true, color: C.background1, align: "left", valign: "bottom", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "subtitle", type: "body", x: 0.8, y: 3.95, w: 8.2, h: 1.0, fontSize: 22, color: C.background2, align: "left", valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.text1, align: "right" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.75, fontSize: 36, bold: true, color: C.text2, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "takeaway", type: "body", x: 0.6, y: 1.2, w: 12.1, h: 0.55, fontSize: 18, color: C.text1, align: "left", valign: "top", margin: 0 }, text: "" } },
    { text: { text: FOOT, options: { x: 0.6, y: 7.0, w: 10, h: 0.3, fontSize: 10, color: C.text1, margin: 0, isTextBox: true } } },
  ],
});

// ---- component helpers (always build fresh option objects: pptxgenjs mutates them) ----------------
function card(slide, name, x, y, w, h, fill) {
  slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.12, fill: { color: fill || C.background2 }, line: { color: fill || C.background2, width: 0 }, objectName: name });
}
function badge(slide, name, n, x, y, d, fill) {
  slide.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: fill || C.accent1 }, line: { color: fill || C.accent1, width: 0 }, objectName: name });
  slide.addText(String(n), { x, y, w: d, h: d, align: "center", valign: "middle", fontSize: Math.round(d * 30), bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: name + " number" });
}
function stat(slide, name, x, y, w, h, value, label, opts = {}) {
  card(slide, name + " card", x, y, w, h);
  slide.addText(value, { x: x + 0.25, y: y + 0.12, w: w - 0.5, h: h * 0.5, fontSize: opts.size || 36, bold: true, color: opts.color || C.accent1, valign: "bottom", margin: 0, isTextBox: true, objectName: name + " value" });
  slide.addText(label, { x: x + 0.25, y: y + h * 0.58, w: w - 0.5, h: h * 0.38, fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: name + " label" });
}
function chartBase(extra) {
  return Object.assign({
    showTitle: false, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", catAxisLabelFontSize: 12, valAxisLabelFontSize: 12,
    catAxisLabelColor: MUTED, valAxisLabelColor: MUTED, valGridLine: { color: "D5DEDC", size: 0.5 }, catGridLine: { style: "none" },
    dataLabelFontFace: "+mn-lt", dataLabelFontSize: 12, dataLabelColor: "1B2A2F", legendFontFace: "+mn-lt", legendFontSize: 12, legendColor: MUTED,
  }, extra);
}
function content(section, title, takeaway, notes) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  s.addText(takeaway, { placeholder: "takeaway" });
  s.addNotes(notes);
  return s;
}

// =====================================================================================================
pres.addSection({ title: "Overview" });
{ // 1 title
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Overview" });
  s.addText("Where the profit goes", { placeholder: "title" });
  s.addText("Superstore sales analysis, 2014 to 2017: what drives margin, and what to do about it", { placeholder: "subtitle" });
  s.addShape(pres.ShapeType.ellipse, { x: 9.5, y: 1.3, w: 3.3, h: 3.3, fill: { color: C.accent2 }, line: { color: C.accent2, width: 0 }, objectName: "Margin circle" });
  s.addText([{ text: pct1(D.kpi.margin), options: { fontSize: 44, bold: true, breakLine: true } }, { text: "profit margin", options: { fontSize: 16 } }],
    { x: 9.5, y: 1.3, w: 3.3, h: 3.3, align: "center", valign: "middle", color: C.background1, margin: 0, isTextBox: true, objectName: "Margin text" });
  s.addShape(pres.ShapeType.ellipse, { x: 8.7, y: 4.1, w: 2.6, h: 2.6, fill: { color: C.accent3 }, line: { color: C.accent3, width: 0 }, objectName: "Sales circle" });
  s.addText([{ text: usdM(D.kpi.sales), options: { fontSize: 32, bold: true, breakLine: true } }, { text: "total sales", options: { fontSize: 14 } }],
    { x: 8.7, y: 4.1, w: 2.6, h: 2.6, align: "center", valign: "middle", color: C.background1, margin: 0, isTextBox: true, objectName: "Sales text" });
  s.addText("Built from a tested data pipeline. Customer identities are masked.", { x: 0.8, y: 6.6, w: 7.5, h: 0.4, fontSize: 14, color: C.background2, margin: 0, isTextBox: true });
  s.addNotes("Title slide. All figures in this deck are computed from the pipeline's mart tables (reports/marts), which reconcile to the source file: 9,994 order lines, $2,297,200.86 sales, $286,397.02 profit.");
}

{ // 2 executive summary
  const s = content("Overview", "Executive summary", "Profitable growth, with one leak worth fixing",
    "Three headline numbers, then the three messages the rest of the deck supports. Sales, profit and margin come from mart_executive_kpis. The discount and furniture figures come from mart_discount_impact and mart_product_profitability.");
  const xs = [0.6, 4.7, 8.8];
  const kp = [[usdM(D.kpi.sales), "total sales"], [usdK(D.kpi.profit), "total profit"], [pct1(D.kpi.margin), "profit margin"]];
  kp.forEach(([v, l], i) => stat(s, "KPI " + (i + 1), xs[i], 1.95, 3.9, 1.5, v, l, { size: 40 }));
  const furn = D.category.find((c) => c.category === "Furniture");
  const tables = D.losing_subcats.find((c) => c.sub_category === "Tables");
  const msgs = [
    ["Growth is real. ", `Sales rose ${pct0(D.growth_total)} from 2014 to 2017 and margin improved from ${pct1(D.years[0].margin)} to ${pct1(D.years[3].margin)}.`],
    ["Deep discounts leak profit. ", `Lines discounted over 20% are ${pct0(D.deep_line_share)} of lines but ${pct0(D.deep_loss_share)} of all losses.`],
    ["Furniture is the weak spot. ", `${pct0(furn.sales_share)} of sales at a ${pct1(furn.margin)} margin; Tables alone lost ${usdK(Math.abs(tables.profit))}.`],
  ];
  msgs.forEach(([lead, rest], i) => {
    const y = 3.85 + i * 0.95;
    badge(s, "Message " + (i + 1), i + 1, 0.6, y, 0.65);
    s.addText([{ text: lead, options: { bold: true, color: C.text2 } }, { text: rest }], { x: 1.5, y: y - 0.05, w: 11.2, h: 0.75, fontSize: 18, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "Message " + (i + 1) + " text" });
  });
}

pres.addSection({ title: "Findings" });
{ // 3 growth
  const s = content("Findings", "Growth with healthier margins", `Sales are up ${pct0(D.growth_total)} since 2014, and profit grew faster than sales`,
    `Source: mart_executive_kpis. Sales 2014 ${usd0(D.years[0].sales)} to 2017 ${usd0(D.years[3].sales)}. 2015 dipped ${pct1(Math.abs(D.dip_2015))} versus 2014, then sales grew every year. Margin is profit / sales; Profit is the dataset's order-level profit.`);
  const labels = D.years.map((y) => y.period);
  s.addChart(pres.charts.BAR, [
    { name: "Sales", labels, values: D.years.map((y) => y.sales) },
    { name: "Profit", labels, values: D.years.map((y) => y.profit) },
  ], chartBase({ x: 0.6, y: 1.95, w: 7.6, h: 4.9, barDir: "col", barGrouping: "clustered", chartColors: [HEX.accent1, HEX.accent2], showLegend: true, legendPos: "b",
    showValue: true, dataLabelFormatCode: '$#,##0,"K"', dataLabelPosition: "outEnd", valAxisLabelFormatCode: '$#,##0,"K"', valAxisMinVal: 0 }));
  stat(s, "Sales growth", 8.6, 1.95, 4.1, 1.4, "+" + pct0(D.growth_total), "sales, 2014 to 2017");
  stat(s, "Margin", 8.6, 3.6, 4.1, 1.4, pct1(D.years[0].margin) + " to " + pct1(D.years[3].margin), "profit margin, 2014 to 2017", { size: 30 });
  stat(s, "Dip", 8.6, 5.25, 4.1, 1.4, "-" + pct1(Math.abs(D.dip_2015)), "sales dip in 2015, the only down year", { color: C.accent2 });
}

{ // 4 category
  const order = ["Furniture", "Office Supplies", "Technology"];
  const cats = order.map((n) => D.category.find((c) => c.category === n));
  const furn = cats[0];
  const s = content("Findings", "Furniture is the weak spot", `Furniture earns ${pct1(furn.margin)} on ${pct0(furn.sales_share)} of sales; the other categories earn about 17%`,
    "Source: mart_product_profitability and mart_sales_flat. Profit share = category profit / total profit. Tables (-$17.7K), Bookcases (-$3.5K) and Supplies (-$1.2K) are the only loss-making sub-categories. This shows where profit is lost, not why.");
  s.addChart(pres.charts.BAR, [{ name: "Profit margin", labels: order, values: cats.map((c) => c.margin) }],
    chartBase({ x: 0.6, y: 1.95, w: 6.2, h: 4.9, barDir: "col", chartColors: [HEX.accent2, HEX.accent1, HEX.accent1], showLegend: false, showValue: true,
      dataLabelFormatCode: "0.0%", dataLabelPosition: "outEnd", valAxisLabelFormatCode: "0%", valAxisMinVal: 0, valAxisMaxVal: 0.2 }));
  const items = [
    [`${pct0(furn.sales_share)} of sales, ${pct0(furn.profit_share)} of profit`, "Furniture sells a lot and keeps little."],
    ["Three sub-categories lose money", D.losing_subcats.map((c) => `${c.sub_category} ${usdK(c.profit)}`).join(", ")],
    ["Technology and Office Supplies carry the profit", `${usdK(cats[2].profit + cats[1].profit)} of ${usdK(D.kpi.profit)} total profit`],
  ];
  items.forEach(([h, t], i) => {
    const y = 1.95 + i * 1.7;
    card(s, "Insight " + (i + 1) + " card", 7.2, y, 5.5, 1.5);
    s.addText([{ text: h, options: { bold: true, color: C.text2, fontSize: 18, breakLine: true } }, { text: t, options: { fontSize: 14 } }],
      { x: 7.45, y: y + 0.1, w: 5.0, h: 1.3, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "Insight " + (i + 1) + " text" });
  });
}

{ // 5 discounts
  const bands = D.discount;
  const s = content("Findings", "Deep discounts drive the losses", "Margin falls from " + pct1(bands[0].margin) + " with no discount to " + pct0(bands[3].margin) + " above 40%",
    "Source: mart_discount_impact. Share of lines = order lines in the band / all order lines. Share of losses = loss in the band / total losses on loss-making lines. Caveat: discount depth is not random. It differs by product (Tables, Binders, Machines carry heavy discounts), so this is an association, not proof that discounts alone cause the losses.");
  s.addChart(pres.charts.BAR, [{ name: "Profit margin", labels: ["No discount", "1-20%", "21-40%", "Over 40%"], values: bands.map((b) => b.margin) }],
    chartBase({ x: 0.6, y: 1.95, w: 7.4, h: 4.9, barDir: "col", chartColors: [HEX.accent1, HEX.accent1, HEX.accent2, HEX.accent2], invertedColors: [HEX.accent2], showLegend: false,
      showValue: true, dataLabelFormatCode: "0.0%", dataLabelPosition: "outEnd", valAxisLabelFormatCode: "0%", catAxisLabelPos: "low", valAxisMinVal: -1, valAxisMaxVal: 0.5 }));
  stat(s, "Loss share", 8.4, 1.95, 4.3, 2.4, pct0(D.deep_loss_share), `of all losses come from lines discounted over 20%, which are only ${pct0(D.deep_line_share)} of lines`, { size: 54, color: C.accent2 });
  card(s, "Caveat card", 8.4, 4.6, 4.3, 2.25);
  s.addText([{ text: "Read with care", options: { bold: true, color: C.text2, fontSize: 16, breakLine: true } },
    { text: "Discount depth differs by product, so this shows an association, not proof that discounts alone cause the losses.", options: { fontSize: 14 } }],
    { x: 8.65, y: 4.7, w: 3.8, h: 2.05, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "Caveat text" });
}

{ // 6 what-if
  const caps = [0.1, 0.2, 0.3];
  const get = (cap, ret) => D.what_if.find((w) => Math.abs(w.discount_cap - cap) < 1e-9 && Math.abs(w.volume_retention - ret) < 1e-9);
  const s = content("Findings", "What if discounts were capped?", `A 20% cap would have added ${usdK(get(0.2, 0).profit_delta)} to ${usdK(get(0.2, 1).profit_delta)} across the demand cases tested (a scenario, not a forecast)`,
    "Source: mart_discount_what_if. Method: lines discounted above the cap are repriced at the cap; cost scales with the share of volume kept. 100% retention assumes no demand loss (an upper bound). 0% retention assumes those lines are lost entirely (a floor: the lost lines were loss-making in total). The floor ignores knock-on effects on other lines in the same orders and on customer behaviour. Elasticity is unknown, so pilot before rolling out.");
  const labels = caps.map((c) => "Cap at " + pct0(c));
  s.addChart(pres.charts.BAR, [
    { name: "Keep 100% of volume (upper bound)", labels, values: caps.map((c) => get(c, 1).profit_delta) },
    { name: "Keep 60% of volume", labels, values: caps.map((c) => get(c, 0.6).profit_delta) },
    { name: "Keep 0% of volume (floor)", labels, values: caps.map((c) => get(c, 0).profit_delta) },
  ], chartBase({ x: 0.6, y: 1.95, w: 7.8, h: 4.9, barDir: "col", barGrouping: "clustered", chartColors: [HEX.accent1, HEX.accent3, HEX.accent2], showLegend: true, legendPos: "b",
    showValue: true, dataLabelFormatCode: '$#,##0,"K"', dataLabelPosition: "outEnd", valAxisLabelFormatCode: '$#,##0,"K"', valAxisMinVal: 0 }));
  card(s, "How to read card", 8.8, 1.95, 3.9, 4.9);
  s.addText([
    { text: "How to read this", options: { bold: true, color: C.text2, fontSize: 18, breakLine: true } },
    { text: "Profit gain versus today on lines above the cap.", options: { bullet: true, breakLine: true } },
    { text: "Cost scales with the volume kept.", options: { bullet: true, breakLine: true } },
    { text: "The floor ignores knock-on effects on other lines in the same orders.", options: { bullet: true, breakLine: true } },
    { text: "Demand response is unknown, so the bars bracket the answer.", options: { bullet: true, breakLine: true } },
    { text: "Pilot in one region before any roll-out.", options: { bullet: true } },
  ], { x: 9.05, y: 2.1, w: 3.4, h: 4.6, fontSize: 16, color: C.text1, valign: "middle", margin: 0, paraSpaceAfter: 10, isTextBox: true, objectName: "How to read text" });
}

{ // 7 customers
  const seg = D.rfm;
  const risk = seg.find((x) => x.rfm_segment === "At Risk");
  const champ = seg.find((x) => x.rfm_segment === "Champions");
  const s = content("Findings", "Protect the customers slipping away", `At Risk customers are ${pct0(risk.customers / D.rfm_total_customers)} of customers but ${pct0(risk.sales / D.rfm_total_sales)} of sales`,
    "Source: mart_customer_rfm. Recency, Frequency and Monetary scores are quintiles; segments follow the rules in warehouse/duckdb/models/34_mart_customer_rfm.sql. Customers are masked tokens, so a win-back list would be built from the token mapping held by the data owner.");
  const ordered = seg.slice().sort((a, b) => a.sales - b.sales);   // horizontal bars read bottom-up
  s.addChart(pres.charts.BAR, [{ name: "Sales", labels: ordered.map((x) => x.rfm_segment), values: ordered.map((x) => x.sales) }],
    chartBase({ x: 0.6, y: 1.95, w: 7.6, h: 4.9, barDir: "bar", chartColors: ordered.map((x) => (x.rfm_segment === "At Risk" ? HEX.accent2 : HEX.accent1)), showLegend: false,
      showValue: true, dataLabelFormatCode: '$#,##0,"K"', dataLabelPosition: "outEnd", valAxisLabelFormatCode: '$#,##0,"K"', valAxisMinVal: 0 }));
  stat(s, "At risk", 8.6, 1.95, 4.1, 2.2, usdK(risk.sales), `sales from ${risk.customers} At Risk customers: a win-back target`, { color: C.accent2, size: 44 });
  stat(s, "Champions", 8.6, 4.4, 4.1, 2.2, usdK(champ.sales), `sales from ${champ.customers} Champions: keep them happy`, { size: 44 });
}

pres.addSection({ title: "Outlook" });
{ // 8 valuation
  const v = D.valuation;
  const s = content("Outlook", "Illustrative valuation range", "A DCF shows how much the answer depends on assumptions, not on the data",
    "Source: src/superstore_pipeline/valuation.py, cross-checked against excel/finance/Superstore_DCF_Valuation.xlsx. Profit is used as an EBIT proxy; there is no balance sheet, so net debt is zero. Growth, margins, tax, capex, working capital and cost of capital are illustrative placeholders, not market data. Terminal value is about " + pct0(v.tv_share) + " of the base enterprise value. Educational model, not investment advice.");
  const cards = [["Bear", v.ev.Bear, "growth fades from 6% to 2%, margin 9% to 11%"], ["Base", v.ev.Base, "growth fades from 12% to 5%, margin 12.5%"], ["Bull", v.ev.Bull, "growth fades from 16% to 8%, margin 14%"]];
  cards.forEach(([name, ev, desc], i) => {
    const x = [0.6, 4.7, 8.8][i];
    card(s, name + " card", x, 1.95, 3.9, 2.7, name === "Base" ? C.background2 : C.background2);
    s.addText(name + " scenario", { x: x + 0.3, y: 2.1, w: 3.3, h: 0.4, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: name + " name" });
    s.addText(usdM(ev), { x: x + 0.3, y: 2.55, w: 3.3, h: 0.9, fontSize: 44, bold: true, color: name === "Base" ? C.accent2 : C.accent1, valign: "middle", margin: 0, isTextBox: true, objectName: name + " value" });
    s.addText("enterprise value", { x: x + 0.3, y: 3.45, w: 3.3, h: 0.35, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, objectName: name + " label" });
    s.addText(desc, { x: x + 0.3, y: 3.85, w: 3.3, h: 0.65, fontSize: 12, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: name + " drivers" });
  });
  card(s, "Warning card", 0.6, 4.95, 12.1, 1.9);
  badge(s, "Warning", "!", 0.9, 5.45, 0.9, C.accent2);
  s.addText([
    { text: "Illustrative only. ", options: { bold: true, color: C.text2 } },
    { text: `Profit stands in for operating profit, there is no balance sheet, and the ${pct1(v.wacc)} discount rate, ${pct1(v.terminal_growth)} terminal growth and all forecast drivers are placeholders. About ${pct0(v.tv_share)} of the base value sits in the terminal value. Replace the inputs before drawing conclusions.` },
  ], { x: 2.1, y: 5.05, w: 10.35, h: 1.7, fontSize: 16, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "Warning text" });
}

{ // 9 recommendations
  const s = content("Outlook", "Recommended next steps", "Fix the discount leak first, then Furniture, then win back At Risk customers",
    "Each action maps to a finding: slide 5 (discount gate), slide 4 (furniture), slide 7 (win-back), slide 6 (pilot). The limits card lists what this analysis cannot tell us.");
  const risk = D.rfm.find((x) => x.rfm_segment === "At Risk");
  const acts = [
    ["Gate deep discounts. ", `Require approval above 20%: ${D.deep_lines.toLocaleString("en-US")} lines lost ${usdK(Math.abs(D.deep_baseline_profit))} in total.`],
    ["Review Furniture pricing. ", "Start with Tables and Bookcases, the two big loss-makers."],
    ["Win back At Risk customers. ", `${risk.customers} customers, ${usdK(risk.sales)} of sales.`],
    ["Pilot before rolling out. ", "Test a discount cap in one region to measure the real demand response."],
  ];
  acts.forEach(([lead, rest], i) => {
    const y = 1.95 + i * 1.22;
    badge(s, "Action " + (i + 1), i + 1, 0.6, y + 0.1, 0.65);
    s.addText([{ text: lead, options: { bold: true, color: C.text2 } }, { text: rest }], { x: 1.5, y, w: 6.3, h: 0.95, fontSize: 16, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "Action " + (i + 1) + " text" });
  });
  card(s, "Limits card", 8.3, 1.95, 4.4, 4.9);
  s.addText([
    { text: "Limits of this analysis", options: { bold: true, color: C.text2, fontSize: 18, breakLine: true } },
    { text: "One dataset, four years.", options: { bullet: true, breakLine: true } },
    { text: "Profit is as reported per order line.", options: { bullet: true, breakLine: true } },
    { text: "Customers are masked tokens.", options: { bullet: true, breakLine: true } },
    { text: "Patterns are associations, not proven causes.", options: { bullet: true, breakLine: true } },
    { text: "The what-if and valuation are scenarios.", options: { bullet: true } },
  ], { x: 8.55, y: 2.1, w: 3.9, h: 4.6, fontSize: 16, color: C.text1, valign: "middle", margin: 0, paraSpaceAfter: 12, isTextBox: true, objectName: "Limits text" });
}

pres.addSection({ title: "Appendix" });
{ // 10 pipeline
  const s = content("Appendix", "Appendix: how the numbers were produced", "A tested pipeline, so every figure traces back to the source file",
    "Pipeline: extract, validate (21 data-quality checks, errors stop the run), mask (HMAC-SHA256 pseudonymisation of customer IDs, postal codes generalised), load into a DuckDB star schema, build marts, reconcile to control totals, publish. Orchestrated by a step runner with a run log. See docs/ in the repository.");
  const steps = [["Extract", "read the source CSV"], ["Validate", "21 data-quality checks"], ["Mask", "pseudonymise IDs, generalise postcodes"], ["Model", "star schema in DuckDB"], ["Marts", "KPIs, discounts, RFM"], ["Reconcile", "control totals and keys"]];
  steps.forEach(([h, t], i) => {
    const x = 0.6 + i * 2.05;
    card(s, h + " card", x, 2.35, 1.85, 2.1);
    badge(s, "Step " + (i + 1), i + 1, x + 0.6, 2.0, 0.6);
    s.addText(h, { x: x + 0.1, y: 2.75, w: 1.65, h: 0.45, fontSize: 18, bold: true, color: C.text2, align: "center", margin: 0, isTextBox: true, objectName: h + " name" });
    s.addText(t, { x: x + 0.15, y: 3.25, w: 1.55, h: 1.3, fontSize: 14, color: C.text1, align: "center", valign: "top", margin: 0, isTextBox: true, objectName: h + " detail" });
  });
  card(s, "Control card", 0.6, 4.85, 5.9, 2.0);
  s.addText([{ text: "Control totals tie out", options: { bold: true, color: C.text2, fontSize: 16, breakLine: true } },
    { text: `${D.control.rows.toLocaleString("en-US")} rows, ${"$" + D.control.sales.toLocaleString("en-US", { minimumFractionDigits: 2 })} sales, ${"$" + D.control.profit.toLocaleString("en-US", { minimumFractionDigits: 2 })} profit.`, options: { fontSize: 14 } }],
    { x: 0.85, y: 4.95, w: 5.4, h: 1.8, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "Control text" });
  card(s, "Privacy card", 6.8, 4.85, 5.9, 2.0);
  s.addText([{ text: "Privacy by design", options: { bold: true, color: C.text2, fontSize: 16, breakLine: true } },
    { text: "Customer IDs are one-way tokens and postal codes are generalised before anything is loaded or shared.", options: { fontSize: 14 } }],
    { x: 7.05, y: 4.95, w: 5.4, h: 1.8, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "Privacy text" });
}

pres.writeFile({ fileName: OUT }).then(() => console.log("wrote " + path.relative(ROOT, OUT)));
module.exports = { THEME };
