"""转换类型注册表 - 全局唯一的转换类型知识库

替代原先散落在三处的重复数据：
  - utils/file_utils.py 的 SUPPORTED_EXTENSIONS、CONVERSION_MAP
  - ui/main_window.py 的 _HINT_MAP、_get_accepted_extensions() 中的 ext_map
  - ui/main_window.py 的 _create_tab_page() 中的 combo.addItem() 硬编码

每个条目字段说明：
  id          str   转换类型唯一标识符，与 task_manager 中的 conversion_type 字符串对齐
  label       str   下拉框显示文字
  input_exts  list  接受的输入文件扩展名（小写，含点号）
  output_ext  str   输出文件扩展名
  hint_text   str   拖拽区底部提示文字
  tab         str   所属 Tab 分组：'doc' / 'pdf' / 'image'
  file_type   str   文件分类标识，供 get_file_type() 使用：'word'/'ppt'/'pdf'/'image'
  is_batch    bool  True 表示多文件合并为一个输出（批量模式），False 表示逐文件转换
"""

CONVERSION_REGISTRY = [
    {
        'id':         'word_to_pdf',
        'label':      'Word → PDF',
        'input_exts': ['.doc', '.docx'],
        'output_ext': '.pdf',
        'hint_text':  '支持 Word 文件（.doc、.docx）',
        'tab':        'doc',
        'file_type':  'word',
        'is_batch':   False,
    },
    {
        'id':         'ppt_to_pdf',
        'label':      'PPT → PDF',
        'input_exts': ['.ppt', '.pptx'],
        'output_ext': '.pdf',
        'hint_text':  '支持 PPT 文件（.ppt、.pptx）',
        'tab':        'doc',
        'file_type':  'ppt',
        'is_batch':   False,
    },
    {
        'id':         'pdf_to_word',
        'label':      'PDF → Word',
        'input_exts': ['.pdf'],
        'output_ext': '.docx',
        'hint_text':  '支持 PDF 文件（.pdf）',
        'tab':        'pdf',
        'file_type':  'pdf',
        'is_batch':   False,
    },
    {
        'id':         'pdf_to_ppt',
        'label':      'PDF → PPT',
        'input_exts': ['.pdf'],
        'output_ext': '.pptx',
        'hint_text':  '支持 PDF 文件（.pdf）',
        'tab':        'pdf',
        'file_type':  'pdf',
        'is_batch':   False,
    },
    {
        'id':         'pdf_to_image',
        'label':      'PDF → 图片',
        'input_exts': ['.pdf'],
        'output_ext': '.png',
        'hint_text':  '支持 PDF 文件（.pdf）',
        'tab':        'pdf',
        'file_type':  'pdf',
        'is_batch':   False,
    },
    {
        'id':         'images_to_pdf',
        'label':      '图片 → PDF（合并）',
        'input_exts': ['.jpg', '.jpeg', '.png'],
        'output_ext': '.pdf',
        'hint_text':  '支持图片文件（.jpg、.jpeg、.png）',
        'tab':        'image',
        'file_type':  'image',
        'is_batch':   True,
    },
    {
        'id':         'images_to_word',
        'label':      '图片 → Word',
        'input_exts': ['.jpg', '.jpeg', '.png'],
        'output_ext': '.docx',
        'hint_text':  '支持图片文件（.jpg、.jpeg、.png）',
        'tab':        'image',
        'file_type':  'image',
        'is_batch':   True,
    },
]

# ── 内部索引（模块加载时构建一次，避免重复遍历）──────────────────────────────
_BY_ID  = {entry['id']:  entry for entry in CONVERSION_REGISTRY}
_BY_TAB = {}
for _entry in CONVERSION_REGISTRY:
    _BY_TAB.setdefault(_entry['tab'], []).append(_entry)


def get_by_id(conversion_type_id: str) -> dict | None:
    """根据转换类型 ID 返回对应条目，找不到返回 None。

    Args:
        conversion_type_id: 如 'word_to_pdf'、'images_to_pdf'

    Returns:
        注册表条目 dict，或 None
    """
    return _BY_ID.get(conversion_type_id)


def get_by_tab(tab_name: str) -> list:
    """返回指定 Tab 下的所有条目列表，顺序与 CONVERSION_REGISTRY 一致。

    Args:
        tab_name: 'doc' / 'pdf' / 'image'

    Returns:
        条目 dict 列表，tab_name 不存在时返回空列表
    """
    return _BY_TAB.get(tab_name, [])


def get_all_input_exts() -> set:
    """返回所有条目允许的输入扩展名集合，供 is_supported_file() 使用。"""
    exts = set()
    for entry in CONVERSION_REGISTRY:
        exts.update(entry['input_exts'])
    return exts


def get_file_type_from_ext(ext: str) -> str:
    """根据扩展名返回文件分类标识（word/ppt/pdf/image），未知返回 'unknown'。

    供 file_utils.get_file_type() 在 Step 3 重构后调用。
    """
    ext = ext.lower()
    for entry in CONVERSION_REGISTRY:
        if ext in entry['input_exts']:
            return entry['file_type']
    return 'unknown'
