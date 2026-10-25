"""Small native SVG market visuals built from verified observations, never synthetic prices."""
from __future__ import annotations
import numpy as np
from dashboard import ui


def sparkline(prices, count=45):
    values=prices.sort_values('date_utc').close.tail(count).to_numpy(float)
    if not len(values) or not np.isfinite(values).all():
        raise ValueError('Không có chuỗi giá hợp lệ cho sparkline')
    width,height=180,42
    span=max(float(np.ptp(values)),1e-12)
    x=np.linspace(2,width-2,len(values));y=height-5-(values-values.min())/span*(height-10)
    points=' '.join(f'{a:.2f},{b:.2f}' for a,b in zip(x,y))
    positive=values[-1]>=values[0]
    color=ui.LOW if positive else ui.HIGH
    area=f'2,{height} {points} {width-2},{height}'
    return (f"<svg class='market-spark' viewBox='0 0 {width} {height}' role='img' aria-label='{len(values)} giá đóng cửa gần nhất'>"
            f"<polygon points='{area}' fill='{color}' opacity='.08'/><polyline points='{points}' fill='none' "
            f"stroke='{color}' stroke-width='1.8' stroke-linejoin='round'/></svg>")


def candles(prices, count=52):
    data=prices.sort_values('date_utc').tail(count)
    values=data[['open','high','low','close']].to_numpy(float)
    if not len(values) or not np.isfinite(values).all() or (values<=0).any():
        raise ValueError('OHLC không hợp lệ')
    if (values[:,1]<values[:,[0,3]].max(1)).any() or (values[:,2]>values[:,[0,3]].min(1)).any():
        raise ValueError('OHLC không nhất quán')
    width,height=680,260
    low,high=float(values[:,2].min()),float(values[:,1].max())
    span=max(high-low,1e-12)
    scale=lambda p:height-24-(p-low)/span*(height-48)
    pieces=[f"<svg class='market-candles' viewBox='0 0 {width} {height}' role='img' aria-label='{len(data)} nến OHLC ngày từ snapshot'>"]
    for row in range(1,5):
        pieces.append(f"<path d='M0 {row*height/5}H{width}' stroke='#E4E9D5' opacity='.09'/>")
    step=(width-24)/len(values)
    for index,(opened,highest,lowest,closed) in enumerate(values):
        x=12+(index+.5)*step;color='#9AC7A3' if closed>=opened else '#D5AA67'
        top=min(scale(opened),scale(closed));body=max(abs(scale(opened)-scale(closed)),1.2)
        pieces.append(f"<line x1='{x:.2f}' x2='{x:.2f}' y1='{scale(highest):.2f}' y2='{scale(lowest):.2f}' stroke='{color}' stroke-width='1.1'/>"
                      f"<rect x='{x-step*.25:.2f}' y='{top:.2f}' width='{max(step*.5,1):.2f}' height='{body:.2f}' rx='.8' fill='{color}'/>")
    pieces.append('</svg>')
    return ''.join(pieces)


def ticker(ctx):
    prices=ctx.prices.sort_values('date_utc')
    close=float(prices.close.iloc[-1])
    change=close/float(prices.close.iloc[-2])-1 if len(prices)>1 else 0.
    color=ui.POS if change>=0 else ui.NEG
    symbol='₿' if ctx.asset=='BTC' else 'Ξ'
    return (f"<div class='market-ticker'><div class='ticker-heading'><span class='coin-mark'>{symbol}</span>"
            f"<b>{ctx.asset}<small>/ USDT</small></b><span class='ticker-period'>45 NẾN</span></div>"
            f"<div class='ticker-bottom'><div><strong>{ui.num(close,2)}</strong><span style='color:{color}'>"
            f"{ui.pct(change,2,sign=True)} · 1D</span></div>{sparkline(prices)}</div></div>")
