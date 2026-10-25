"""Summarize actual UI acceptance without making new research claims."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = json.loads((ROOT/'outputs/research_v2/technical_acceptance.json').read_text())
    if evidence['technical_status'] != 'passed' or not evidence['checks'].get('ui_single_result_48_passed'):
        raise ValueError('Current UI acceptance has not passed')
    folder = ROOT/'reports/ui_review_20261025'
    folder.mkdir(exist_ok=True)
    document = f'''# Rà soát giao diện và tính nhất quán dữ liệu — 25/10/2026

Thời điểm xác minh UTC: {evidence['checked_at_utc']}.

## Các vấn đề đã sửa

| Vấn đề | Hành vi sau sửa |
|---|---|
| Giao diện mới và cũ gây nhầm lẫn | Chỉ giữ giao diện hiện tại trên cả bốn trang; xóa bộ chọn phiên, nhánh chạy và renderer giao diện cũ |
| Sidebar ghi K=3 trong khi người dùng muốn xem model V2 | Phiên, tài sản, K và ngày được lấy từ cùng context model đã xác minh |
| Dòng “cập nhật mỗi ngày” không có bằng chứng scheduler | Hiển thị nến đã đóng đến ngày nào, thời điểm xuất kết quả UTC, cảnh báo nếu chậm nến |
| Giá/feature/backtest có thể thuộc phiên khác | Kiểm hash và model ID; feature còn đối chiếu input lock của lúc fit; giá dùng snapshot gắn với model |
| Tràn sidebar 6px | Loại resize handle không hoạt động khỏi sidebar cố định 248px; kiểm cả chiều rộng thực và scroll width |
| Module Streamlit cũ còn trong bộ nhớ | Khởi động lại server local, bật file watcher; kiểm bản đang phục vụ trong Chrome, ghi hash source UI |
| Mobile không nhìn được cả current và T+1 | Dùng thẻ xác suất cho từng state; đủ K và cả hai cột xác suất, không phải kéo ngang bảng chính |
| Scenario/phí khác nhưng có nguy cơ dùng nhầm uncertainty | Chỉ hiển thị CI ở đúng scenario close-to-close và phí 10 bps đã được tính; các trường hợp khác có giải thích |
| Các bài test cũ chỉ kiểm giao diện baseline | Chuyển các bài test giao diện sang đối chiếu bộ kết quả hiện tại; kiểm session cũ không thể mở lại màn hình cũ. Các test thuật toán/benchmark vẫn giữ |

## Bằng chứng thực chạy

- Toàn bộ {evidence['details']['pytest']['tests']} test đạt, không fail/error/skip.
- {evidence['details']['browser_checks']} trường hợp Chrome đạt: 2 tài sản × 4 trang × 6 viewport/zoom, chỉ một bộ kết quả hiện tại.
- Mỗi trường hợp kiểm model K/phiên so với metadata, số state đúng K ở Overview, không exception/error, không KPI bị cắt, không tràn toàn trang hoặc sidebar.
- 40 trường hợp viewport trực tiếp; 8 trường hợp zoom 125% được mô phỏng bằng viewport/device scale.
- Source UI không đổi trong suốt phép kiểm; hash source được đối chiếu lại khi nghiệm thu.
- Kiểm tra âm: không fallback sang baseline khi V2 thiếu; từ chối backtest khác model dù hash file được cập nhật; từ chối feature khác phiên fit; không lấy raw mới để thay lịch sử giá V2.

Logs: `outputs/research_v2/acceptance_pytest_final.log/.xml`, `outputs/research_v2/acceptance_browser_release.log`.
Kết quả máy đọc: `outputs/research_v2/technical_acceptance.json`, `outputs/research_v2/ui/acceptance.json`.

Ảnh desktop/mobile: `outputs/research_v2/ui/current_overview_1440_1.png`, `outputs/research_v2/ui/current_overview_390_1.png`.

## Phạm vi giữ nguyên

Không refit, đổi nhãn kinh tế, điều chỉnh chiến lược hoặc sửa kết quả nghiên cứu. Hash model, dữ liệu baseline, source C1/C2 và paper được đối chiếu. Cohort prospective vẫn giữ nguyên; xác nhận nghiên cứu độc lập vẫn pending. Không commit/push.

Các kiểm tra chứng minh hành vi trên những trường hợp nêu trên; không phải bảo đảm không thể phát sinh lỗi với mọi dữ liệu hoặc môi trường khác.
'''
    (folder/'BAO_CAO_RASOAT_UI.md').write_text(document, encoding='utf-8')
    print(str(folder/'BAO_CAO_RASOAT_UI.md'))


if __name__ == '__main__':
    main()
