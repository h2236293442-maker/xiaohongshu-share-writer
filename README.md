# Xiaohongshu Share Writer Skill

把文章、主题、笔记或链接提炼成可直接发布的小红书分享稿，并同步生成逐页配图提示词；配置 APIMart API 后，也可以调用图像模型自动生成配图。

## 功能亮点

- 提炼文章、链接、截图、笔记或主题内容
- 生成小红书多页分享稿：封面、导读、详情页、总结页
- 输出发布标题、发布正文和标签建议
- 为每一页生成统一风格的英文生图提示词
- 可选调用 APIMart 兼容接口生成图片并保存到本地

## 目录结构

```text
.
├── .env.example
├── apimart_xhs_image.py
└── .trae/
    └── skills/
        └── xiaohongshu-share-writer/
            └── SKILL.md
```

## 快速开始

将 `.trae/skills/xiaohongshu-share-writer` 放到你的 Trae skills 目录中，然后在对话里要求使用 `xiaohongshu-share-writer` 生成小红书分享稿。

示例：

```text
使用 xiaohongshu-share-writer，把这篇文章整理成 7 页小红书分享稿，并给每一页生成英文生图提示词。
```

默认会输出：

1. 封面标题候选
2. 导读页文案
3. 逐页内容策划
4. 每页标题、正文、总结
5. 每页英文插图提示词
6. 小红书发布标题
7. 小红书发布正文
8. 推荐标签

## 配置自动生图

复制环境变量模板：

```bash
cp .env.example .env
```

填写你的 APIMart API Key：

```bash
APIMART_API_KEY=your-apimart-api-key
APIMART_BASE_URL=https://api.apimart.ai/v1
APIMART_TEXT_MODEL=gpt-4o-mini
APIMART_IMAGE_MODEL=gpt-image-2
APIMART_IMAGE_SIZE=1280x1024
APIMART_IMAGE_QUALITY=medium
```

注意：不要提交 `.env`，仓库已默认忽略真实环境变量文件。

## 生成图片

如果你已经有生成好的分享稿 Markdown，可以运行：

```bash
python3 apimart_xhs_image.py --markdown "/absolute/path/to/分享稿.md"
```

脚本会读取 Markdown 中的页面内容，调用 APIMart 兼容接口生成图片，并保存到：

```text
<稿件文件名>_images/
```

每一页会保存：

- `.png` 图片
- `.prompt.txt` 最终提示词
- `.json` 页级元数据
- `manifest.json` 总清单

也可以直接生成单页图片：

```bash
python3 apimart_xhs_image.py \
  --title "页面标题" \
  --content "页面内容" \
  --summary "总结1" \
  --summary "总结2" \
  --summary "总结3"
```

## 默认内容风格

这个 skill 默认偏向“小红书爆款风里保留专业感”：

- 标题有钩子，但不过度夸张
- 内容短句、高密度、适合手机阅读
- 多页结构默认控制在 6-8 页
- 配图 prompt 默认使用统一风格锁
- 插图默认不含任何文字，提示词中会包含 `Absolutely no text`

## 安全与隐私

仓库默认不会上传：

- `.env`
- 临时文件
- 图片生成结果
- 系统缓存文件
- 本地调试输出

发布前请确认没有把真实 API Key、私有素材或客户资料写入示例文件。

## License

MIT
