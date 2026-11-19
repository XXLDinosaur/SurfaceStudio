export function importReviewHtml(review, fmt, esc) {
  const rules = '<h3>导入自动检查 · 已启用</h3><p class="form-note">每次导入扫描时自动选择预览并识别分类。植物拼版全部收录，保留手动分类，不修改原素材；无法确认的素材留在未分类。</p>';
  if (!review?.reviewedAt) {
    return `<section class="import-review">${rules}<p class="form-note">首次检查将在扫描时完成。</p></section>`;
  }
  return `<section class="import-review">${rules}<p class="form-note">上次检查：${esc(new Date(review.reviewedAt * 1000).toLocaleString('zh-CN'))}<br>检查 ${fmt(review.checkedFolders)} 个图片目录 · 收录 ${fmt(review.includedPlantAtlases || 0)} 个植物拼版 · ${fmt(review.colorPreviews)} 个材质采用颜色图预览<br>当前已分类 ${fmt(review.classified)} 个 · 待确认 ${fmt(review.unclassified)} 个 · 保留 ${fmt(review.manualAssignments)} 个手动分类</p></section>`;
}
