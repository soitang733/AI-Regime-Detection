# Lịch sử và khôi phục

Chỉ còn working tree V2 tại `D:\AI-Regime-Detection-main`. Không tạo commit hoặc push trong lần rà soát này. `main` giữ commit V1 `31779c1`; các thay đổi V2 vẫn chưa commit. Remote gốc được giữ; đã fetch để bổ sung Git objects lịch sử bị thiếu trong bản local cũ. Kết quả `git fsck` lưu trong `reports/v2_review/git_fsck.log`.

Snapshot Git có thể phục hồi:

| Ref | Nội dung |
|---|---|
| `refs/archive/v1-commit-worktree` | Bản source cũ từng chuẩn bị commit |
| `refs/archive/v1-original-worktree` | Bản giải nén source V1 còn lại |
| `refs/archive/v2-before-cleanup` | Toàn bộ source/data/model/kết quả V2 trước khi dọn bản trùng/ZIP/tài liệu cũ |

Các snapshot là Git tree refs có thể dùng với `git show`/`git archive`, không phải commit mới. Inventory SHA-256 từng file và tree ID ở `reports/v2_review/repository_history.json`; byte trong Git đã được đọc lại và kiểm tra trước khi xóa thư mục source trùng. M0 baseline ZIP cũng nằm trong ref V2. Theo lựa chọn tiếp theo của người dùng,28 file tài liệu/công cụ/ZIP cũ và12 thư mục cache trong `reports/v2_review/cleanup.json` được giữ nguyên trên đĩa; không xóa đợt này và không xem chúng là bộ kết quả V2 đang dùng.

Xem một file lịch sử:

```powershell
git show refs/archive/v1-original-worktree:README.md
```

Khôi phục file nhị phân an toàn (không dùng PowerShell text redirect cho ZIP):

```powershell
python scripts/restore_history.py --ref refs/archive/v2-before-cleanup --path reports/m0_lock/baseline.zip --output .work/restored-baseline.zip
```

Không ghi đè file đang dùng: helper từ chối destination đã tồn tại. Thư mục `.work` chỉ dành cho phục hồi/tái lập tạm. Xóa bản phục hồi sau khi đối chiếu để giữ repository sạch. Những ref local này chưa được push; một lần push branch thông thường không tự mang theo `refs/archive/*`. Muốn bàn giao lịch sử cần sao lưu thư mục `.git` hoặc xuất bundle Git gồm các archive refs một cách rõ ràng.
