"""One current, verified research result set. The dashboard never fits models."""
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard import ui, v2_pages, v2_service  # noqa: E402

st.set_page_config(page_title='Crypto Market Regime Radar', page_icon='📡',
                   layout='wide', initial_sidebar_state='auto')
st.markdown(ui.CSS, unsafe_allow_html=True)
PAGES = ['Overview', 'Regime History', 'Model Comparison', 'Portfolio & Risk']


def sync_header_asset():
    st.session_state['top_asset'] = st.session_state['asset']


def sync_sidebar_asset():
    st.session_state['asset'] = st.session_state['top_asset']


if 'asset' not in st.session_state:
    st.session_state['asset'] = 'BTC'
if 'top_asset' not in st.session_state:
    st.session_state['top_asset'] = st.session_state['asset']

with st.sidebar:
    st.markdown("<div class='wordmark'>Regime<span> Radar</span>"
                "<small>CRYPTO MARKET RESEARCH</small></div>", unsafe_allow_html=True)
    st.markdown("<div class='sidecap'>TÀI SẢN</div>", unsafe_allow_html=True)
    asset = st.radio('Tài sản', ['BTC', 'ETH'], horizontal=True, key='asset', label_visibility='collapsed', on_change=sync_header_asset)
    st.markdown("<div class='sidecap'>ĐIỀU HƯỚNG</div>", unsafe_allow_html=True)
    page = st.radio('Trang', PAGES, key='nav', label_visibility='collapsed',
                    format_func=lambda name: f'{PAGES.index(name)+1}.  {name}')

context, error = None, None
try:
    context = v2_service.context(asset)
except (OSError, ValueError, KeyError) as exc:
    error = str(exc)

if context is not None:
    title, picker = st.columns([3.3, 1])
    with title:
        st.markdown("<div class='terminal-brand'><span class='eyebrow'>QUANTITATIVE RESEARCH · AI EXPLAINABILITY</span>"
                    "<div class='terminal-title'>Crypto Market Regime Radar</div></div>", unsafe_allow_html=True)
    with picker:
        st.markdown("<div class='terminal-picker-label'>Market / USDT</div>", unsafe_allow_html=True)
        st.radio('Tài sản nhanh', ['BTC', 'ETH'], horizontal=True, key='top_asset', label_visibility='collapsed', on_change=sync_sidebar_asset)
    st.markdown("<div class='snapshot-strip'><span class='snapshot-indicator'>SNAPSHOT · V2</span>"
                f"<span>Nến đóng <b>{context.through:%d/%m/%Y} UTC</b></span>"
                f"<span>Khả dụng <b>{pd.Timestamp(context.signals.as_of_utc.iloc[-1]):%d/%m/%Y %H:%M} UTC</b></span>"
                f"<span>Gaussian HMM · <b>K={context.metadata['K']}</b></span></div>", unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("<div class='sidecap'>DỮ LIỆU</div>"
                    f"<div class='asof' data-result-set='current'>Nến đã đóng đến<br>"
                    f"<b>{context.through:%d/%m/%Y}</b> (UTC)<br>Binance Spot · nến ngày</div>",
                    unsafe_allow_html=True)
        st.caption(f"Gaussian HMM · K = {context.metadata['K']}")
        st.markdown("<div class='sidebar-model-pill'>MODEL · "+('STABLE' if context.metadata['stability']['stable'] else 'UNSTABLE')+"</div>",unsafe_allow_html=True)
        st.caption(f'Xuất kết quả: {pd.Timestamp(context.exported_at):%d/%m %H:%M} UTC')
        st.caption('RQ1–RQ5 · Historical research')
    v2_pages.render(st, ui, context, page)
else:
    st.error(f'Chưa tải được bộ kết quả: {error}')
    st.info('Khôi phục artifact từ gói bàn giao đã xác minh. Không dùng dữ liệu thay thế chưa được kiểm tra.')
    st.markdown("<div class='foot'>Chưa có bộ kết quả hợp lệ</div>", unsafe_allow_html=True)
