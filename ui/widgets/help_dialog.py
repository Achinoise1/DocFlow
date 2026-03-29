"""使用指南对话框"""
import os
import re
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


_HELP_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body      { font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 14px;
              line-height: 1.5; color: #333; }
  h1        { font-size: 22px; color: #1565C0; border-bottom: 2px solid #1565C0;
              padding-bottom: 6px; margin-top: 20px; }
  h2        { font-size: 16px; color: #1976D2; margin-top: 20px; margin-bottom: 6px; }
  h3        { font-size: 14px; color: #1976D2; margin-top: 14px; margin-bottom: 4px; }
  p         { margin: 2px 0; }
  code      { background: #E3F2FD; color: #0D47A1; padding: 1px 5px;
              border-radius: 3px; font-family: Consolas, monospace; }
  table     { border-collapse: collapse; width: 100%; margin: 10px 0; }
  th        { background: #1976D2; color: #fff; padding: 6px 9px; text-align: left; }
  td        { padding: 6px 9px; border-bottom: 1px solid #ddd; }
  tr:nth-child(even) td { background: #F5F5F5; }
  .step     { display: block; background: #E3F2FD; border-left: 4px solid #1976D2;
              padding: 6px 9px; margin: 8px 0; border-radius: 0 6px 6px 0; }
  .tip      { background: #FFF8E1; border-left: 4px solid #FFA000;
              padding: 6px 9px; margin: 8px 0; border-radius: 0 6px 6px 0; }
  .warn     { background: #FBE9E7; border-left: 4px solid #E53935;
              padding: 6px 9px; margin: 8px 0; border-radius: 0 6px 6px 0; }
  ul        { padding-left: 6px; margin: 6px 0; }
  ol        { padding-left: 6px; margin: 6px 0; }
  li        { margin: 2px 0; }
  hr        { border: none; border-top: 1px solid #ddd; margin: 2px 0; }
  .img      { text-align: left; }
  img      { display: block; margin: 0; line-height: 0;}
</style>
</head>
<body>

<h1>📖 使用指南</h1>
<p>DocFlow 是一款 <b>本地离线</b> 文档格式转换工具，无需联网，文件不上传云端，安全可靠。</p>

<hr>

<h1>🖥️ 系统要求</h1>
<ul>
  <li>Windows 10 / 11（64 位）</li>
  <li>Word / PPT → PDF 转换：需要本机已安装 <b>Microsoft Office 或 WPS</b></li>
</ul>

<hr>

<h1>🚀 启动软件</h1>
<p>直接双击 <code>DocFlow.exe</code> 即可运行。</p>
<p class="tip">💡 首次启动会有几秒等待，属于正常现象。</p>
<p class="img"><img src="mainpage.png" width="480"></p>

<hr>

<h1>🗂️ 界面介绍</h1>
<p>软件顶部有三个功能选项卡：</p>
<table>
  <tr><th>选项卡</th><th>说明</th></tr>
  <tr><td>📄 文档转换</td><td>Word / PPT 转为 PDF</td></tr>
  <tr><td>📕 PDF转换</td><td>PDF 转为 Word、PPT 或图片</td></tr>
  <tr><td>🖼️ 图片转换</td><td>多张图片合并为 PDF 或插入 Word</td></tr>
</table>
<p>右上角 🌙 / ☀️ 按钮可切换深色 / 浅色主题，❓ 按钮打开本指南。</p>

<hr>

<h1>📋 使用步骤</h1>

<p><span class="step">第一步：选择转换类型</span></p>
<p>点击对应的选项卡，再从下拉菜单中选择具体转换方式。</p>
<p><b>📄 文档转换</b></p>
<p class="img"><img src="doc-transfer.png" width="480"></p>
<p><b>📕 PDF转换</b></p>
<p class="img"><img src="pdf-transfer.png" width="480"></p>
<p><b>🖼️ 图片转换</b></p>
<p class="img"><img src="image-transfer.png" width="480"></p>

<p><span class="step">第二步：添加文件</span></p>
<p>有两种方式添加文件：</p>
<ul>
  <li><b>拖拽</b>：直接将文件或整个目录拖入中央的虚线框</li>
  <li><b>点击按钮</b>：点击下方 <code>📄 选择文件</code> 或 <code>📁 选择目录</code> 按钮</li>
</ul>
<p>拖入目录时，软件会自动识别其中与当前转换模式匹配的文件并显示在列表中：</p>
<p class="img"><img src="folder-content.png" width="480"></p>
<p class="img"><img src="file-list.png" width="480"></p>
<p class="tip">💡 提示区域会显示当前转换模式支持的文件格式，格式不匹配的文件会提示「文件类型不匹配」并忽略。</p>
<p class="img"><img src="incorrect-suffix.png" width="480"></p>

<p><span class="step">第三步：选择输出目录（可选）</span></p>
<ul>
  <li>默认将转换结果保存在<b>与源文件相同的目录</b></li>
  <li>点击左下角 <code>📁 选择输出目录</code> 可自定义保存位置</li>
</ul>

<p><span class="step">第四步：开始转换</span></p>
<p>点击右下角蓝色 <b>▶ 开始转换</b> 按钮，每个文件的进度会实时显示在文件列表中。</p>
<p class="img"><img src="add-file.png" width="480"></p>
<p>转换完成后：</p>
<ul>
  <li>文件状态显示 <b>✓ 完成</b></li>
  <li>勾选了「转换完成后自动打开」时，会自动打开输出文件</li>
</ul>
<p class="img"><img src="finish-transfer.png" width="480"></p>

<hr>

<h1>🔄 支持的转换格式</h1>

<table>
  <tr>
    <th>转换方向</th><th>输入格式</th><th>输出格式</th><th>依赖要求</th>
  </tr>
  <tr><td>Word → PDF</td><td>.doc .docx</td><td>.pdf</td><td>需要 Office 或 WPS</td></tr>
  <tr><td>PPT → PDF</td><td>.ppt .pptx</td><td>.pdf</td><td>需要 Office 或 WPS</td></tr>
  <tr><td>PDF → Word</td><td>.pdf</td><td>.docx</td><td>无</td></tr>
  <tr><td>PDF → PPT</td><td>.pdf</td><td>.pptx</td><td>无</td></tr>
  <tr><td>PDF → 图片</td><td>.pdf</td><td>.png / .jpg</td><td>无</td></tr>
  <tr><td>图片 → PDF</td><td>.jpg .jpeg .png</td><td>.pdf（多图合并）</td><td>无</td></tr>
  <tr><td>图片 → Word</td><td>.jpg .jpeg .png</td><td>.docx</td><td>无</td></tr>
</table>

<hr>

<h1>⚙️ 特别说明</h1>

<h2>Word / PPT 转 PDF 需要 Office 或 WPS</h2>
<p>转换时软件会在后台静默调用本机已安装的 Office 或 WPS，转换过程中请<b>不要手动操作 Office / WPS 窗口</b>。</p>

<hr>

<h1>❓ 常见问题</h1>

<h3>Q：添加文件后提示"文件类型不匹配"？</h3>
<p>A：当前选择的转换方式不支持该格式，请先确认选项卡和下拉菜单的转换方向。</p>

<h3>Q：Word / PPT 转 PDF 报错？</h3>
<p>A：请确认本机已安装 Microsoft Office 或 WPS，且版本正常可打开文件。</p>

<h3>Q：转换后文件在哪里？</h3>
<p>A：默认与源文件在同一目录，文件名与原文件相同，扩展名变为目标格式。若指定了输出目录，则在指定目录中。</p>

<h3>Q：转换过程中能取消吗？</h3>
<p>A：可以点击右下角 <b>⏹ 取消全部</b> 按钮中止转换。</p>

<hr>

<h1>📄 日志文件</h1>
<p>软件运行日志保存在与 <code>DocFlow.exe</code> 同目录下的 <code>log.txt</code>，遇到转换失败时可查看详细错误原因。</p>

</body>
</html>
"""


def _fix_img_sizes(html: str, img_dir: str, max_w: int = 680) -> str:
    """将 HTML 中的 img 标签替换为正确的显示尺寸。

    QTextBrowser 不支持 CSS max-width，会严格按 width 属性值放大小图，
    导致尺寸远小于 max_w 的图片被强制拉伸，产生大片空白。
    本函数读取每张图片的实际像素尺寸：大图缩到 max_w，小图保持原始大小。
    """
    from PIL import Image as PILImage

    def _replace(m: re.Match) -> str:
        filename = m.group(1)
        path = os.path.join(img_dir, filename)
        try:
            with PILImage.open(path) as im:
                w, h = im.size
            if w > max_w:
                dw, dh = max_w, int(h * max_w / w)
            else:
                dw, dh = w, h
            return f'<img src="{filename}" width="{dw}" height="{dh}">'
        except Exception:
            return m.group(0)  # 无法读取时保留原始标签

    return re.sub(r'<img src="([^"]+)" width="\d+">', _replace, html)


class HelpDialog(QDialog):
    """使用指南对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('使用指南 - DocFlow')
        self.setMinimumSize(720, 580)
        self.resize(760, 620)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        # 定位图片目录
        if getattr(sys, 'frozen', False):
            img_dir = os.path.join(sys._MEIPASS, 'doc', 'image')
        else:
            img_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'doc', 'image'
            )

        # 内容浏览器：先设置 searchPaths，再 setHtml，确保图片能被找到
        browser = QTextBrowser()
        browser.setSearchPaths([img_dir])
        # 修正 img 尺寸：小图按原始大小显示，大图缩到最大宽度，防止 QTextBrowser 放大小图产生巨大空白
        # browser.setHtml(_HELP_HTML)
        browser.setHtml(_fix_img_sizes(_HELP_HTML, img_dir))
        browser.setOpenExternalLinks(False)
        browser.setReadOnly(True)
        layout.addWidget(browser)

        # 关闭按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton('关闭')
        close_btn.setFixedWidth(90)
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
