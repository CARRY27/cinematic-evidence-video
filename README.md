# Cinematic Evidence Video

一个面向非真人出镜、证据驱动短视频的 Agent Skill。提供三种可独立调用的能力：

1. **口播稿调整**：保留用户锁定内容，检查事实口径、听感、情绪停顿与时长，交付正文和改动账本。
2. **专业分镜**：按真实配音和参考片设计时间码、证据状态、画面主体、运动弧、2D/3D 选择与声音落点。
3. **2D/3D 动画**：按镜头卡制作可编辑画面和实际渲染，复核质感、连续运动、事实边界与成片技术参数。

核心入口是符合 [Agent Skills 规范](https://agentskills.io/specification)的 [SKILL.md](SKILL.md)。口播、分镜、动画的详细方法分别在 [references/narration.md](references/narration.md)、[references/storyboard.md](references/storyboard.md) 和 [references/animation.md](references/animation.md)。[ofo 案例](references/ofo-v14-case.md)只记录设计取舍，不包含新闻图片、用户素材、声音、工程或成片。

## 使用

安装后对支持 Agent Skills 的 AI 说：

- “使用 cinematic-evidence-video，保留我标出的事实和金句，调整这段口播稿并给出逐句改动账本。”
- “使用 cinematic-evidence-video，根据这段配音和样片做专业分镜，给每镜标时间码、证据身份和运动落点。”
- “使用 cinematic-evidence-video，按镜头卡制作 2D/3D 动画，交付可编辑工程、运动预览和实际导出的成片。”

只要求其中一步时，Skill 不要求把另外两步重做。完整视频任务会按需要串联三个阶段。

## 安装与兼容

将整个 `cinematic-evidence-video` 文件夹放到宿主支持的 Skill 目录。下表是个人级目录；也可使用各宿主支持的项目级目录。

| 宿主 | 个人级目录 | 项目级常见目录 |
|---|---|---|
| Codex | `~/.codex/skills/` | `.agents/skills/` |
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| GitHub Copilot | `~/.copilot/skills/` 或 `~/.agents/skills/` | `.github/skills/`、`.claude/skills/`、`.agents/skills/` |
| Gemini CLI | `~/.gemini/skills/` 或 `~/.agents/skills/` | `.gemini/skills/` 或 `.agents/skills/` |

各宿主识别标准 `SKILL.md` 的方式相近，但文件访问、浏览器、音视频工具、代码执行和插件权限不完全相同。**格式兼容不等于每台机器都具备相同的渲染能力。** 核心 Skill 不依赖某一家 AI 的专用命令；`agents/openai.yaml` 只是 Codex 的可选界面信息。安装位置以各宿主当前官方文档为准：[Codex](https://learn.chatgpt.com/docs/build-skills)、[Claude](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)、[Copilot](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills)、[Gemini CLI](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/using-agent-skills.md)。

## 可选验片脚本

SKILL.md 和参考资料无需安装 Python 依赖。若要运行 `scripts/verify_video.py`，需要 Python 3.9+ 和 PATH 中的 `ffprobe`；使用 `--full-decode` 时还需 `ffmpeg`。此脚本只检查实际媒体文件的技术状态，不判断稿件事实、画面审美或外部审片结论。

```bash
python3 scripts/verify_video.py final.mp4 --width 1080 --height 1920 --fps 30 --full-decode
python3 -m unittest discover -s tests -v
```

如需比较高清和审片版，可加 `--review review.mp4`，并使用 `--review-width`、`--review-height` 指定审片版尺寸。参数仅为命令示例，不是本 Skill 的统一导出规格。

## 公开范围

本项目使用 [MIT License](LICENSE)，版权署名为 Feihaoye。仓库只放通用方法、脱敏案例、自写脚本与合成测试；不要提交用户的原稿、私有素材、本人声音、新闻原图、样片或成片。用户提供的第三方素材不因本项目采用 MIT 而获得再分发许可。

---

**English:** A portable Agent Skill for three stages of evidence-led short-video production: narration revision, professional timecoded storyboarding, and 2D/3D motion production. The `SKILL.md` entrypoint is platform neutral; the optional Python script checks exported media. Reference media and user voice are not bundled. Host capabilities vary.
