# DocFlow 使用说明

DocFlow 是一款**本地离线**文档格式转换工具，无需联网，文件不上传云端，安全可靠。

---

## 系统要求

- Windows 10 / 11（64位）
- **文档转换**功能（Word / PPT → PDF）需要本地安装 Microsoft Office 或 WPS

---

## 启动软件

直接双击 ![img](image/programexe.png) 即可运行。首次启动会有几秒等待，属于正常现象。

![img](image/mainpage.png)

---

## 界面介绍

软件顶部有三个功能选项卡：

| 选项卡 | 说明 |
|--------|------|
| 📄 文档转换 | Word / PPT 转为 PDF |
| 📕 PDF转换 | PDF 转为 Word、PPT 或图片 |
| 🖼️ 图片转换 | 多张图片合并为 PDF 或插入 Word |

右上角 🌙 / ☀️ 按钮可切换深色 / 浅色主题。

---

## 使用步骤

### 第一步：选择转换类型

点击对应的选项卡，再从下拉菜单中选择具体转换方式。

**📄 文档转换**


![img](image/doc-transfer.png)

**📕 PDF转换**


![img](image/pdf-transfer.png)

**🖼️ 图片转换**


![img](image/image-transfer.png)

### 第二步：添加文件

有两种方式添加文件：

- **拖拽**：直接将文件/目录拖入中央的虚线框
- **点击**：单击虚线框，在弹出的文件选择窗口中选取文件

以![img](image/folder.png)目录为例，该目录下有如下文档：

![img](image/folder-content.png)

拖入后会自动识别出其中的 Word 文件，并显示在列表中：

![img](image/file-list.png)



> 提示区域会显示当前转换模式支持的文件格式，格式不匹配的文件会提示「文件类型不匹配」，并忽略该文件的转换。

![img](image/incorrect-suffix.png)

### 第三步：选择输出目录（可选）

- 默认将转换结果保存在**与源文件相同的目录**
- 点击左下角 📁 **选择输出目录** 可自定义保存位置

### 第四步：开始转换

点击右下角蓝色 **▶ 开始转换** 按钮，每个文件的进度会实时显示在文件列表中。

![img](image/add-file.png)

转换完成后：
- 文件状态显示 **✓ 完成**
- 勾选了「转换完成后自动打开」时，会自动打开输出文件

![img](image/finish-transfer.png)

---

## 支持的转换格式

| 转换方向 | 输入格式 | 输出格式 | 依赖要求 |
|----------|----------|----------|----------|
| Word → PDF | .doc .docx | .pdf | 需要 Office 或 WPS |
| PPT → PDF | .ppt .pptx | .pdf | 需要 Office 或 WPS |
| PDF → Word | .pdf | .docx | 无 |
| PDF → PPT | .pdf | .pptx | 无 |
| PDF → 图片 | .pdf | .png / .jpg | 无 |
| 图片 → PDF | .jpg .jpeg .png | .pdf（多图合并） | 无 |
| 图片 → Word | .jpg .jpeg .png | .docx | 无 |

---

## 特别说明

### Word / PPT 转 PDF 需要 Office 或 WPS

转换时软件会在后台静默调用本机已安装的 Office 或 WPS，转换过程中请不要手动操作 Office / WPS 窗口。

---

## 常见问题

**Q：添加文件后提示"文件类型不匹配"？**  
A：当前选择的转换方式不支持该格式，请先确认选项卡和下拉菜单的转换方向。

**Q：Word / PPT 转 PDF 报错？**  
A：请确认本机已安装 Microsoft Office 或 WPS，且版本正常可打开文件。

**Q：转换后文件在哪里？**  
A：默认与源文件在同一目录，文件名与原文件相同，扩展名变为目标格式。若指定了输出目录，则在指定目录中。

**Q：转换过程中能取消吗？**  
A：可以点击右下角 **⏹ 取消全部** 按钮中止转换。

---

## 日志文件

软件运行日志保存在与 `DocFlow.exe` 同目录下的 `log.txt`，遇到转换失败时可查看详细错误原因。
