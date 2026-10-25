"""Thành phần giao diện dùng chung cho dashboard: bảng màu, định dạng số, CSS, thẻ KPI, bố cục biểu đồ.

Tách khỏi app.py để test có thể dùng đúng hàm định dạng mà giao diện hiển thị.
Không phụ thuộc Streamlit ở mức import (trừ các hàm render nhận module st làm tham số ngầm).
"""

from __future__ import annotations

import html
import math

# ----------------------------------------------------------------------------- bảng màu (phương án B: đất ấm)

BRAND = "#3E4A3D"  # nâu ô liu đậm: thanh bên, tiêu đề mục
ACCENT = "#C08A3E"  # đồng: mục đang chọn, điểm nhấn
NAVY = "#36584A"  # xanh rêu đậm: màu chính (regime-aware, HMM)
POS, NEG, MUTED = "#4F7F5C", "#A9472F", "#7A7368"
INK, GRID, LINE = "#2E2A24", "#ECE6DC", "#D6CEC1"
WARN = "#B07A2A"
BG = "#E7E1D8"

HIGH, LOW = "#B5523B", "#5B8C6A"  # state rủi ro cao / thấp
OTHER = ["#C9A227", "#7A6C9B", "#5E8A9A", "#8C8273"]  # các state trung gian
STRATEGY_COLORS = {"buy_and_hold": "#A79C8C", "regime_aware": NAVY}
METHOD_COLORS = {"HMM": NAVY, "GMM": ACCENT}
PERIOD_COLORS = {"train": NAVY, "validation": "#8FB39A", "test": "#D6CEC1"}


# ----------------------------------------------------------------------------- định dạng số kiểu Việt Nam


def _bad(x) -> bool:
    try:
        return x is None or not math.isfinite(float(x))
    except (TypeError, ValueError):
        return True


def _vn(s: str) -> str:
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def num(x, d: int = 2, sign: bool = False) -> str:
    """Số thập phân kiểu Việt Nam: 1.234,56."""
    return "-" if _bad(x) else _vn(f"{float(x):{'+' if sign else ''},.{d}f}")


def pct(x, d: int = 2, sign: bool = False) -> str:
    """Tỷ lệ (0,05 -> 5,00%)."""
    return "-" if _bad(x) else _vn(f"{float(x) * 100:{'+' if sign else ''},.{d}f}") + "%"


def pp(x, d: int = 2) -> str:
    """Chênh lệch theo điểm phần trăm."""
    return "-" if _bad(x) else _vn(f"{float(x) * 100:+,.{d}f}") + " điểm %"


def sign_color(x, higher_is_better: bool = True) -> str:
    if _bad(x) or float(x) == 0:
        return MUTED
    good = float(x) > 0 if higher_is_better else float(x) < 0
    return POS if good else NEG


def esc(x) -> str:
    return html.escape(str(x))


# ----------------------------------------------------------------------------- nhãn state


def state_name(sid, label_map) -> str:
    """'High-Vol (state 0)'; state chưa có nhãn mô tả thì chỉ ghi 'State 1'."""
    label = label_map[str(int(sid))]
    return label if label == f"State {int(sid)}" else f"{label} (state {int(sid)})"


def state_colors(label_map) -> dict:
    colors, i = {}, 0
    for sid in sorted(label_map, key=int):
        label = label_map[sid]
        if label == "High-Vol":
            colors[int(sid)] = HIGH
        elif label == "Low-Vol":
            colors[int(sid)] = LOW
        else:
            colors[int(sid)] = OTHER[i % len(OTHER)]
            i += 1
    return colors


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


# ----------------------------------------------------------------------------- nền chủ đề và CSS


def _background_svg() -> str:
    """Họa tiết nền tự vẽ: lưới mờ, chuỗi nến giá và hai đường dữ liệu chạy ngang (không dùng ảnh bản quyền)."""
    import math as _m
    import random

    rnd = random.Random(7)
    w, h = 1600, 900
    parts = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}'>"]
    for x in range(0, w, 80):
        parts.append(f"<line x1='{x}' y1='0' x2='{x}' y2='{h}' stroke='#3E4A3D' stroke-opacity='.05'/>")
    for y in range(0, h, 80):
        parts.append(f"<line x1='0' y1='{y}' x2='{w}' y2='{y}' stroke='#3E4A3D' stroke-opacity='.05'/>")
    price = 560.0
    for i in range(64):
        x = 20 + i * 25
        o = price
        price += rnd.gauss(-1.2, 16)
        c = price
        hi, lo = max(o, c) + rnd.uniform(4, 18), min(o, c) - rnd.uniform(4, 18)
        col = "#5B8C6A" if c < o else "#B5523B"
        parts.append(f"<line x1='{x + 6}' y1='{lo:.0f}' x2='{x + 6}' y2='{hi:.0f}' stroke='{col}' stroke-opacity='.16'/>")
        parts.append(f"<rect x='{x}' y='{min(o, c):.0f}' width='12' height='{max(abs(c - o), 2):.0f}' "
                     f"fill='{col}' fill-opacity='.13'/>")
    for k, (amp, base, col) in enumerate(((60, 300, "#C08A3E"), (45, 760, "#36584A"))):
        pts = " ".join(f"{x},{base + amp * _m.sin(x / 140 + k) + 18 * _m.sin(x / 37):.0f}" for x in range(0, w + 1, 20))
        parts.append(f"<polyline points='{pts}' fill='none' stroke='{col}' stroke-opacity='.18' stroke-width='2'/>")
    parts.append("</svg>")
    return "".join(parts)


def _bg_uri() -> str:
    import base64

    return "data:image/svg+xml;base64," + base64.b64encode(_background_svg().encode()).decode()


CSS = f"""
<style>
.stApp {{background:#F5F4F0; color:{INK}; font-family:'Segoe UI',sans-serif;}}
header[data-testid="stHeader"] {{background:transparent;}}
.block-container {{padding:2rem clamp(20px,3vw,48px) 2.5rem; max-width:1560px;
    container-type:inline-size; container-name:dashboard;}}
[data-testid="stHorizontalBlock"] {{gap:16px;}}
[data-testid="stColumn"] {{min-width:0;}}
[data-testid="stMarkdownContainer"] p {{font-size:.9rem; line-height:1.6;}}
[data-testid="stCaptionContainer"] p {{font-size:.76rem; line-height:1.55; color:#756F65;}}
[data-testid="stSidebar"][data-collapsed="false"] {{width:248px !important; min-width:248px !important;
    max-width:248px !important; flex-basis:248px !important;}}
/* The sidebar has a fixed width; hide the inactive resize affordance outside its edge. */
section[data-testid="stSidebar"] div:has(> [data-testid="stSidebarResizeHandle"]) {{display:none;}}

section[data-testid="stSidebar"] {{background:{BRAND};}}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{padding:1rem 0 .75rem;}}
section[data-testid="stSidebar"] * {{color:#E9E3D7;}}
section[data-testid="stSidebar"] code {{background:rgba(255,255,255,.10); color:#F0D9A8 !important;}}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{opacity:1 !important;}}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{color:#CFD6C9 !important; opacity:1 !important; font-size:.75rem;}}
/* menu điều hướng */
.st-key-nav, .st-key-nav [data-testid="stRadio"], .st-key-nav [role="radiogroup"],
.st-key-nav [role="radiogroup"] > div {{width:100% !important;}}
.st-key-nav [role="radiogroup"] {{gap:2px;}}
[class*="st-key-nav"] [data-testid="stRadioOption"] > div > div:first-child,
[class*="st-key-asset"] [data-testid="stRadioOption"] > div > div:first-child {{display:none;}}
.st-key-nav [data-testid="stRadioOption"] {{padding:10px 12px; border-radius:6px; width:100%; margin:0;
    border-left:3px solid transparent; cursor:pointer;}}
.st-key-nav [data-testid="stRadioOption"]:hover {{background:rgba(255,255,255,.07);}}
.st-key-nav [data-testid="stRadioOption"][data-selected="true"] {{background:rgba(255,255,255,.13);
    border-left:3px solid {ACCENT};}}
.st-key-nav [data-testid="stRadioOption"] p {{font-size:.95rem; font-weight:500;}}
.st-key-nav [data-testid="stRadioOption"][data-selected="true"] p {{color:#fff !important; font-weight:700;}}
.st-key-asset [role="radiogroup"] {{gap:6px;}}
.st-key-asset [data-testid="stRadioOption"] {{background:rgba(255,255,255,.07); padding:6px 16px; border-radius:6px;
    border:1px solid rgba(255,255,255,.18); margin:0; cursor:pointer;}}
.st-key-asset [data-testid="stRadioOption"][data-selected="true"] {{background:{ACCENT}; border-color:{ACCENT};}}
.st-key-asset [data-testid="stRadioOption"][data-selected="true"] p {{color:#2E2A24 !important; font-weight:800;}}
.wordmark {{font-weight:650; letter-spacing:-.025em; font-size:1.3rem; color:#fff !important; margin:0 0 16px; line-height:1.25;}}
.wordmark span {{color:{ACCENT} !important;}}
.wordmark small {{display:block; font-size:.7rem; color:#BFC7BB !important; letter-spacing:.03em; font-weight:400; margin-top:7px;}}
.sidecap {{font-size:.68rem; letter-spacing:.1em; color:#B9B09F !important; margin:18px 0 6px 0; font-weight:700;}}
.asof {{background:rgba(255,255,255,.07); border-radius:6px; padding:10px 12px; font-size:.82rem; line-height:1.5;}}
.asof b {{font-size:1.05rem; color:#fff !important;}}

div[class*="st-key-card"] {{background:#FFF; border-radius:8px !important;
    border:1px solid #E5E7DF !important; box-shadow:none;}}
.sec {{font-size:.96rem; font-weight:600; letter-spacing:-.01em; color:{BRAND};
    margin:2px 0 10px; display:flex; justify-content:space-between; align-items:center;}}
.sec span {{text-transform:none; letter-spacing:0; font-weight:500; color:{MUTED};}}
.info {{display:inline-block; width:15px; height:15px; min-width:15px; flex:0 0 15px; border-radius:50%; border:1px solid {MUTED}; color:{MUTED};
    font-size:.62rem; line-height:13px; text-align:center; cursor:help; font-weight:600; text-transform:none; margin-left:6px;}}

.kpi-grid {{display:grid; grid-template-columns:repeat(var(--columns),minmax(0,1fr)); gap:0; margin:0 0 12px;
    background:#FFF; border:1px solid #E5E7DF; border-radius:8px; padding:8px 0;}}
.kpi {{box-sizing:border-box; border-right:1px solid #EBEDE7; padding:10px 16px; min-height:100px; height:100%; min-width:0;}}
.kpi:last-child {{border-right:none;}}
.kpi .l {{color:#6D746A; font-size:.73rem; font-weight:400;
    display:flex; justify-content:space-between; align-items:flex-start; line-height:1.45; gap:4px;}}
.kpi .l>span:first-child {{min-width:0; overflow-wrap:break-word;}}
.kpi .v {{font-size:clamp(1.3rem,1.8vw,1.8rem); font-weight:600; letter-spacing:-.035em; color:var(--c); line-height:1.3; margin:9px 0 5px; overflow-wrap:anywhere;
    font-variant-numeric:tabular-nums;}}
.kpi .s {{color:#756F65; font-size:.74rem; line-height:1.45; white-space:normal; overflow-wrap:break-word;}}
.pill {{display:inline-block; color:var(--c); font-weight:600; background:transparent !important; font-size:inherit;}}

.hero {{display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; margin:0 0 24px;}}
.hero .t {{font-size:2rem; font-weight:600; letter-spacing:-.045em; color:{INK}; margin:0; line-height:1.25;}}
.hero .t span {{display:block; color:#72796D; font-weight:400; letter-spacing:0; margin-top:6px; font-size:.82rem;}}
.tag {{display:inline-block; padding:3px 10px; border-radius:999px; font-size:.75rem; font-weight:600;
    background:rgba(176,122,42,.14); color:{WARN}; border:1px solid rgba(176,122,42,.35); margin-left:6px;}}
.muted {{color:{MUTED}; font-size:.82rem; line-height:1.5;}}
.chip {{display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; vertical-align:middle;}}
.profgrid {{display:grid; grid-template-columns:1fr; gap:8px;}}
.profgrid.two {{grid-template-columns:1fr 1fr;}}
.profgrid .prof {{margin-bottom:0;}}
.profgrid > div {{min-width:0;}}
.profgrid.two .prof .g {{grid-template-columns:1fr 1fr; row-gap:8px;}}
.prof {{border-radius:10px; padding:10px 12px; background:rgba(255,255,255,.6); border-left:5px solid var(--c);
    margin-bottom:8px;}}
.prof .n {{font-weight:800; color:var(--c); font-size:.95rem;}}
.prof .g {{display:grid; grid-template-columns:repeat(4, 1fr); gap:6px; margin-top:4px;}}
.prof .g div {{font-size:.7rem; color:{MUTED}; text-transform:uppercase; letter-spacing:.03em;}}
.prof .g b {{display:block; font-size:1.02rem; color:{INK}; text-transform:none; letter-spacing:0;}}
.note {{border-left:3px solid var(--c); background:rgba(255,255,255,.55); padding:8px 12px; margin:6px 0;
    font-size:.88rem; color:#4A443B; border-radius:4px;}}
.rule {{display:flex; gap:10px; margin:8px 0 4px 0;}}
.rule div {{flex:1; border:1px solid {LINE}; border-radius:6px; padding:8px 10px; text-align:center;}}
.rule div.on {{border:2px solid var(--c); background:var(--bg);}}
.rule b {{display:block; font-size:1.25rem;}}

.table-scroll {{width:100%; min-width:0; overflow-x:auto; -webkit-overflow-scrolling:touch; border-radius:7px;}}
table.cmp {{width:100%; min-width:480px; border-collapse:collapse; font-size:.8rem; margin:0; line-height:1.45;}}
table.cmp th, table.cmp td {{border:none !important;}}
table.cmp th {{background:#F5F6F2; color:#65705F; padding:11px 10px; text-align:right; font-weight:500;}}
table.cmp th:first-child {{text-align:left;}}
table.cmp td {{padding:12px 10px; border-bottom:1px solid #ECEEE8 !important; text-align:right; color:{INK}; font-variant-numeric:tabular-nums;}}
table.cmp td:first-child {{text-align:left; color:#4A443B; white-space:nowrap;}}
table.cmp tr.grp td {{background:rgba(231,225,216,.6); font-weight:700; color:{BRAND}; font-size:.76rem;
    text-transform:uppercase; letter-spacing:.04em;}}
table.cmp tr.key td {{font-weight:700;}}
table.cmp tr.sel td {{background:#F0F5EE;}}
[data-testid="stAlert"] {{padding:6px 12px;}}
[data-testid="stAlertContainer"] {{background:#FAF6EA; color:#806330; border-radius:4px;}}
[data-testid="stAlertContainer"] p {{font-size:.8rem;}}
.radar-summary {{display:grid; grid-template-columns:1.25fr 1fr 1fr 1fr; gap:20px; align-items:end; margin:0 0 8px; padding:0;}}
.radar-summary .state {{font-size:2.25rem; font-weight:550; letter-spacing:-.04em; color:var(--c);}}
.radar-summary small {{display:block; color:#72796D; font-size:.74rem; line-height:1.65;}}
.radar-summary .number {{font-size:1.4rem; font-weight:500; letter-spacing:-.025em; color:{INK}; font-variant-numeric:tabular-nums;}}
.prob-cell {{display:flex; justify-content:flex-end; align-items:center; gap:10px;}}
.prob-track {{display:inline-block; width:72px; height:4px; background:#E9EDE6; border-radius:2px;}}
.prob-fill {{display:block; height:100%; background:var(--c); border-radius:2px;}}
.prob-cell .prob-value {{min-width:58px;}}
.regime-mobile {{display:none;}}
.regime-mobile-state {{border:1px solid #E5E7DF; border-left:3px solid var(--c); padding:12px; border-radius:6px;}}
.regime-mobile-state.selected {{background:#F0F5EE;}}
.regime-mobile-state strong {{color:{INK}; font-size:1rem;}}
.regime-mobile-state small {{display:block; color:{MUTED}; font-size:.72rem; margin:3px 0 10px;}}
.regime-mobile-state .probabilities {{display:grid; grid-template-columns:1fr 1fr; gap:16px;}}
.regime-mobile-state .probabilities span {{display:block; color:{MUTED}; font-size:.7rem;}}
.regime-mobile-state .probabilities b {{display:block; color:var(--c); font-size:1.1rem; margin-top:3px;}}
.katex-display {{overflow-x:auto; overflow-y:hidden;}}
@container dashboard (max-width:960px) {{.kpi-grid {{grid-template-columns:repeat(3,minmax(0,1fr));}}
    .kpi-grid[style*="--columns:4"] {{grid-template-columns:repeat(2,minmax(0,1fr));}}
    .kpi-grid[style*="--columns:4"] .kpi:nth-child(2n) {{border-right:none;}}
    .kpi-grid[style*="--columns:4"] .kpi:nth-child(3) {{border-right:1px solid #EBEDE7;}}
    .kpi:nth-child(3n) {{border-right:none;}}}}
@container dashboard (max-width:800px) {{
    [data-testid="stHorizontalBlock"] {{flex-direction:column;}}
    [data-testid="stHorizontalBlock"]>[data-testid="stColumn"] {{width:100% !important; flex:1 1 100% !important;}}
    .profgrid.two {{grid-template-columns:1fr;}}
}}
@container dashboard (max-width:520px) {{
    .regime-table {{display:none;}}
    .regime-mobile {{display:grid; grid-template-columns:1fr; gap:8px;}}
    .kpi-grid {{grid-template-columns:repeat(2,minmax(0,1fr));}}
    .kpi:nth-child(3n) {{border-right:1px solid #EBEDE7;}}
    .kpi:nth-child(2n) {{border-right:none;}}
    .radar-summary {{grid-template-columns:1fr 1fr; gap:20px;}}
    .hero .t span {{display:block; margin-top:3px;}}
    .sec {{align-items:flex-start; gap:8px; line-height:1.5;}}
    .sec span {{display:block;}}
    .prof .g {{grid-template-columns:1fr 1fr;}}
}}
@container dashboard (max-width:300px) {{.kpi-grid {{grid-template-columns:1fr;}}}}
.foot {{color:{MUTED}; font-size:.75rem; text-align:center; margin-top:18px;}}
</style>
"""



# ----------------------------------------------------------------------------- HTML nhỏ


def sec_html(title: str, sub: str = "", info: str = "") -> str:
    right = info_html(info) if info else ""
    return f"<div class='sec'><div>{title}{f' <span>· {sub}</span>' if sub else ''}</div>{right}</div>"


def kpi_html(label: str, value: str, sub: str = "", color: str = NAVY, info: str = "") -> str:
    tip = f"<span class='info' title='{esc(info)}'>i</span>" if info else ""
    return (f"<div class='kpi' style='--c:{color}'><div class='l'><span>{label}</span>{tip}</div>"
            f"<div class='v'>{value}</div><div class='s'>{sub}</div></div>")


def kpis_html(items) -> str:
    return f"<div class='kpi-grid' style='--columns:{len(items)}'>" + "".join(kpi_html(*item) for item in items) + "</div>"


def info_html(text: str) -> str:
    return f"<span class='info' title='{esc(text)}'>i</span>"


def chip(color: str) -> str:
    return f"<span class='chip' style='background:{color}'></span>"


def html_table(header: list, rows: list, row_classes: list | None = None) -> str:
    """Bảng HTML gọn; cột đầu canh trái, các cột còn lại canh phải. rows là list các list chuỗi (đã escape)."""
    head = "".join(f"<th>{h}</th>" for h in header)
    body = []
    for i, r in enumerate(rows):
        cls = row_classes[i] if row_classes else ""
        if cls == "grp":
            body.append(f"<tr class='grp'><td colspan='{len(header)}'>{r[0]}</td></tr>")
        else:
            body.append(f"<tr class='{cls}'>" + "".join(f"<td>{v}</td>" for v in r) + "</tr>")
    return f"<div class='table-scroll' role='region' aria-label='Bảng số liệu'><table class='cmp'><tr>{head}</tr>{''.join(body)}</table></div>"


# ----------------------------------------------------------------------------- Plotly


def chart_layout(fig, height: int = 360, title: str | None = None, legend: bool = True, **kw):
    """Nền trắng, lưới nhạt, chú giải nằm ngang phía trên vùng vẽ, dấu thập phân kiểu Việt Nam."""
    fig.update_layout(
        height=height, margin={"l": 10, "r": 10, "t": 72 if title else 36, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", separators=",.",
        font={"family": "Inter, Segoe UI, sans-serif", "size": 12, "color": INK},
        title={"text": title, "x": 0, "xanchor": "left", "y": 0.98, "yanchor": "top", "font": {"size": 14}} if title else None,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "x": 0, "bgcolor": "rgba(0,0,0,0)"} if legend else None,
        showlegend=legend, hoverlabel={"bgcolor": "white", "font_size": 12}, **kw,
    )
    fig.update_xaxes(showgrid=False, linecolor=LINE)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


# Terminal refinement: keep the established palette and existing Streamlit components.
CSS += f"""
<style>
.stApp {{background:#F7F6F1; font-family:Inter,Aptos,'Segoe UI',sans-serif;}}
.block-container {{padding-top:1.6rem; max-width:1512px;}}
.terminal-brand {{padding:4px 0 14px;}}
.terminal-brand .eyebrow {{display:block; color:{ACCENT}; margin-bottom:5px;}}
.terminal-title {{font-size:1.5rem; font-weight:650; letter-spacing:-.035em; color:{BRAND}; line-height:1.3;}}
.eyebrow {{font-size:.62rem; font-weight:700; letter-spacing:.13em; text-transform:uppercase;}}
.terminal-picker-label {{font-size:.65rem; color:{MUTED}; margin-bottom:4px; letter-spacing:.08em; text-transform:uppercase;}}
.st-key-top_asset [data-testid="stRadioOption"] > div > div:first-child {{display:none;}}
.st-key-top_asset [role="radiogroup"] {{gap:5px;}}
.st-key-top_asset [data-testid="stRadioOption"] {{border:1px solid #DFE2D7; border-radius:6px; padding:5px 22px; margin:0; background:#FFFDF8; cursor:pointer;}}
.st-key-top_asset [data-testid="stRadioOption"][data-selected="true"] {{background:{BRAND}; border-color:{BRAND};}}
.st-key-top_asset [data-testid="stRadioOption"][data-selected="true"] p {{color:#FFFDF8;}}
.snapshot-strip {{display:flex; flex-wrap:wrap; gap:6px 22px; align-items:center; border-top:1px solid #E1E3D9;
    padding:10px 0 5px; margin-bottom:4px; font-size:.72rem; color:{MUTED}; line-height:1.5;}}
.snapshot-strip b {{font-weight:600; color:{BRAND};}}
.snapshot-indicator {{font-size:.62rem; font-weight:700; color:{BRAND}; letter-spacing:.08em; padding:3px 7px; border:1px solid #D9DED2; border-radius:4px; background:#EDF0E8;}}
.hero {{margin:3px 0 10px;}}
.hero .t {{font-size:1.55rem; font-weight:600;}}
.hero .t span {{font-size:.78rem; margin-top:4px;}}
.tag {{font-size:.65rem; font-weight:500; margin-left:0;}}
div[class*="st-key-card"] {{background:#FFFDF9; border-color:#E0E4D9 !important; border-radius:10px !important;}}
.sec {{font-size:.96rem; font-weight:650; margin-bottom:12px;}}
.sec span {{font-size:.76rem;}}
.radar-terminal {{display:grid; grid-template-columns:minmax(210px,.8fr) minmax(0,1.65fr); gap:26px; padding:8px 0 16px; align-items:center;}}
.radar-state.kpi {{border:none !important; padding:8px 22px 8px 4px; min-height:0;}}
.radar-state .l {{font-size:.74rem; letter-spacing:.03em;}}
.radar-state.kpi .v {{font-size:clamp(2.3rem,4vw,3.8rem); line-height:1.3; padding:2px 0; margin:10px 0; font-weight:550;}}
.radar-state .s {{font-size:.75rem;}}
.radar-confidence {{font-size:1.65rem; font-weight:550; letter-spacing:-.03em; color:{BRAND}; margin-top:20px; font-variant-numeric:tabular-nums;}}
.radar-confidence span {{display:block; color:{MUTED}; font-size:.7rem; font-weight:400; letter-spacing:0; margin-top:2px;}}
.regime-tenure {{color:{MUTED}; font-size:.73rem; line-height:1.65; margin-top:18px;}}
.regime-tenure b {{color:{BRAND}; font-weight:600;}}
.probability-board {{display:grid; gap:7px; min-width:0;}}
.probability-row.regime-mobile-state {{display:grid; grid-template-columns:1.2fr 1fr 1fr; gap:14px; align-items:center;
    padding:10px 12px; border:1px solid #E6E9E0; border-left:3px solid var(--c); border-radius:6px; background:#FFFDF9; min-width:0;}}
.probability-row.selected {{background:#F0F4ED; border-color:#DBE5D5; border-left-color:var(--c);}}
.probability-row .state-label {{min-width:0;}}
.probability-row strong {{font-size:.84rem; font-weight:600; color:{BRAND};}}
.probability-row small {{font-size:.61rem; margin:3px 0 0; display:block; color:{MUTED}; line-height:1.4;}}
.prob-reading {{min-width:0;}}
.prob-reading b {{font-size:1rem; display:block; font-weight:600; font-variant-numeric:tabular-nums; margin-top:3px; color:{BRAND};}}
.terminal-track {{height:3px; background:#E7EAE0; margin-top:7px; border-radius:5px; overflow:hidden;}}
.terminal-track i {{display:block; height:100%; background:var(--c); border-radius:5px;}}
.prob-reading:last-child .terminal-track i {{opacity:.55;}}
.kpi-grid {{border-radius:8px; background:#FFFDF9; margin:3px 0 12px;}}
.kpi {{min-height:104px; padding:12px 18px;}}
.kpi .v {{font-size:1.65rem;}}
.state-legend {{display:flex; align-items:center; flex-wrap:wrap; gap:5px; color:{MUTED}; font-size:.7rem; margin:0 0 3px;}}
.drivers-strip {{display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; margin:4px 0 12px;}}
.driver-observation {{border-left:2px solid #D9E1D0; padding:4px 12px; min-width:0;}}
.driver-observation span {{display:block; color:{MUTED}; font-size:.72rem;}}
.driver-observation b {{display:block; color:{BRAND}; font-size:1.3rem; font-weight:550; margin:6px 0; font-variant-numeric:tabular-nums;}}
.driver-observation small {{font-size:.68rem; color:{MUTED}; display:block;}}
.asset-snapshots {{display:grid; grid-template-columns:1fr 1fr; gap:16px;}}
.asset-snapshot {{background:#F7F8F3; border:1px solid #E2E7DA; border-radius:7px; padding:17px 18px; min-width:0;}}
.asset-snapshot-head {{display:flex; justify-content:space-between; color:{BRAND}; font-size:.85rem; margin-bottom:14px;}}
.asset-snapshot-head span {{font-size:.7rem; color:{MUTED};}}
.asset-snapshot>strong {{display:block; font-size:1.55rem; color:{BRAND}; font-weight:550;}}
.asset-snapshot small {{display:block; font-size:.68rem; color:{MUTED}; margin-top:4px;}}
.asset-snapshot p {{font-size:.73rem !important; color:{BRAND}; margin:12px 0;}}
.asset-snapshot-metrics {{display:grid; grid-template-columns:1fr 1fr; gap:12px; border-top:1px solid #E0E6D8; margin-top:15px; padding-top:12px;}}
.asset-snapshot-metrics span {{font-size:.67rem; color:{MUTED};}}
.asset-snapshot-metrics b {{display:block; font-size:1.05rem; color:{BRAND}; font-weight:600; margin-top:5px;}}
.finding {{border-left:3px solid {ACCENT}; padding:12px 18px; background:#F6F4EA; border-radius:0 6px 6px 0; margin:12px 0;}}
.finding .eyebrow {{display:block; color:{WARN}; margin-bottom:7px;}}
.finding>strong {{font-size:.95rem; font-weight:600; color:{BRAND}; display:block;}}
.finding>p {{font-size:.8rem !important; line-height:1.65 !important; color:#626A5D; margin:8px 0 0;}}
.regime-timeline {{display:grid; gap:0;}}
.timeline-row {{display:grid; grid-template-columns:1.1fr 1.4fr auto; align-items:center; gap:12px; padding:11px 0; border-bottom:1px solid #EBEEE5; font-size:.75rem;}}
.timeline-row:last-child {{border:none;}}
.timeline-row span {{font-variant-numeric:tabular-nums; color:{BRAND};}}
.timeline-row small {{display:block; color:{MUTED}; font-size:.65rem; margin-top:2px;}}
.timeline-row b,.timeline-row strong {{font-weight:550;}}
.timeline-row strong {{color:{MUTED};}}
[data-testid="stTabs"] [role="tablist"] {{overflow-x:auto; flex-wrap:nowrap; gap:12px; border-bottom:1px solid #DFE4D6;}}
[data-testid="stTabs"] [role="tab"] {{font-size:.76rem; white-space:nowrap; padding:7px 3px;}}
[data-testid="stTabs"] [aria-selected="true"] {{color:{NAVY}; font-weight:600;}}
.metric-strip {{display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; padding:12px 0;}}
.metric-strip span {{color:{MUTED}; font-size:.7rem;}}
.metric-strip b {{display:block; font-size:1.1rem; font-weight:550; color:{BRAND}; margin-top:5px;}}
@container dashboard (max-width:700px) {{
    .radar-terminal {{grid-template-columns:1fr; gap:18px;}}
    .radar-state.kpi {{display:grid; grid-template-columns:1fr auto; padding:2px 0 14px; border-bottom:1px solid #E3E8DB !important;}}
    .radar-state .l,.radar-state .v,.radar-state .s {{grid-column:1;}}
    .radar-state .radar-confidence {{grid-column:2; grid-row:1/4; align-self:center; margin:0; text-align:right;}}
    .radar-state .regime-tenure {{grid-column:1/3; margin-top:12px;}}
    .radar-state.kpi .v {{font-size:2.7rem;}}
    .drivers-strip {{gap:8px;}}
    .driver-observation {{padding-left:8px;}}
    .driver-observation b {{font-size:1.15rem;}}
}}
@container dashboard (max-width:520px) {{
    .terminal-title {{font-size:1.3rem;}}
    .terminal-brand {{padding-bottom:2px;}}
    .terminal-brand .eyebrow {{font-size:.57rem;}}
    .snapshot-strip {{gap:7px 12px; font-size:.65rem;}}
    .hero .t {{font-size:1.35rem;}}
    .hero .t span {{font-size:.7rem;}}
    .probability-row.regime-mobile-state {{grid-template-columns:1.15fr 1fr 1fr; gap:9px; padding:10px;}}
    .probability-row strong {{font-size:.78rem;}}
    .probability-row small {{font-size:.58rem;}}
    .prob-reading b {{font-size:.9rem;}}
    .asset-snapshots {{grid-template-columns:1fr;}}
    .drivers-strip {{grid-template-columns:1fr; gap:10px;}}
    .driver-observation {{display:grid; grid-template-columns:1fr auto; gap:3px;}}
    .driver-observation b {{grid-column:2; grid-row:1/3; margin:0; align-self:center;}}
    .driver-observation small {{grid-column:1;}}
    .metric-strip {{grid-template-columns:1fr 1fr;}}
    .kpi .v {{font-size:1.4rem;}}
    .kpi {{padding:10px 12px;}}
    .sec {{align-items:flex-start; flex-direction:column; gap:3px;}}
    .finding {{padding:12px;}}
}}
</style>
"""


# Market-studio visual layer: financial grid, real-data ticker art and an editorial hero.
CSS += f"""
<style>
.stApp {{background-color:#F2F1E9; background-image:linear-gradient(rgba(62,74,61,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(62,74,61,.025) 1px,transparent 1px); background-size:64px 64px;}}
.block-container {{padding-top:1.3rem; max-width:1640px;}}
.terminal-brand .eyebrow {{letter-spacing:.17em; color:#9A743F;}}
.terminal-title {{font-size:1.9rem; letter-spacing:-.055em;}}
.terminal-brand {{padding-bottom:10px;}}
.snapshot-strip {{border-color:#D1D8C8; padding:9px 0;}}
.hero {{margin:3px 0 5px;}}
.hero .t {{font-size:1.3rem;}}
.hero .t span {{display:inline; margin-left:10px;}}
.tag {{font-family:'Cascadia Code',Consolas,monospace; font-size:.61rem; letter-spacing:.05em; background:#F3E8CC; color:#946E32; border-color:#E4D1A4;}}
.sidebar-model-pill {{display:inline-block; padding:5px 9px; margin:8px 0; color:#E9CD93 !important; border:1px solid rgba(233,205,147,.28); border-radius:4px; font-family:Consolas,monospace; font-size:.66rem; letter-spacing:.05em;}}
.market-tickers {{display:grid; grid-template-columns:1fr 1fr; gap:14px; margin:3px 0 4px;}}
.market-ticker {{background:linear-gradient(105deg,#FFFDF7,#F7F6EF); border:1px solid #DDE2D3; border-radius:9px; padding:13px 18px; position:relative; overflow:hidden;}}
.ticker-heading {{display:flex; align-items:center; gap:9px;}}
.coin-mark {{display:grid; place-items:center; width:28px; height:28px; background:#EDE1CB; color:#96703C; border:1px solid #DCC49F; border-radius:50%; font-size:1rem;}}
.ticker-heading b {{font-size:.8rem; color:{BRAND}; font-weight:650;}}
.ticker-heading small {{font-size:.64rem; color:{MUTED}; margin-left:5px; font-weight:400;}}
.ticker-period {{margin-left:auto; color:{MUTED}; border:1px solid #E1E4D9; font-family:Consolas,monospace; font-size:.6rem; padding:1px 5px; border-radius:3px;}}
.ticker-bottom {{display:flex; justify-content:space-between; align-items:center; gap:20px; margin-top:8px;}}
.ticker-bottom strong {{display:block; color:{INK}; font-size:1.45rem; font-weight:550; letter-spacing:-.04em; font-variant-numeric:tabular-nums;}}
.ticker-bottom span {{display:block; font-size:.68rem; margin-top:2px;}}
.market-spark {{width:46%; max-width:220px; height:42px; flex-shrink:1;}}
.st-key-card_ai_radar {{padding:18px !important; border-color:#CCD5C1 !important; box-shadow:0 8px 26px rgba(36,56,41,.04) !important;}}
.st-key-card_ai_radar>.stVerticalBlock {{gap:12px;}}
.radar-terminal {{grid-template-columns:minmax(260px,1fr) minmax(0,1.2fr); gap:24px; align-items:stretch; padding:0 0 5px;}}
.radar-state.kpi.market-state {{position:relative; isolation:isolate; background:#2D4439; border:none !important; border-radius:8px;
    padding:25px 28px; overflow:hidden; min-height:310px;}}
.market-state>div:not(.market-artwork) {{position:relative; z-index:1;}}
.market-artwork {{position:absolute; inset:40px -60px 0 30%; opacity:.24; z-index:0; pointer-events:none;}}
.market-candles {{width:100%; height:100%;}}
.market-state:after {{content:''; position:absolute; inset:0; background:linear-gradient(90deg,rgba(34,55,44,.25),transparent); z-index:0; pointer-events:none;}}
.market-kicker {{font-family:Consolas,monospace; font-size:.67rem; letter-spacing:.06em; color:#D9DECA; margin-bottom:20px;}}
.market-kicker span {{float:right; color:#B8CAAF; font-size:.56rem;}}
.market-state .l {{color:#B5C8B6; font-size:.74rem;}}
.market-state.kpi .v {{color:#F0E6CE; font-size:clamp(2.8rem,4.5vw,4rem); font-weight:450; line-height:1.3; padding:2px 0; margin:0 0 5px;}}
.market-state .s {{color:#B5C8B6;}}
.market-state .radar-confidence {{color:#F6F3E5; font-size:1.75rem; margin-top:15px;}}
.market-state .radar-confidence span {{color:#B8CCB8; font-size:.65rem;}}
.market-state .regime-tenure {{margin-top:18px; color:#B9CDBA; font-size:.7rem;}}
.market-state .regime-tenure b {{color:#E3D2A5;}}
.probability-board {{gap:5px;}}
.probability-row.regime-mobile-state {{background:#F6F7F0; border:0; border-left:3px solid var(--c); border-radius:5px; padding:10px 15px;}}
.probability-row.selected {{background:#E8EFDF;}}
.probability-row strong {{font-size:.9rem;}}
.prob-reading b {{font-family:'Cascadia Code',Consolas,monospace; font-size:1.1rem; font-weight:500;}}
.terminal-track {{height:4px;}}
.market-interpretation {{display:flex; gap:16px; align-items:flex-start; padding:12px 15px; border:1px solid #E2E6D9; background:#F5F5EB; border-radius:6px;}}
.market-interpretation>span {{color:#997640; font-size:.6rem; letter-spacing:.09em; font-weight:700; white-space:nowrap; padding-top:4px;}}
.market-interpretation>p {{margin:0; color:#5A6555; font-size:.77rem !important; line-height:1.6;}}
.kpi-grid {{background:#FFFDF7; border-color:#D8DFCE;}}
.kpi .l {{font-size:.69rem; letter-spacing:.02em;}}
.kpi .v {{font-family:'Cascadia Code',Consolas,monospace; font-size:1.55rem; font-weight:500;}}
.market-state.kpi .v {{font-family:Inter,Aptos,'Segoe UI',sans-serif;}}
.st-key-card_overview_price {{background:#FFFDF9; border-color:#CCD8C1 !important; box-shadow:0 6px 22px rgba(36,56,41,.025) !important;}}
.sec {{font-size:1.02rem;}}
.finding {{background:#F0F1E6;}}
@container dashboard (max-width:700px) {{
 .radar-terminal {{grid-template-columns:1fr; gap:12px;}}
 .radar-state.kpi.market-state {{display:block; padding:20px 22px; min-height:270px;}}
 .market-state .radar-confidence {{margin-top:12px; text-align:left;}}
 .market-state.kpi .v {{font-size:3.3rem;}}
 .market-state .regime-tenure {{margin-top:12px;}}
 .market-kicker {{margin-bottom:12px;}}
 .market-artwork {{inset:35px -40px 0 20%;}}
}}
@container dashboard (max-width:520px) {{
 .terminal-title {{font-size:1.45rem;}}
 .terminal-brand .eyebrow {{font-size:.5rem; letter-spacing:.1em;}}
 .hero .t span {{display:block; margin-left:0;}}
 .market-tickers {{gap:8px;}}
 .market-ticker {{padding:10px;}}
 .ticker-heading {{gap:5px;}}
 .coin-mark {{width:22px; height:22px; font-size:.8rem;}}
 .ticker-heading small {{display:none;}}
 .ticker-bottom {{display:block; margin-top:6px;}}
 .ticker-bottom strong {{font-size:1.14rem;}}
 .market-spark {{display:block; width:100%; height:29px; margin-top:5px;}}
 .st-key-card_ai_radar {{padding:12px !important;}}
 .market-state.kpi .v {{font-size:2.9rem;}}
 .probability-row.regime-mobile-state {{padding:10px;}}
 .prob-reading b {{font-size:.91rem;}}
 .market-interpretation {{display:block;}}
 .market-interpretation>span {{display:block; margin-bottom:7px;}}
 .kpi .v {{font-size:1.25rem;}}
}}
</style>
"""


